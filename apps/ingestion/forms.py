from pathlib import PurePosixPath

from django import forms
from django.conf import settings

from apps.ingestion.services.validators import (
    UploadValidationError,
    validate_extension,
    validate_file_signature,
    validate_file_size,
    validate_text_file,
)
from apps.workspaces.models import Workspace


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if hasattr(files, "getlist"):
            return files.getlist(name)
        value = files.get(name) if files else None
        return value if isinstance(value, (list, tuple)) else ([value] if value else [])


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not isinstance(data, (list, tuple)):
            data = [data] if data else []
        cleaned = []
        for item in data:
            if item:
                cleaned.append(super().clean(item, initial))
        return cleaned


def safe_display_name(filename: str) -> str:
    name = PurePosixPath(filename.replace("\\", "/")).name
    name = "".join(char for char in name if char.isprintable()).strip()
    if not name:
        return "uploaded-file"
    return name[:255]


class SourceFileUploadForm(forms.Form):
    workspace = forms.ModelChoiceField(
        queryset=Workspace.objects.none(),
        required=True,
        label="Workspace",
    )
    files = MultipleFileField(
        label="Log or documents",
        widget=MultipleFileInput(attrs={"multiple": True, "accept": ".log,.txt,.pdf,.docx,.doc"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.upload_errors = []
        if user is not None:
            self.fields["workspace"].queryset = Workspace.objects.filter(
                owner=user
            ).order_by("name")

    def clean_files(self):
        uploads = self.cleaned_data.get("files", [])
        max_count = settings.MAX_UPLOAD_COUNT
        accepted = []
        accepted_bytes = 0

        for index, uploaded_file in enumerate(uploads):
            if index >= max_count:
                self.upload_errors.append(
                    (safe_display_name(uploaded_file.name), f"Only {max_count} files may be uploaded at once.")
                )
                continue
            try:
                extension = validate_extension(uploaded_file.name)
                validate_file_size(uploaded_file)
                if accepted_bytes + uploaded_file.size > settings.MAX_UPLOAD_BATCH_SIZE:
                    raise UploadValidationError(
                        "The selected files exceed the total upload batch limit."
                    )
                detected_type = validate_file_signature(uploaded_file, extension)
                encoding = (
                    validate_text_file(uploaded_file)
                    if extension in {".log", ".txt"}
                    else ""
                )
            except UploadValidationError as exc:
                self.upload_errors.append((safe_display_name(uploaded_file.name), str(exc)))
                continue

            uploaded_file.loglens_extension = extension
            uploaded_file.loglens_detected_type = detected_type
            uploaded_file.loglens_encoding = encoding
            uploaded_file.loglens_display_name = safe_display_name(uploaded_file.name)
            accepted.append(uploaded_file)
            accepted_bytes += uploaded_file.size

        if not uploads and not self.upload_errors:
            raise forms.ValidationError("Choose at least one file to upload.")
        return accepted

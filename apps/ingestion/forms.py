from django import forms

from apps.ingestion.services.validators import (
    UploadValidationError,
    validate_extension,
    validate_file_signature,
    validate_file_size,
)
from apps.workspaces.models import Workspace


class SourceFileUploadForm(forms.Form):
    workspace = forms.ModelChoiceField(
        queryset=Workspace.objects.none(),
        required=True,
        label="Workspace",
    )

    file = forms.FileField(
        required=True,
        label="Log or document",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields["workspace"].queryset = Workspace.objects.filter(
                owner=user
            ).order_by("name")

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]

        try:
            extension = validate_extension(uploaded_file.name)
            validate_file_size(uploaded_file)
            validate_file_signature(uploaded_file, extension)
        except UploadValidationError as exc:
            raise forms.ValidationError(str(exc)) from exc

        return uploaded_file
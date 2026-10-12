from django import forms

from apps.ingestion.models import SourceFile
from apps.workspaces.models import Workspace


class BenchmarkRunForm(forms.Form):
    workspace = forms.ModelChoiceField(
        queryset=Workspace.objects.none(),
        label="Workspace",
        empty_label="Select a workspace",
    )

    source_file = forms.ModelChoiceField(
        queryset=SourceFile.objects.none(),
        label="Source file",
        empty_label="Select an extracted source file",
    )

    pattern = forms.CharField(
        label="Literal pattern",
        max_length=1000,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Example: ERROR",
                "autocomplete": "off",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is None:
            return

        self.fields["workspace"].queryset = (
            Workspace.objects
            .filter(owner=user)
            .order_by("name")
        )

        self.fields["source_file"].queryset = (
            SourceFile.objects
            .filter(
                owner=user,
                extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
            )
            .select_related("workspace")
            .order_by("-uploaded_at")
        )

    def clean_pattern(self):
        pattern = self.cleaned_data.get("pattern", "")

        if not pattern.strip():
            raise forms.ValidationError(
                "The benchmark pattern cannot be empty."
            )

        return pattern

    def clean(self):
        cleaned_data = super().clean()

        workspace = cleaned_data.get("workspace")
        source_file = cleaned_data.get("source_file")

        if workspace is not None and source_file is not None:
            if source_file.workspace_id != workspace.id:
                raise forms.ValidationError(
                    "The selected source file does not belong "
                    "to the selected workspace."
                )

        return cleaned_data
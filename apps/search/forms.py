from django import forms

from apps.ingestion.models import SourceFile
from apps.search.models import IndicatorRule, SavedSearch
from apps.search.services.matching import ALGORITHMS
from apps.workspaces.models import Workspace


ALGORITHM_CHOICES = [
    ("naive", "Naive"),
    ("kmp", "KMP"),
    ("rabin_karp", "Rabin-Karp"),
]


class SearchRunForm(forms.Form):
    workspace = forms.ModelChoiceField(
        queryset=Workspace.objects.none(),
        label="Workspace",
        empty_label="Select a workspace",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    source_file = forms.ModelChoiceField(
        queryset=SourceFile.objects.none(),
        label="Source file",
        empty_label="Select an extracted source file",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    pattern = forms.CharField(
        label="Literal pattern",
        max_length=1000,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: ERROR",
                "autocomplete": "off",
            }
        ),
    )

    algorithm = forms.ChoiceField(
        label="Algorithm",
        choices=ALGORITHM_CHOICES,
        widget=forms.Select(
            attrs={"class": "form-select"}
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
                "The search pattern cannot be empty."
            )

        return pattern

    def clean_algorithm(self):
        algorithm = self.cleaned_data["algorithm"]

        if algorithm not in ALGORITHMS:
            raise forms.ValidationError(
                "Invalid search algorithm."
            )

        return algorithm

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


class SavedSearchForm(forms.Form):
    workspace = forms.ModelChoiceField(
        queryset=Workspace.objects.none(),
        label="Workspace",
        empty_label="Select a workspace",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    name = forms.CharField(
        max_length=200,
        label="Search name",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: Database Errors",
            }
        ),
    )

    pattern = forms.CharField(
        max_length=1000,
        label="Literal pattern",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: ERROR",
            }
        ),
    )

    algorithm = forms.ChoiceField(
        choices=ALGORITHM_CHOICES,
        label="Algorithm",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    description = forms.CharField(
        required=False,
        label="Description",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields["workspace"].queryset = (
                Workspace.objects
                .filter(owner=user)
                .order_by("name")
            )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "The saved search name cannot be empty."
            )

        return name

    def clean_pattern(self):
        pattern = self.cleaned_data["pattern"].strip()

        if not pattern:
            raise forms.ValidationError(
                "The saved search pattern cannot be empty."
            )

        return pattern


class IndicatorRuleForm(forms.Form):
    workspace = forms.ModelChoiceField(
        queryset=Workspace.objects.none(),
        label="Workspace",
        empty_label="Select a workspace",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    name = forms.CharField(
        max_length=200,
        label="Indicator name",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: Database Error",
            }
        ),
    )

    pattern = forms.CharField(
        max_length=1000,
        label="Literal pattern",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: database connection failed",
            }
        ),
    )

    description = forms.CharField(
        required=False,
        label="Description",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
            }
        ),
    )

    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label="Active",
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input"}
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields["workspace"].queryset = (
                Workspace.objects
                .filter(owner=user)
                .order_by("name")
            )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "The indicator name cannot be empty."
            )

        return name

    def clean_pattern(self):
        pattern = self.cleaned_data["pattern"].strip()

        if not pattern:
            raise forms.ValidationError(
                "The indicator pattern cannot be empty."
            )

        return pattern
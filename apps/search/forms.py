from django import forms

from apps.ingestion.models import SourceFile
from apps.search.services.matching import ALGORITHMS
from apps.search.services.normalization import UNICODE_NORMALIZATION_CHOICES
from apps.search.models import IndicatorRule
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

    source_files = forms.ModelMultipleChoiceField(
        queryset=SourceFile.objects.none(),
        label="Source files",
        widget=forms.SelectMultiple(
            attrs={"class": "form-select", "size": "6"}
        ),
    )

    pattern = forms.CharField(
        label="Literal pattern",
        max_length=1000,
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "One literal pattern per line, e.g. ERROR\\nWARN",
                "rows": 4,
                "autocomplete": "off",
            }
        ),
    )

    indicator_rule = forms.ModelChoiceField(
        queryset=IndicatorRule.objects.none(),
        label="Indicator rule",
        required=False,
        empty_label="Search a custom pattern",
        help_text="Choose a saved literal indicator, or leave this blank to enter a pattern.",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    case_sensitive = forms.BooleanField(
        label="Case-sensitive",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    unicode_normalization = forms.ChoiceField(
        label="Unicode normalization",
        choices=UNICODE_NORMALIZATION_CHOICES,
        initial="none",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    algorithm = forms.ChoiceField(
        label="Algorithm",
        choices=ALGORITHM_CHOICES,
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    level_filter = forms.ChoiceField(
        label="Log level filter",
        choices=[("", "All levels"), ("ERROR", "ERROR"), ("WARN", "WARN"), ("INFO", "INFO"), ("DEBUG", "DEBUG")],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
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

        self.fields["source_files"].queryset = (
            SourceFile.objects
            .filter(
                owner=user,
                extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
            )
            .select_related("workspace")
            .order_by("-uploaded_at")
        )
        self.fields["indicator_rule"].queryset = (
            IndicatorRule.objects
            .filter(owner=user, is_active=True)
            .select_related("workspace")
            .order_by("name")
        )

    def clean_pattern(self):
        raw = self.cleaned_data.get("pattern", "")
        patterns = list(dict.fromkeys(line.strip() for line in raw.splitlines() if line.strip()))
        if len(patterns) > 20:
            raise forms.ValidationError("Enter no more than 20 patterns per search batch.")
        return patterns

    def clean_unicode_normalization(self):
        return self.cleaned_data.get("unicode_normalization") or "none"

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
        source_files = cleaned_data.get("source_files")
        patterns = cleaned_data.get("pattern", [])
        indicator_rule = cleaned_data.get("indicator_rule")

        if not patterns and indicator_rule is None:
            self.add_error("pattern", "Enter at least one literal pattern or select an indicator rule.")
        elif patterns and indicator_rule is not None:
            self.add_error("indicator_rule", "Choose either a custom pattern or an indicator rule, not both.")

        if workspace is not None and source_files is not None:
            if any(source_file.workspace_id != workspace.id for source_file in source_files):
                raise forms.ValidationError("Every selected source file must belong to the selected workspace.")
            requested_patterns = len(patterns) or (1 if indicator_rule is not None else 0)
            if len(source_files) * requested_patterns > 100:
                raise forms.ValidationError("A search batch can contain at most 100 file/pattern combinations.")

        if workspace is not None and indicator_rule is not None:
            if indicator_rule.workspace_id != workspace.id:
                self.add_error(
                    "indicator_rule",
                    "The selected indicator does not belong to this workspace.",
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

    source_file = forms.ModelChoiceField(
        queryset=SourceFile.objects.none(),
        label="Source file",
        empty_label="Select an extracted source file",
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

    case_sensitive = forms.BooleanField(
        label="Case-sensitive",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    unicode_normalization = forms.ChoiceField(
        label="Unicode normalization",
        choices=UNICODE_NORMALIZATION_CHOICES,
        initial="none",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
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

            self.fields["source_file"].queryset = (
                SourceFile.objects
                .filter(
                    owner=user,
                    extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
                )
                .select_related("workspace")
                .order_by("-uploaded_at")
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

    def clean_unicode_normalization(self):
        return self.cleaned_data.get("unicode_normalization") or "none"

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

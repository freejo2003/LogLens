from django.contrib.auth import get_user_model
from django import forms

from apps.accounts.services import REVIEWER_ROLE
from apps.workspaces.models import Workspace


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ("name", "description")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "maxlength": 200}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class ReviewerShareForm(forms.Form):
    reviewer = forms.ModelChoiceField(queryset=get_user_model().objects.none(), widget=forms.Select(attrs={"class": "form-select"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reviewer"].queryset = get_user_model().objects.filter(groups__name=REVIEWER_ROLE).distinct().order_by("username")

from django import forms

from apps.workspaces.models import Workspace


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ("name", "description")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "maxlength": 200}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

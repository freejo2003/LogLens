from django import forms
from django.contrib.auth import get_user_model

from apps.accounts.services import LOG_LENS_ROLES


class RoleAssignmentForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        label="Account",
    )
    role = forms.ChoiceField(
        choices=[(role, role) for role in LOG_LENS_ROLES],
        label="LogLens role",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = get_user_model().objects.order_by("username")

    def clean_user(self):
        user = self.cleaned_data["user"]
        if user.is_superuser:
            raise forms.ValidationError(
                "Superusers already have the Admin role and cannot be reassigned here."
            )
        return user

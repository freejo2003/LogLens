"""Create a superuser from temporary deployment environment variables."""

import os

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a superuser from DJANGO_SUPERUSER_* environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if not username or not password:
            raise CommandError(
                "Set DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD."
            )

        user_model = get_user_model()
        existing = user_model.objects.filter(
            **{user_model.USERNAME_FIELD: username}
        ).first()
        if existing:
            if existing.is_superuser and existing.is_staff:
                self.stdout.write("Bootstrap superuser already exists; no changes made.")
                return
            raise CommandError(
                "That username already belongs to a non-superuser. Choose another username."
            )

        candidate = user_model(**{user_model.USERNAME_FIELD: username})
        if email and any(field.name == "email" for field in user_model._meta.fields):
            candidate.email = email
        validate_password(password, user=candidate)

        create_kwargs = {
            user_model.USERNAME_FIELD: username,
            "password": password,
        }
        if email and any(field.name == "email" for field in user_model._meta.fields):
            create_kwargs["email"] = email
        user_model.objects.create_superuser(**create_kwargs)
        self.stdout.write("Bootstrap superuser created.")

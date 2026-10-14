from django.core.management.base import BaseCommand

from apps.accounts.services import get_or_create_role_groups


class Command(BaseCommand):
    help = "Create the LogLens application role groups."

    def handle(self, *args, **options):
        roles = get_or_create_role_groups()

        for role_name, group in roles.items():
            self.stdout.write(
                self.style.SUCCESS(
                    f"Role ready: {role_name} (Group ID: {group.id})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "LogLens role groups are ready."
            )
        )
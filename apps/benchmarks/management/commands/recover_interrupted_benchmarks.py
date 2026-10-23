from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.benchmarks.models import BenchmarkRun


class Command(BaseCommand):
    help = "Mark in-process benchmark runs interrupted by a service restart as failed."

    def handle(self, *args, **options):
        count = BenchmarkRun.objects.filter(
            status__in=[BenchmarkRun.Status.PENDING, BenchmarkRun.Status.RUNNING]
        ).update(
            status=BenchmarkRun.Status.FAILED,
            progress_message="The service restarted before this benchmark finished.",
            error_message="The service restarted before this benchmark finished. Run it again.",
            completed_at=timezone.now(),
        )
        self.stdout.write(f"Marked {count} interrupted benchmark(s) as failed.")

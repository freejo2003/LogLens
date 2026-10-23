from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from apps.accounts.services import ANALYST_ROLE, assign_role
from apps.benchmarks.models import BenchmarkRun
from apps.benchmarks.services.benchmark_persistence import (
    create_pending_benchmark_run,
)
from apps.ingestion.models import SourceFile, TextSegment
from apps.workspaces.models import Workspace


User = get_user_model()


class BenchmarkWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="benchmark-user",
            password="test-password",
        )
        assign_role(self.user, ANALYST_ROLE)

        self.other_user = User.objects.create_user(
            username="other-user",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Benchmark Workspace",
            description="Workflow test workspace",
            owner=self.user,
        )

        self.other_workspace = Workspace.objects.create(
            name="Other Workspace",
            description="Other user's workspace",
            owner=self.other_user,
        )

        self.source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="benchmark.log",
            storage_key="uploads/benchmark.log",
            storage_path="private_media/uploads/benchmark.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=100,
            checksum="a" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

        TextSegment.objects.create(
            source_file=self.source_file,
            sequence=1,
            text="INFO startup\nERROR database\nERROR database",
            line_number=1,
            parser_name="plain_text",
            parser_version="1.0",
        )
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(
            reverse("benchmarks:run")
        )

        self.assertEqual(response.status_code, 302)

        self.assertIn(
            "/accounts/login/",
            response["Location"],
        )

    def test_authenticated_user_can_open_benchmark_page(self):
        self.client.login(
            username="benchmark-user",
            password="test-password",
        )

        response = self.client.get(
            reverse("benchmarks:run")
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "benchmarks/benchmark.html",
        )

        self.assertContains(
            response,
            "Algorithm Benchmark",
        )

        self.assertContains(
            response,
            "benchmark.log",
        )

    @patch("apps.benchmarks.views.queue_source_benchmark")
    def test_authenticated_user_can_start_benchmark(self, queue_benchmark):
        self.client.login(
            username="benchmark-user",
            password="test-password",
        )

        queue_benchmark.side_effect = lambda **kwargs: create_pending_benchmark_run(
            workspace=kwargs["source_file"].workspace,
            owner=kwargs["owner"],
            text="INFO startup\nERROR database\nERROR database",
            pattern=kwargs["pattern"],
            source_file=kwargs["source_file"],
            case_sensitive=kwargs["case_sensitive"],
            unicode_normalization=kwargs["unicode_normalization"],
        )

        response = self.client.post(
            reverse("benchmarks:run"),
            {
                "workspace": self.workspace.id,
                "source_file": self.source_file.id,
                "pattern": "ERROR",
            },
        )

        self.assertEqual(response.status_code, 302)

        benchmark = BenchmarkRun.objects.get(
            owner=self.user,
        )

        self.assertEqual(
            benchmark.workspace_id,
            self.workspace.id,
        )

        self.assertEqual(
            benchmark.source_file_id,
            self.source_file.id,
        )

        self.assertEqual(
            benchmark.pattern,
            "ERROR",
        )

        self.assertEqual(
            benchmark.status,
            BenchmarkRun.Status.PENDING,
        )

        response = self.client.get(response["Location"])
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Benchmark in progress",
        )

    def test_user_cannot_select_another_users_source_file(self):
        other_source_file = SourceFile.objects.create(
            workspace=self.other_workspace,
            owner=self.other_user,
            original_name="private.log",
            storage_key="uploads/private.log",
            storage_path="private_media/uploads/private.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=100,
            checksum="b" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

        self.client.login(
            username="benchmark-user",
            password="test-password",
        )

        response = self.client.post(
            reverse("benchmarks:run"),
            {
                "workspace": self.workspace.id,
                "source_file": other_source_file.id,
                "pattern": "ERROR",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Select a valid choice",
        )

        self.assertEqual(
            BenchmarkRun.objects.filter(
                owner=self.user,
            ).count(),
            0,
        )

    def test_user_cannot_pair_source_file_with_wrong_workspace(self):
        self.client.login(
            username="benchmark-user",
            password="test-password",
        )

        response = self.client.post(
            reverse("benchmarks:run"),
            {
                "workspace": self.other_workspace.id,
                "source_file": self.source_file.id,
                "pattern": "ERROR",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Select a valid choice",
        )

        self.assertEqual(
            BenchmarkRun.objects.filter(
                owner=self.user,
            ).count(),
            0,
        )

    def test_empty_pattern_is_rejected(self):
        self.client.login(
            username="benchmark-user",
            password="test-password",
        )

        response = self.client.post(
            reverse("benchmarks:run"),
            {
                "workspace": self.workspace.id,
                "source_file": self.source_file.id,
                "pattern": "   ",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "The benchmark pattern cannot be empty.",
        )

        self.assertEqual(
            BenchmarkRun.objects.filter(
                owner=self.user,
            ).count(),
            0,
        )

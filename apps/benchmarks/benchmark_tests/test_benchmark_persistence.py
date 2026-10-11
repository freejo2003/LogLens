from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.benchmarks.models import AlgorithmMetric, BenchmarkRun
from apps.benchmarks.services.benchmark_persistence import (
    create_benchmark_run,
)
from apps.workspaces.models import Workspace


class BenchmarkPersistenceTests(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.user = User.objects.create_user(
            username="benchmark-user",
            password="test-password",
        )

        cls.workspace = Workspace.objects.create(
            name="Benchmark Workspace",
            description="Workspace for benchmark persistence tests.",
            owner=cls.user,
        )

    def test_benchmark_run_is_persisted(self):
        benchmark = create_benchmark_run(
            workspace=self.workspace,
            owner=self.user,
            text="ERROR database ERROR",
            pattern="ERROR",
        )

        benchmark.refresh_from_db()

        self.assertEqual(
            benchmark.status,
            BenchmarkRun.Status.SUCCEEDED,
        )

        self.assertTrue(
            benchmark.positions_consistent,
        )

        self.assertEqual(
            benchmark.pattern,
            "ERROR",
        )

        self.assertEqual(
            benchmark.text_length,
            20,
        )

        self.assertIsNotNone(
            benchmark.completed_at,
        )

    def test_all_algorithm_metrics_are_persisted(self):
        benchmark = create_benchmark_run(
            workspace=self.workspace,
            owner=self.user,
            text="ERROR database ERROR",
            pattern="ERROR",
        )

        metrics = list(
            benchmark.algorithm_metrics.order_by("algorithm")
        )

        self.assertEqual(
            len(metrics),
            3,
        )

        self.assertEqual(
            [metric.algorithm for metric in metrics],
            [
                "kmp",
                "naive",
                "rabin_karp",
            ],
        )

        for metric in metrics:
            self.assertEqual(
                metric.match_count,
                2,
            )

            self.assertEqual(
                metric.positions,
                [0, 15],
            )

            self.assertEqual(
                metric.text_length,
                20,
            )

            self.assertGreaterEqual(
                metric.elapsed_seconds,
                0,
            )

    def test_metrics_are_unique_per_algorithm(self):
        benchmark = create_benchmark_run(
            workspace=self.workspace,
            owner=self.user,
            text="AAAA",
            pattern="AA",
        )

        self.assertEqual(
            AlgorithmMetric.objects.filter(
                benchmark_run=benchmark
            ).count(),
            3,
        )

    def test_user_cannot_benchmark_another_users_workspace(self):
        User = get_user_model()

        other_user = User.objects.create_user(
            username="other-user",
            password="test-password",
        )

        with self.assertRaises(PermissionError):
            create_benchmark_run(
                workspace=self.workspace,
                owner=other_user,
                text="ERROR",
                pattern="ERROR",
            )
    def test_benchmark_stores_input_checksum(self):
        text = "ERROR database ERROR"

        benchmark = create_benchmark_run(
            workspace=self.workspace,
            owner=self.user,
            text=text,
            pattern="ERROR",
        )

        import hashlib

        expected_checksum = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

        self.assertEqual(
            benchmark.input_checksum,
            expected_checksum,
        )

        self.assertEqual(
            benchmark.source_checksum,
            "",
        )

    def test_source_benchmark_stores_source_checksum(self):
        from apps.ingestion.models import SourceFile

        source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="benchmark.log",
            storage_key="uploads/benchmark.log",
            storage_path="private_media/uploads/benchmark.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=100,
            checksum="d" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

        benchmark = create_benchmark_run(
            workspace=self.workspace,
            owner=self.user,
            text="ERROR database",
            pattern="ERROR",
            source_file=source_file,
        )

        self.assertEqual(
            benchmark.source_file_id,
            source_file.id,
        )

        self.assertEqual(
            benchmark.source_checksum,
            "d" * 64,
        )
    
    def test_algorithm_versions_are_persisted(self):
        benchmark = create_benchmark_run(
            workspace=self.workspace,
            owner=self.user,
            text="ERROR ERROR",
            pattern="ERROR",
        )

        metrics = benchmark.algorithm_metrics.all()

        self.assertEqual(
            metrics.count(),
            3,
        )

        for metric in metrics:
            self.assertEqual(
                metric.algorithm_version,
                "1.0",
            )
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.benchmarks.models import AlgorithmMetric, BenchmarkRun
from apps.benchmarks.services.source_benchmark import (
    benchmark_source_file,
    build_source_text,
)
from apps.ingestion.models import SourceFile, TextSegment
from apps.workspaces.models import Workspace


class SourceBenchmarkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.user = User.objects.create_user(
            username="source-benchmark-user",
            password="test-password",
        )

        cls.workspace = Workspace.objects.create(
            name="Source Benchmark Workspace",
            description="Workspace for source benchmark tests.",
            owner=cls.user,
        )

        cls.source_file = SourceFile.objects.create(
            workspace=cls.workspace,
            owner=cls.user,
            original_name="server.log",
            storage_key="uploads/source-benchmark.log",
            storage_path="private_media/uploads/source-benchmark.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=200,
            checksum="b" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

        TextSegment.objects.bulk_create(
            [
                TextSegment(
                    source_file=cls.source_file,
                    sequence=1,
                    text="INFO application started",
                    line_number=1,
                    parser_name="plain_text",
                    parser_version="1.0",
                ),
                TextSegment(
                    source_file=cls.source_file,
                    sequence=2,
                    text="ERROR database connection failed",
                    line_number=2,
                    parser_name="plain_text",
                    parser_version="1.0",
                ),
                TextSegment(
                    source_file=cls.source_file,
                    sequence=3,
                    text="INFO application stopped",
                    line_number=3,
                    parser_name="plain_text",
                    parser_version="1.0",
                ),
            ]
        )

    def test_build_source_text_preserves_segment_order(self):
        text = build_source_text(
            self.source_file
        )

        self.assertEqual(
            text,
            (
                "INFO application started\n"
                "ERROR database connection failed\n"
                "INFO application stopped"
            ),
        )

    def test_benchmark_source_file_persists_run(self):
        benchmark = benchmark_source_file(
            source_file=self.source_file,
            owner=self.user,
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
            len(
                "INFO application started\n"
                "ERROR database connection failed\n"
                "INFO application stopped"
            ),
        )

    def test_benchmark_source_file_persists_three_metrics(self):
        benchmark = benchmark_source_file(
            source_file=self.source_file,
            owner=self.user,
            pattern="ERROR",
        )

        metrics = list(
            AlgorithmMetric.objects.filter(
                benchmark_run=benchmark
            ).order_by("algorithm")
        )

        self.assertEqual(
            len(metrics),
            3,
        )

        for metric in metrics:
            self.assertEqual(
                metric.match_count,
                1,
            )

            self.assertEqual(
                metric.positions,
                [25],
            )

    def test_source_file_must_be_successfully_extracted(self):
        self.source_file.extraction_status = (
            SourceFile.ExtractionStatus.PENDING
        )
        self.source_file.save(
            update_fields=["extraction_status"]
        )

        with self.assertRaises(ValueError):
            benchmark_source_file(
                source_file=self.source_file,
                owner=self.user,
                pattern="ERROR",
            )

    def test_user_cannot_benchmark_another_users_source(self):
        User = get_user_model()

        other_user = User.objects.create_user(
            username="unauthorized-source-user",
            password="test-password",
        )

        with self.assertRaises(PermissionError):
            benchmark_source_file(
                source_file=self.source_file,
                owner=other_user,
                pattern="ERROR",
            )

    def test_source_with_no_segments_produces_empty_corpus(self):
        empty_source = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="empty.log",
            storage_key="uploads/empty-source.log",
            storage_path="private_media/uploads/empty-source.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=0,
            checksum="c" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

        self.assertEqual(
            build_source_text(empty_source),
            "",
        )
        
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.benchmarks.models import AlgorithmMetric, BenchmarkRun
from apps.reports.services import (
    build_benchmark_analysis,
    calculate_percentage_difference,
    calculate_relative_time,
    get_algorithm_theory,
    get_empirical_order,
)
from apps.workspaces.models import Workspace
from apps.accounts.models import AuditEvent
from apps.accounts.services import ANALYST_ROLE, assign_role
from apps.benchmarks.services.benchmark_persistence import create_benchmark_run


User = get_user_model()


class ReportAnalysisServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="report-test-user",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Report Test Workspace",
            description="Workspace used for report analysis tests.",
            owner=self.user,
        )
        assign_role(self.user, ANALYST_ROLE)

    def create_benchmark(self):
        benchmark = BenchmarkRun.objects.create(
            workspace=self.workspace,
            owner=self.user,
            pattern="ERROR",
            source_checksum="source-checksum",
            input_checksum="input-checksum",
            text_length=10000,
            status=BenchmarkRun.Status.SUCCEEDED,
            positions_consistent=True,
        )

        AlgorithmMetric.objects.create(
            benchmark_run=benchmark,
            algorithm="naive",
            algorithm_version="1.0",
            elapsed_seconds=0.20,
            preprocessing_seconds=0.000001,
            search_seconds=0.20,
            total_seconds=0.20,
            warmup_runs=3,
            trial_count=10,
            median_seconds=0.20,
            minimum_seconds=0.19,
            maximum_seconds=0.22,
            trial_times_seconds=[0.19, 0.20, 0.21],
            preprocessing_trial_times_seconds=[0.000001],
            search_trial_times_seconds=[0.20],
            total_trial_times_seconds=[0.20],
            preprocessing_median_seconds=0.000001,
            preprocessing_minimum_seconds=0.000001,
            preprocessing_maximum_seconds=0.000002,
            search_median_seconds=0.20,
            search_minimum_seconds=0.19,
            search_maximum_seconds=0.22,
            total_median_seconds=0.20,
            total_minimum_seconds=0.19,
            total_maximum_seconds=0.22,
            verification_count=0,
            collision_count=0,
            match_count=100,
            positions=[1, 2, 3],
            text_length=10000,
        )

        AlgorithmMetric.objects.create(
            benchmark_run=benchmark,
            algorithm="kmp",
            algorithm_version="1.0",
            elapsed_seconds=0.10,
            preprocessing_seconds=0.000002,
            search_seconds=0.10,
            total_seconds=0.10,
            warmup_runs=3,
            trial_count=10,
            median_seconds=0.10,
            minimum_seconds=0.09,
            maximum_seconds=0.12,
            trial_times_seconds=[0.09, 0.10, 0.11],
            preprocessing_trial_times_seconds=[0.000002],
            search_trial_times_seconds=[0.10],
            total_trial_times_seconds=[0.10],
            preprocessing_median_seconds=0.000002,
            preprocessing_minimum_seconds=0.000001,
            preprocessing_maximum_seconds=0.000003,
            search_median_seconds=0.10,
            search_minimum_seconds=0.09,
            search_maximum_seconds=0.12,
            total_median_seconds=0.10,
            total_minimum_seconds=0.09,
            total_maximum_seconds=0.12,
            verification_count=0,
            collision_count=0,
            match_count=100,
            positions=[1, 2, 3],
            text_length=10000,
        )

        AlgorithmMetric.objects.create(
            benchmark_run=benchmark,
            algorithm="rabin_karp",
            algorithm_version="1.0",
            elapsed_seconds=0.30,
            preprocessing_seconds=0.000003,
            search_seconds=0.30,
            total_seconds=0.30,
            warmup_runs=3,
            trial_count=10,
            median_seconds=0.30,
            minimum_seconds=0.28,
            maximum_seconds=0.32,
            trial_times_seconds=[0.28, 0.30, 0.32],
            preprocessing_trial_times_seconds=[0.000003],
            search_trial_times_seconds=[0.30],
            total_trial_times_seconds=[0.30],
            preprocessing_median_seconds=0.000003,
            preprocessing_minimum_seconds=0.000002,
            preprocessing_maximum_seconds=0.000004,
            search_median_seconds=0.30,
            search_minimum_seconds=0.28,
            search_maximum_seconds=0.32,
            total_median_seconds=0.30,
            total_minimum_seconds=0.28,
            total_maximum_seconds=0.32,
            verification_count=100,
            collision_count=2,
            match_count=100,
            positions=[1, 2, 3],
            text_length=10000,
        )

        return benchmark

    def test_algorithm_theory(self):
        theory = get_algorithm_theory("naive")

        self.assertEqual(
            theory.search_complexity,
            "O(nm)",
        )
        self.assertEqual(
            theory.space_complexity,
            "O(1)",
        )

    def test_build_benchmark_analysis(self):
        benchmark = self.create_benchmark()

        analysis = build_benchmark_analysis(benchmark)

        self.assertEqual(
            analysis.benchmark_id,
            benchmark.pk,
        )
        self.assertEqual(
            analysis.pattern,
            "ERROR",
        )
        self.assertEqual(
            analysis.pattern_length,
            5,
        )
        self.assertEqual(
            analysis.text_length,
            10000,
        )
        self.assertTrue(
            analysis.positions_consistent,
        )
        self.assertEqual(
            len(analysis.algorithms),
            3,
        )

    def test_fastest_algorithm(self):
        benchmark = self.create_benchmark()

        analysis = build_benchmark_analysis(benchmark)

        self.assertIsNotNone(
            analysis.fastest_algorithm,
        )
        self.assertEqual(
            analysis.fastest_algorithm.algorithm,
            "kmp",
        )

    def test_analysis_orders_algorithms_by_median_total_time(self):
        benchmark = self.create_benchmark()
        AlgorithmMetric.objects.filter(
            benchmark_run=benchmark,
            algorithm="naive",
        ).update(
            search_median_seconds=0.489113,
            total_median_seconds=0.489126,
        )
        AlgorithmMetric.objects.filter(
            benchmark_run=benchmark,
            algorithm="kmp",
        ).update(
            search_median_seconds=0.012135,
            total_median_seconds=0.012163,
        )
        AlgorithmMetric.objects.filter(
            benchmark_run=benchmark,
            algorithm="rabin_karp",
        ).update(
            search_median_seconds=0.026246,
            total_median_seconds=0.026281,
        )

        analysis = build_benchmark_analysis(benchmark)

        self.assertEqual(
            [item.algorithm for item in analysis.algorithms],
            ["kmp", "rabin_karp", "naive"],
        )

    def test_slowest_algorithm(self):
        benchmark = self.create_benchmark()

        analysis = build_benchmark_analysis(benchmark)

        self.assertIsNotNone(
            analysis.slowest_algorithm,
        )
        self.assertEqual(
            analysis.slowest_algorithm.algorithm,
            "rabin_karp",
        )

    def test_speedup_over_slowest(self):
        benchmark = self.create_benchmark()

        analysis = build_benchmark_analysis(benchmark)

        self.assertAlmostEqual(
            analysis.speedup_over_slowest,
            3.0,
        )

    def test_rabin_karp_diagnostics_are_preserved(self):
        benchmark = self.create_benchmark()

        analysis = build_benchmark_analysis(benchmark)

        rabin_karp = next(
            item
            for item in analysis.algorithms
            if item.algorithm == "rabin_karp"
        )

        self.assertEqual(
            rabin_karp.verification_count,
            100,
        )
        self.assertEqual(
            rabin_karp.collision_count,
            2,
        )

    def test_relative_time(self):
        result = calculate_relative_time(
            baseline_seconds=0.10,
            comparison_seconds=0.30,
        )

        self.assertAlmostEqual(
            result,
            3.0,
        )

    def test_percentage_difference(self):
        result = calculate_percentage_difference(
            baseline_seconds=0.10,
            comparison_seconds=0.20,
        )

        self.assertAlmostEqual(
            result,
            100.0,
        )

    def test_empirical_order(self):
        benchmark = self.create_benchmark()

        analysis = build_benchmark_analysis(benchmark)

        ordered = get_empirical_order(
            analysis.algorithms,
        )

        self.assertEqual(
            [item.algorithm for item in ordered],
            [
                "kmp",
                "naive",
                "rabin_karp",
            ],
        )


class BenchmarkExportWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="benchmark-export-user",
            password="test-password",
        )
        assign_role(self.user, ANALYST_ROLE)
        self.workspace = Workspace.objects.create(name="Exports", owner=self.user)
        self.benchmark = create_benchmark_run(
            workspace=self.workspace,
            owner=self.user,
            text="ERROR ERROR",
            pattern="ERROR",
        )
        self.client.force_login(self.user)

    def test_benchmark_json_export_contains_methodology_and_memory(self):
        response = self.client.get(
            reverse("reports:export-json", args=[self.benchmark.pk])
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["benchmark"]["python_version"])
        self.assertEqual(len(payload["algorithms"]), 3)
        self.assertTrue(all("peak_memory_bytes" in row for row in payload["algorithms"]))
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.user,
                action=AuditEvent.Action.EXPORT_CREATED,
                object_id=str(self.benchmark.pk),
                details={"format": "json"},
            ).exists()
        )

    def test_benchmark_csv_export_contains_three_algorithm_rows(self):
        response = self.client.get(
            reverse("reports:export-csv", args=[self.benchmark.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("peak_memory_bytes", response.content.decode("utf-8"))
        self.assertEqual(response.content.decode("utf-8").count("\r\n"), 4)

    def test_benchmark_exports_are_owner_scoped(self):
        other_user = get_user_model().objects.create_user(
            username="benchmark-export-other",
            password="test-password",
        )
        assign_role(other_user, ANALYST_ROLE)
        self.client.force_login(other_user)
        response = self.client.get(
            reverse("reports:export-json", args=[self.benchmark.pk])
        )
        self.assertEqual(response.status_code, 404)

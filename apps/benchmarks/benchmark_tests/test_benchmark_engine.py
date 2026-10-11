from django.test import SimpleTestCase

from apps.benchmarks.services.benchmark_engine import (
    benchmark_algorithm,
    benchmark_all,
)


class BenchmarkAlgorithmTests(SimpleTestCase):
    def test_benchmark_algorithm_returns_result(self):
        result = benchmark_algorithm(
            "naive",
            "ERROR database ERROR",
            "ERROR",
        )

        self.assertEqual(result.algorithm, "naive")
        self.assertEqual(result.pattern, "ERROR")
        self.assertEqual(result.text_length, 20)
        self.assertEqual(result.match_count, 2)
        self.assertEqual(result.positions, (0, 15))
        self.assertGreaterEqual(
            result.elapsed_seconds,
            0,
        )

    def test_elapsed_milliseconds_is_derived(self):
        result = benchmark_algorithm(
            "kmp",
            "AAAAAA",
            "AA",
        )

        self.assertAlmostEqual(
            result.elapsed_milliseconds,
            result.elapsed_seconds * 1000,
        )


class BenchmarkAllTests(SimpleTestCase):
    def test_all_algorithms_are_benchmarked(self):
        result = benchmark_all(
            "ERROR database ERROR",
            "ERROR",
        )

        self.assertEqual(
            set(result.algorithms),
            {"naive", "kmp", "rabin_karp"},
        )

        self.assertEqual(
            len(result.results),
            3,
        )

    def test_all_algorithms_receive_same_input(self):
        result = benchmark_all(
            "AAAA ERROR ERROR database ERROR",
            "ERROR",
        )

        for algorithm_result in result.results:
            self.assertEqual(
                algorithm_result.pattern,
                "ERROR",
            )

            self.assertEqual(
                algorithm_result.text_length,
                len("AAAA ERROR ERROR database ERROR"),
            )

    def test_positions_are_consistent(self):
        result = benchmark_all(
            "ERROR ERROR INFO ERROR",
            "ERROR",
        )

        self.assertTrue(
            result.positions_consistent,
        )

        for algorithm_result in result.results:
            self.assertEqual(
                algorithm_result.positions,
                (0, 6, 17),
            )

            self.assertEqual(
                algorithm_result.match_count,
                3,
            )

    def test_overlapping_matches_are_consistent(self):
        result = benchmark_all(
            "AAAA",
            "AA",
        )

        self.assertTrue(
            result.positions_consistent,
        )

        for algorithm_result in result.results:
            self.assertEqual(
                algorithm_result.positions,
                (0, 1, 2),
            )

    def test_empty_pattern_is_rejected(self):
        with self.assertRaises(ValueError):
            benchmark_all(
                "some text",
                "",
            )
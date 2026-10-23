from django.test import SimpleTestCase

from apps.benchmarks.services.benchmark_engine import (
    DEFAULT_TRIALS,
    DEFAULT_WARMUP_RUNS,
    benchmark_algorithm,
    benchmark_all,
)
from apps.search.services.matching import SearchMatchLimitError


class BenchmarkEngineTests(SimpleTestCase):

    def test_benchmark_algorithm_returns_expected_result(self):
        result = benchmark_algorithm(
            "naive",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=1,
            trials=3,
        )

        self.assertEqual(result.algorithm, "naive")
        self.assertEqual(result.pattern, "ERROR")
        self.assertEqual(result.text_length, 20)
        self.assertEqual(result.match_count, 2)
        self.assertEqual(result.positions, (0, 15))

    def test_benchmark_algorithm_records_repeated_trials(self):
        result = benchmark_algorithm(
            "naive",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=2,
            trials=5,
        )

        self.assertEqual(result.warmup_runs, 2)
        self.assertEqual(result.trial_count, 5)
        self.assertEqual(len(result.trial_times_seconds), 5)

        for elapsed in result.trial_times_seconds:
            self.assertGreaterEqual(elapsed, 0)

    def test_elapsed_seconds_is_median(self):
        result = benchmark_algorithm(
            "naive",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=0,
            trials=5,
        )

        self.assertEqual(
            result.elapsed_seconds,
            result.median_seconds,
        )

        self.assertEqual(
            result.elapsed_milliseconds,
            result.median_milliseconds,
        )

    def test_trial_statistics_have_valid_spread(self):
        result = benchmark_algorithm(
            "naive",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=1,
            trials=5,
        )

        self.assertLessEqual(
            result.minimum_seconds,
            result.median_seconds,
        )

        self.assertLessEqual(
            result.median_seconds,
            result.maximum_seconds,
        )

        self.assertEqual(
            result.minimum_seconds,
            min(result.trial_times_seconds),
        )

        self.assertEqual(
            result.maximum_seconds,
            max(result.trial_times_seconds),
        )

    def test_phase_timing_records_three_phases(self):
        result = benchmark_algorithm(
            "kmp",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=1,
            trials=5,
        )

        self.assertGreaterEqual(
            result.preprocessing_seconds,
            0,
        )

        self.assertGreaterEqual(
            result.search_seconds,
            0,
        )

        self.assertGreaterEqual(
            result.total_seconds,
            0,
        )

    def test_phase_timing_records_all_trial_series(self):
        result = benchmark_algorithm(
            "kmp",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=1,
            trials=5,
        )

        self.assertEqual(
            len(result.preprocessing_trial_times_seconds),
            5,
        )

        self.assertEqual(
            len(result.search_trial_times_seconds),
            5,
        )

        self.assertEqual(
            len(result.total_trial_times_seconds),
            5,
        )

        for elapsed in result.preprocessing_trial_times_seconds:
            self.assertGreaterEqual(elapsed, 0)

        for elapsed in result.search_trial_times_seconds:
            self.assertGreaterEqual(elapsed, 0)

        for elapsed in result.total_trial_times_seconds:
            self.assertGreaterEqual(elapsed, 0)

    def test_phase_statistics_have_valid_spread(self):
        result = benchmark_algorithm(
            "kmp",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=1,
            trials=5,
        )

        self.assertLessEqual(
            result.preprocessing_minimum_seconds,
            result.preprocessing_median_seconds,
        )

        self.assertLessEqual(
            result.preprocessing_median_seconds,
            result.preprocessing_maximum_seconds,
        )

        self.assertLessEqual(
            result.search_minimum_seconds,
            result.search_median_seconds,
        )

        self.assertLessEqual(
            result.search_median_seconds,
            result.search_maximum_seconds,
        )

        self.assertLessEqual(
            result.total_minimum_seconds,
            result.total_median_seconds,
        )

        self.assertLessEqual(
            result.total_median_seconds,
            result.total_maximum_seconds,
        )

    def test_total_timing_is_representative_elapsed_timing(self):
        result = benchmark_algorithm(
            "naive",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=1,
            trials=5,
        )

        self.assertEqual(
            result.elapsed_seconds,
            result.total_seconds,
        )

        self.assertEqual(
            result.median_seconds,
            result.total_median_seconds,
        )

        self.assertEqual(
            result.minimum_seconds,
            result.total_minimum_seconds,
        )

        self.assertEqual(
            result.maximum_seconds,
            result.total_maximum_seconds,
        )

    def test_rabin_karp_diagnostics_are_exposed(self):
        result = benchmark_algorithm(
            "rabin_karp",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=1,
            trials=5,
        )

        self.assertEqual(
            result.positions,
            (0, 15),
        )

        self.assertEqual(
            result.match_count,
            2,
        )

        self.assertEqual(
            result.verification_count,
            2,
        )

        self.assertEqual(
            result.collision_count,
            0,
        )

    def test_non_rabin_karp_algorithms_have_zero_diagnostics(self):
        for algorithm in ("naive", "kmp"):
            result = benchmark_algorithm(
                algorithm,
                "ERROR database ERROR",
                "ERROR",
                warmup_runs=1,
                trials=5,
            )

            self.assertEqual(
                result.collision_count,
                0,
            )

            self.assertEqual(
                result.verification_count,
                0,
            )

    def test_rabin_karp_diagnostics_are_consistent_across_trials(self):
        result = benchmark_algorithm(
            "rabin_karp",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=2,
            trials=10,
        )

        self.assertEqual(
            result.collision_count,
            0,
        )

        self.assertEqual(
            result.verification_count,
            2,
        )

    def test_benchmark_all_uses_three_algorithms(self):
        result = benchmark_all(
            "ERROR ERROR INFO ERROR",
            "ERROR",
            warmup_runs=1,
            trials=3,
        )

        self.assertEqual(
            result.algorithms,
            ("naive", "kmp", "rabin_karp"),
        )

    def test_benchmark_all_uses_same_configuration_for_all_algorithms(self):
        result = benchmark_all(
            "ERROR ERROR INFO ERROR",
            "ERROR",
            warmup_runs=2,
            trials=4,
        )

        self.assertEqual(result.warmup_runs, 2)
        self.assertEqual(result.trial_count, 4)

        for algorithm_result in result.results:
            self.assertEqual(algorithm_result.warmup_runs, 2)
            self.assertEqual(algorithm_result.trial_count, 4)
            self.assertEqual(
                len(algorithm_result.trial_times_seconds),
                4,
            )
            self.assertEqual(
                len(
                    algorithm_result.preprocessing_trial_times_seconds
                ),
                4,
            )
            self.assertEqual(
                len(
                    algorithm_result.search_trial_times_seconds
                ),
                4,
            )
            self.assertEqual(
                len(
                    algorithm_result.total_trial_times_seconds
                ),
                4,
            )

    def test_benchmark_all_positions_are_consistent(self):
        result = benchmark_all(
            "ERROR ERROR INFO ERROR",
            "ERROR",
            warmup_runs=1,
            trials=3,
        )

        self.assertTrue(result.positions_consistent)

        for algorithm_result in result.results:
            self.assertEqual(
                algorithm_result.positions,
                (0, 6, 17),
            )

    def test_benchmark_applies_casefold_and_unicode_normalization(self):
        result = benchmark_all(
            "Straße café",
            "STRASSE CAFE\u0301",
            case_sensitive=False,
            unicode_normalization="NFC",
            warmup_runs=0,
            trials=1,
        )
        self.assertTrue(result.positions_consistent)
        for algorithm_result in result.results:
            self.assertEqual(algorithm_result.positions, (0,))

    def test_benchmark_measures_peak_python_memory(self):
        result = benchmark_algorithm(
            "kmp",
            "ERROR database ERROR",
            "ERROR",
            warmup_runs=0,
            trials=1,
        )
        self.assertIsNotNone(result.peak_memory_bytes)
        self.assertGreater(result.peak_memory_bytes, 0)

    def test_overlap_positions_are_consistent(self):
        result = benchmark_all(
            "AAAA",
            "AA",
            warmup_runs=1,
            trials=3,
        )

        self.assertTrue(result.positions_consistent)

        for algorithm_result in result.results:
            self.assertEqual(
                algorithm_result.positions,
                (0, 1, 2),
            )

    def test_chunked_benchmark_preserves_matches_across_log_boundaries(self):
        progress = []
        result = benchmark_all(
            "ab\nab\nab\nab\n",
            "b\na",
            warmup_runs=0,
            trials=1,
            chunk_lines=2,
            progress_callback=progress.append,
        )

        self.assertTrue(result.positions_consistent)
        for algorithm_result in result.results:
            self.assertEqual(algorithm_result.positions, (1, 4, 7))
        self.assertEqual(len(progress), 6)
        self.assertEqual(
            [event["lines_processed"] for event in progress],
            [2, 4, 2, 4, 2, 4],
        )
        self.assertEqual(progress[-1]["percent"], 99)

    def test_benchmark_enforces_match_result_cap(self):
        with self.assertRaises(SearchMatchLimitError):
            benchmark_all(
                "A" * 1000,
                "A",
                warmup_runs=0,
                trials=1,
                max_matches=5,
            )

    def test_empty_pattern_raises_value_error(self):
        with self.assertRaises(ValueError):
            benchmark_all(
                "ERROR ERROR",
                "",
            )

    def test_zero_trials_raises_value_error(self):
        with self.assertRaises(ValueError):
            benchmark_all(
                "ERROR ERROR",
                "ERROR",
                trials=0,
            )

    def test_negative_warmups_raises_value_error(self):
        with self.assertRaises(ValueError):
            benchmark_all(
                "ERROR ERROR",
                "ERROR",
                warmup_runs=-1,
            )

    def test_default_benchmark_configuration(self):
        result = benchmark_all(
            "ERROR ERROR",
            "ERROR",
        )

        self.assertEqual(
            result.warmup_runs,
            DEFAULT_WARMUP_RUNS,
        )

        self.assertEqual(
            result.trial_count,
            DEFAULT_TRIALS,
        )

        for algorithm_result in result.results:
            self.assertEqual(
                len(algorithm_result.trial_times_seconds),
                DEFAULT_TRIALS,
            )
            self.assertEqual(
                len(
                    algorithm_result.preprocessing_trial_times_seconds
                ),
                DEFAULT_TRIALS,
            )
            self.assertEqual(
                len(
                    algorithm_result.search_trial_times_seconds
                ),
                DEFAULT_TRIALS,
            )
            self.assertEqual(
                len(
                    algorithm_result.total_trial_times_seconds
                ),
                DEFAULT_TRIALS,
            )

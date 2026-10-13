from django.test import SimpleTestCase

from apps.search.services.matching import (
    build_kmp_failure_table,
    kmp_search,
    naive_search,
    prepare_search,
    rabin_karp_search,
    rabin_karp_search_detailed,
    run_search,
    search_prepared,
)


class MatchingTests(SimpleTestCase):

    def test_naive_search_finds_all_matches(self):
        self.assertEqual(
            naive_search(
                "ERROR database ERROR",
                "ERROR",
            ),
            [0, 15],
        )

    def test_naive_search_supports_overlapping_matches(self):
        self.assertEqual(
            naive_search(
                "AAAA",
                "AA",
            ),
            [0, 1, 2],
        )

    def test_naive_search_returns_empty_for_no_match(self):
        self.assertEqual(
            naive_search(
                "INFO Application started",
                "ERROR",
            ),
            [],
        )

    def test_naive_search_returns_empty_for_empty_pattern(self):
        self.assertEqual(
            naive_search(
                "ERROR",
                "",
            ),
            [],
        )

    def test_kmp_failure_table(self):
        self.assertEqual(
            build_kmp_failure_table("ABABCABAB"),
            [0, 0, 1, 2, 0, 1, 2, 3, 4],
        )

    def test_kmp_search_finds_all_matches(self):
        self.assertEqual(
            kmp_search(
                "ERROR database ERROR",
                "ERROR",
            ),
            [0, 15],
        )

    def test_kmp_search_supports_overlapping_matches(self):
        self.assertEqual(
            kmp_search(
                "AAAA",
                "AA",
            ),
            [0, 1, 2],
        )

    def test_kmp_search_returns_empty_for_no_match(self):
        self.assertEqual(
            kmp_search(
                "INFO Application started",
                "ERROR",
            ),
            [],
        )

    def test_kmp_search_returns_empty_for_empty_pattern(self):
        self.assertEqual(
            kmp_search(
                "ERROR",
                "",
            ),
            [],
        )

    def test_rabin_karp_search_finds_all_matches(self):
        self.assertEqual(
            rabin_karp_search(
                "ERROR database ERROR",
                "ERROR",
            ),
            [0, 15],
        )

    def test_rabin_karp_search_supports_overlapping_matches(self):
        self.assertEqual(
            rabin_karp_search(
                "AAAA",
                "AA",
            ),
            [0, 1, 2],
        )

    def test_rabin_karp_search_returns_empty_for_no_match(self):
        self.assertEqual(
            rabin_karp_search(
                "INFO Application started",
                "ERROR",
            ),
            [],
        )

    def test_rabin_karp_search_returns_empty_for_empty_pattern(self):
        self.assertEqual(
            rabin_karp_search(
                "ERROR",
                "",
            ),
            [],
        )

    def test_prepare_search_creates_naive_state(self):
        prepared = prepare_search(
            "naive",
            "ERROR",
        )

        self.assertEqual(prepared.algorithm, "naive")
        self.assertEqual(prepared.pattern, "ERROR")
        self.assertIsNone(prepared.state)

    def test_prepare_search_creates_kmp_lps_state(self):
        prepared = prepare_search(
            "kmp",
            "ABABCABAB",
        )

        self.assertEqual(prepared.algorithm, "kmp")
        self.assertEqual(
            prepared.state,
            [0, 0, 1, 2, 0, 1, 2, 3, 4],
        )

    def test_prepare_search_creates_rabin_karp_state(self):
        prepared = prepare_search(
            "rabin_karp",
            "ERROR",
        )

        self.assertEqual(prepared.algorithm, "rabin_karp")
        self.assertIsInstance(prepared.state, tuple)
        self.assertEqual(len(prepared.state), 3)

    def test_prepared_search_matches_regular_search(self):
        text = "ERROR database ERROR"

        for algorithm in (
            "naive",
            "kmp",
            "rabin_karp",
        ):
            prepared = prepare_search(
                algorithm,
                "ERROR",
            )

            prepared_result = search_prepared(
                prepared,
                text,
            )

            regular_result = run_search(
                algorithm,
                text,
                "ERROR",
            )

            self.assertEqual(
                prepared_result.positions,
                regular_result.positions,
            )

    def test_prepared_search_supports_overlapping_matches(self):
        for algorithm in (
            "naive",
            "kmp",
            "rabin_karp",
        ):
            prepared = prepare_search(
                algorithm,
                "AA",
            )

            result = search_prepared(
                prepared,
                "AAAA",
            )

            self.assertEqual(
                result.positions,
                (0, 1, 2),
            )

    def test_prepared_search_rejects_empty_pattern(self):
        with self.assertRaises(ValueError):
            prepare_search(
                "kmp",
                "",
            )

    def test_rabin_karp_detailed_counts_verifications(self):
        result = rabin_karp_search_detailed(
            "ERROR database ERROR",
            "ERROR",
        )

        self.assertEqual(
            result.positions,
            (0, 15),
        )

        self.assertEqual(
            result.verification_count,
            2,
        )

        self.assertEqual(
            result.collision_count,
            0,
        )

    def test_run_search_returns_normalized_match_result(self):
        result = run_search(
            "kmp",
            "ERROR database ERROR",
            "ERROR",
        )

        self.assertEqual(result.algorithm, "kmp")
        self.assertEqual(result.pattern, "ERROR")
        self.assertEqual(result.positions, (0, 15))
        self.assertEqual(result.match_count, 2)
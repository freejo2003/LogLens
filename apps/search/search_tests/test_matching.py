from django.test import SimpleTestCase

from apps.search.services.matching import (
    ALGORITHMS,
    build_kmp_failure_table,
    kmp_search,
    naive_search,
    rabin_karp_search,
    run_search,
)


class NaiveSearchTests(SimpleTestCase):
    def test_finds_single_match(self):
        self.assertEqual(
            naive_search("hello world", "world"),
            [6],
        )

    def test_finds_multiple_matches(self):
        self.assertEqual(
            naive_search(
                "ERROR ERROR INFO ERROR",
                "ERROR",
            ),
            [0, 6, 17],
        )

    def test_finds_overlapping_matches(self):
        self.assertEqual(
            naive_search("AAAA", "AA"),
            [0, 1, 2],
        )

    def test_returns_empty_for_no_match(self):
        self.assertEqual(
            naive_search("hello", "xyz"),
            [],
        )

    def test_returns_empty_for_empty_pattern(self):
        self.assertEqual(
            naive_search("hello", ""),
            [],
        )

    def test_returns_empty_when_pattern_is_longer(self):
        self.assertEqual(
            naive_search("abc", "abcdef"),
            [],
        )


class KMPTests(SimpleTestCase):
    def test_failure_table(self):
        self.assertEqual(
            build_kmp_failure_table("ABABCABAB"),
            [0, 0, 1, 2, 0, 1, 2, 3, 4],
        )

    def test_finds_single_match(self):
        self.assertEqual(
            kmp_search("hello world", "world"),
            [6],
        )

    def test_finds_multiple_matches(self):
        self.assertEqual(
            kmp_search(
                "ERROR ERROR INFO ERROR",
                "ERROR",
            ),
            [0, 6, 17],
        )

    def test_finds_overlapping_matches(self):
        self.assertEqual(
            kmp_search("AAAA", "AA"),
            [0, 1, 2],
        )

    def test_returns_empty_for_no_match(self):
        self.assertEqual(
            kmp_search("hello", "xyz"),
            [],
        )

    def test_returns_empty_for_empty_pattern(self):
        self.assertEqual(
            kmp_search("hello", ""),
            [],
        )


class RabinKarpTests(SimpleTestCase):
    def test_finds_single_match(self):
        self.assertEqual(
            rabin_karp_search("hello world", "world"),
            [6],
        )

    def test_finds_multiple_matches(self):
        self.assertEqual(
            rabin_karp_search(
                "ERROR ERROR INFO ERROR",
                "ERROR",
            ),
            [0, 6, 17],
        )

    def test_finds_overlapping_matches(self):
        self.assertEqual(
            rabin_karp_search("AAAA", "AA"),
            [0, 1, 2],
        )

    def test_returns_empty_for_no_match(self):
        self.assertEqual(
            rabin_karp_search("hello", "xyz"),
            [],
        )

    def test_returns_empty_for_empty_pattern(self):
        self.assertEqual(
            rabin_karp_search("hello", ""),
            [],
        )


class AlgorithmConsistencyTests(SimpleTestCase):
    def test_all_algorithms_return_identical_positions(self):
        test_cases = [
            ("hello world", "world"),
            ("ERROR ERROR INFO ERROR", "ERROR"),
            ("AAAA", "AA"),
            ("ABABABAB", "ABAB"),
            ("database connection failed", "connection"),
            ("", "test"),
            ("test", ""),
            ("abc", "abcdef"),
            ("abcabcabc", "abc"),
        ]

        for text, pattern in test_cases:
            with self.subTest(
                text=text,
                pattern=pattern,
            ):
                results = [
                    matcher(text, pattern)
                    for matcher in ALGORITHMS.values()
                ]

                self.assertEqual(
                    results[0],
                    results[1],
                )

                self.assertEqual(
                    results[1],
                    results[2],
                )


class RunSearchTests(SimpleTestCase):
    def test_run_search_returns_normalized_result(self):
        result = run_search(
            "kmp",
            "ERROR ERROR",
            "ERROR",
        )

        self.assertEqual(result.algorithm, "kmp")
        self.assertEqual(result.pattern, "ERROR")
        self.assertEqual(result.positions, (0, 6))
        self.assertEqual(result.match_count, 2)

    def test_run_search_rejects_unknown_algorithm(self):
        with self.assertRaises(ValueError):
            run_search(
                "unknown",
                "hello",
                "hello",
            )
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.ingestion.models import SourceFile, TextSegment
from apps.search.services.search_service import (
    search_source_file,
    search_text_segments,
)
from apps.workspaces.models import Workspace


class SearchServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.user = User.objects.create_user(
            username="search-user",
            password="test-password",
        )

        cls.workspace = Workspace.objects.create(
            name="Search Test Workspace",
            description="Workspace for search-service tests.",
            owner=cls.user,
        )

        cls.source_file = SourceFile.objects.create(
            workspace=cls.workspace,
            owner=cls.user,
            original_name="application.log",
            storage_key="uploads/test-search.log",
            storage_path="private_media/uploads/test-search.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=100,
            checksum="a" * 64,
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

    def test_search_text_segments_returns_matching_segments(self):
        segments = TextSegment.objects.select_related("source_file").all()

        results = search_text_segments(
            segments,
            pattern="ERROR",
            algorithm="naive",
        )

        self.assertEqual(len(results), 1)

        result = results[0]

        self.assertEqual(
            result.source_file_name,
            "application.log",
        )
        self.assertEqual(result.sequence, 2)
        self.assertEqual(result.line_number, 2)
        self.assertEqual(result.pattern, "ERROR")
        self.assertEqual(result.algorithm, "naive")
        self.assertEqual(result.positions, (0,))
        self.assertEqual(result.match_count, 1)

    def test_search_source_file_uses_selected_algorithm(self):
        results = search_source_file(
            self.source_file,
            pattern="database",
            algorithm="kmp",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].algorithm, "kmp")
        self.assertEqual(results[0].positions, (6,))
        self.assertEqual(results[0].line_number, 2)

    def test_rabin_karp_returns_same_match_position(self):
        results = search_source_file(
            self.source_file,
            pattern="application",
            algorithm="rabin_karp",
        )

        self.assertEqual(len(results), 2)

        self.assertEqual(
            [result.sequence for result in results],
            [1, 3],
        )

        self.assertEqual(
            [result.positions for result in results],
            [(5,), (5,)],
        )

    def test_multiple_occurrences_in_one_segment_are_preserved(self):
        segment = TextSegment.objects.create(
            source_file=self.source_file,
            sequence=4,
            text="ERROR ERROR ERROR",
            line_number=4,
            parser_name="plain_text",
            parser_version="1.0",
        )

        results = search_text_segments(
            [segment],
            pattern="ERROR",
            algorithm="kmp",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0].positions,
            (0, 6, 12),
        )
        self.assertEqual(
            results[0].match_count,
            3,
        )

    def test_empty_pattern_returns_no_results(self):
        segments = TextSegment.objects.select_related("source_file").all()

        results = search_text_segments(
            segments,
            pattern="",
            algorithm="naive",
        )

        self.assertEqual(results, [])

    def test_unmatched_segments_are_not_returned(self):
        segments = TextSegment.objects.select_related("source_file").all()

        results = search_text_segments(
            segments,
            pattern="CRITICAL",
            algorithm="rabin_karp",
        )

        self.assertEqual(results, [])

    def test_case_insensitive_search_uses_unicode_casefold(self):
        segment = TextSegment.objects.create(
            source_file=self.source_file,
            sequence=5,
            text="Straße login",
            line_number=5,
            parser_name="plain_text",
            parser_version="1.1",
        )
        results = search_text_segments(
            [segment],
            pattern="STRASSE",
            algorithm="kmp",
            case_sensitive=False,
        )
        self.assertEqual(results[0].positions, (0,))

    def test_unicode_normalization_matches_composed_and_decomposed_text(self):
        segment = TextSegment.objects.create(
            source_file=self.source_file,
            sequence=6,
            text="cafe\u0301",
            line_number=6,
            parser_name="plain_text",
            parser_version="1.1",
        )
        results = search_text_segments(
            [segment],
            pattern="café",
            algorithm="rabin_karp",
            unicode_normalization="NFC",
        )
        self.assertEqual(results[0].positions, (0,))

    @override_settings(MAX_NAIVE_COMPARISONS=10)
    def test_naive_search_rejects_excessive_worst_case_work(self):
        from apps.search.services.search_service import SearchWorkLimitError

        segment = TextSegment.objects.create(
            source_file=self.source_file,
            sequence=7,
            text="x" * 20,
            line_number=7,
            parser_name="plain_text",
            parser_version="1.1",
        )
        with self.assertRaises(SearchWorkLimitError):
            search_text_segments(
                [segment],
                pattern="zz",
                algorithm="naive",
            )

    @override_settings(MAX_SEARCH_MATCHES=2)
    def test_search_rejects_excessive_match_results_before_materializing_them(self):
        from apps.search.services.matching import SearchMatchLimitError

        segment = TextSegment.objects.create(
            source_file=self.source_file,
            sequence=8,
            text="A" * 1000,
            line_number=8,
            parser_name="plain_text",
            parser_version="1.1",
        )
        with self.assertRaises(SearchMatchLimitError):
            search_text_segments([segment], pattern="A", algorithm="kmp")

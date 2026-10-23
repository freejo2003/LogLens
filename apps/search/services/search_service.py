from dataclasses import dataclass

from django.conf import settings

from apps.ingestion.models import TextSegment
from apps.search.services.matching import run_search
from apps.search.services.normalization import normalize_search_text


class SearchWorkLimitError(ValueError):
    """Raised when a request would exceed the configured Naive work budget."""


@dataclass(frozen=True)
class SegmentSearchResult:
    """
    A search match associated with its extracted source segment.
    """

    segment_id: int
    source_file_id: int
    source_file_name: str
    sequence: int
    page_number: int | None
    paragraph_number: int | None
    line_number: int | None
    algorithm: str
    pattern: str
    positions: tuple[int, ...]

    @property
    def match_count(self) -> int:
        return len(self.positions)


def search_text_segments(
    segments,
    *,
    pattern: str,
    algorithm: str,
    case_sensitive: bool = True,
    unicode_normalization: str = "none",
) -> list[SegmentSearchResult]:
    """
    Search extracted text segments using the selected algorithm.

    Only segments containing at least one match are returned.

    The algorithm operates entirely on the in-memory text contained
    in each TextSegment.
    """
    if not pattern:
        return []

    results: list[SegmentSearchResult] = []
    normalized_pattern = normalize_search_text(
        pattern,
        case_sensitive=case_sensitive,
        unicode_normalization=unicode_normalization,
    )
    estimated_comparisons = 0
    total_matches = 0

    for segment in segments:
        searchable_text = normalize_search_text(
            segment.text,
            case_sensitive=case_sensitive,
            unicode_normalization=unicode_normalization,
        )
        if algorithm == "naive":
            estimated_comparisons += len(searchable_text) * len(normalized_pattern)
            if estimated_comparisons > settings.MAX_NAIVE_COMPARISONS:
                raise SearchWorkLimitError(
                    "This Naive search exceeds the configured work limit. Use KMP or Rabin-Karp, or narrow the source text."
                )
        match_result = run_search(
            algorithm,
            searchable_text,
            normalized_pattern,
            max_matches=max(0, settings.MAX_SEARCH_MATCHES - total_matches),
        )

        if not match_result.positions:
            continue

        total_matches += len(match_result.positions)

        results.append(
            SegmentSearchResult(
                segment_id=segment.id,
                source_file_id=segment.source_file_id,
                source_file_name=segment.source_file.original_name,
                sequence=segment.sequence,
                page_number=segment.page_number,
                paragraph_number=segment.paragraph_number,
                line_number=segment.line_number,
                algorithm=match_result.algorithm,
                pattern=match_result.pattern,
                positions=match_result.positions,
            )
        )

    return results


def search_source_file(
    source_file,
    *,
    pattern: str,
    algorithm: str,
    case_sensitive: bool = True,
    unicode_normalization: str = "none",
    level_filter: str = "",
) -> list[SegmentSearchResult]:
    """
    Search all extracted segments belonging to one SourceFile.

    The search itself runs against the extracted text in memory.
    """
    segments = (
        TextSegment.objects
        .filter(source_file=source_file)
        .select_related("source_file")
        .order_by("sequence")
    )
    if level_filter:
        segments = segments.filter(text__icontains=level_filter)

    return search_text_segments(
        segments,
        pattern=pattern,
        algorithm=algorithm,
        case_sensitive=case_sensitive,
        unicode_normalization=unicode_normalization,
    )

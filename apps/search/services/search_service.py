from dataclasses import dataclass

from apps.ingestion.models import TextSegment
from apps.search.services.matching import run_search


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

    for segment in segments:
        match_result = run_search(
            algorithm,
            segment.text,
            pattern,
        )

        if not match_result.positions:
            continue

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

    return search_text_segments(
        segments,
        pattern=pattern,
        algorithm=algorithm,
    )

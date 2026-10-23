from apps.benchmarks.models import BenchmarkRun
from apps.benchmarks.services.benchmark_persistence import (
    create_benchmark_run,
)
from apps.benchmarks.services.benchmark_jobs import submit_source_benchmark
from apps.ingestion.models import SourceFile


def build_source_text(source_file: SourceFile) -> str:
    """
    Combine extracted TextSegment records into one ordered
    in-memory benchmark corpus.
    """
    segments = (
        source_file.text_segments
        .all()
        .order_by("sequence")
    )

    return "\n".join(
        segment.text
        for segment in segments
    )


def benchmark_source_file(
    *,
    source_file: SourceFile,
    owner,
    pattern: str,
    case_sensitive: bool = True,
    unicode_normalization: str = "none",
) -> BenchmarkRun:
    """
    Benchmark an extracted source file using all registered
    algorithms.
    """
    if source_file.owner_id != owner.id:
        raise PermissionError(
            "The source file does not belong "
            "to the current user."
        )

    if source_file.extraction_status != (
        SourceFile.ExtractionStatus.SUCCEEDED
    ):
        raise ValueError(
            "The source file must have successful "
            "extraction before it can be benchmarked."
        )

    text = build_source_text(source_file)

    return create_benchmark_run(
        workspace=source_file.workspace,
        owner=owner,
        text=text,
        pattern=pattern,
        source_file=source_file,
        case_sensitive=case_sensitive,
        unicode_normalization=unicode_normalization,
    )


def queue_source_benchmark(
    *,
    source_file: SourceFile,
    owner,
    pattern: str,
    case_sensitive: bool = True,
    unicode_normalization: str = "none",
) -> BenchmarkRun:
    """Queue a source benchmark and return its progress record immediately."""
    if source_file.owner_id != owner.id:
        raise PermissionError("The source file does not belong to the current user.")
    if source_file.extraction_status != SourceFile.ExtractionStatus.SUCCEEDED:
        raise ValueError("The source file must have successful extraction before it can be benchmarked.")

    return submit_source_benchmark(
        source_file=source_file,
        owner=owner,
        text=build_source_text(source_file),
        pattern=pattern,
        case_sensitive=case_sensitive,
        unicode_normalization=unicode_normalization,
    )

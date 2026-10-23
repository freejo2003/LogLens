from dataclasses import dataclass
from statistics import median
import tracemalloc
from time import perf_counter
from typing import Callable

from apps.search.services.matching import (
    ALGORITHMS,
    MatchResult,
    PreparedSearch,
    _rabin_karp_search_prepared,
    prepare_search,
    search_prepared,
)
from apps.search.services.normalization import normalize_search_text


DEFAULT_WARMUP_RUNS = 3
DEFAULT_TRIALS = 10
DEFAULT_MAX_SEARCH_MATCHES = 100_000
DEFAULT_CHUNK_LINES = 300


@dataclass(frozen=True)
class AlgorithmBenchmarkResult:
    algorithm: str
    pattern: str
    text_length: int
    match_count: int
    positions: tuple[int, ...]

    # Representative total elapsed time.
    elapsed_seconds: float

    # Detailed repeated-trial statistics for total execution.
    warmup_runs: int
    trial_count: int
    trial_times_seconds: tuple[float, ...]
    median_seconds: float
    minimum_seconds: float
    maximum_seconds: float

    # Phase-aware timing.
    preprocessing_seconds: float
    search_seconds: float
    total_seconds: float

    # Repeated phase timings.
    preprocessing_trial_times_seconds: tuple[float, ...]
    search_trial_times_seconds: tuple[float, ...]
    total_trial_times_seconds: tuple[float, ...]

    # Phase statistics.
    preprocessing_median_seconds: float
    preprocessing_minimum_seconds: float
    preprocessing_maximum_seconds: float

    search_median_seconds: float
    search_minimum_seconds: float
    search_maximum_seconds: float

    total_median_seconds: float
    total_minimum_seconds: float
    total_maximum_seconds: float

    # Rabin-Karp diagnostics.
    #
    # These remain zero for Naive and KMP because those algorithms
    # do not use hash-candidate verification.
    collision_count: int
    verification_count: int
    peak_memory_bytes: int | None

    @property
    def elapsed_milliseconds(self) -> float:
        return self.elapsed_seconds * 1000

    @property
    def median_milliseconds(self) -> float:
        return self.median_seconds * 1000

    @property
    def minimum_milliseconds(self) -> float:
        return self.minimum_seconds * 1000

    @property
    def maximum_milliseconds(self) -> float:
        return self.maximum_seconds * 1000

    @property
    def preprocessing_milliseconds(self) -> float:
        return self.preprocessing_seconds * 1000

    @property
    def search_milliseconds(self) -> float:
        return self.search_seconds * 1000

    @property
    def total_milliseconds(self) -> float:
        return self.total_seconds * 1000

    @property
    def preprocessing_median_milliseconds(self) -> float:
        return self.preprocessing_median_seconds * 1000

    @property
    def preprocessing_minimum_milliseconds(self) -> float:
        return self.preprocessing_minimum_seconds * 1000

    @property
    def preprocessing_maximum_milliseconds(self) -> float:
        return self.preprocessing_maximum_seconds * 1000

    @property
    def search_median_milliseconds(self) -> float:
        return self.search_median_seconds * 1000

    @property
    def search_minimum_milliseconds(self) -> float:
        return self.search_minimum_seconds * 1000

    @property
    def search_maximum_milliseconds(self) -> float:
        return self.search_maximum_seconds * 1000

    @property
    def total_median_milliseconds(self) -> float:
        return self.total_median_seconds * 1000

    @property
    def total_minimum_milliseconds(self) -> float:
        return self.total_minimum_seconds * 1000

    @property
    def total_maximum_milliseconds(self) -> float:
        return self.total_maximum_seconds * 1000


@dataclass(frozen=True)
class BenchmarkResult:
    pattern: str
    text_length: int
    results: tuple[AlgorithmBenchmarkResult, ...]
    positions_consistent: bool
    warmup_runs: int
    trial_count: int

    @property
    def algorithms(self) -> tuple[str, ...]:
        return tuple(result.algorithm for result in self.results)


def _validate_benchmark_configuration(
    pattern: str,
    warmup_runs: int,
    trials: int,
) -> None:
    if not pattern:
        raise ValueError("Benchmark pattern cannot be empty.")

    if warmup_runs < 0:
        raise ValueError("warmup_runs cannot be negative.")

    if trials <= 0:
        raise ValueError("trials must be greater than zero.")


def _measure_preprocessing(
    algorithm: str,
    pattern: str,
) -> tuple[PreparedSearch, float]:
    """
    Prepare algorithm-specific state and measure only preprocessing.

    The returned state is reused by the search phase so the measured
    search timing does not include preprocessing.
    """
    start = perf_counter()

    prepared = prepare_search(
        algorithm,
        pattern,
    )

    elapsed_seconds = perf_counter() - start

    return prepared, elapsed_seconds


def _measure_search(
    prepared: PreparedSearch,
    text: str,
    *,
    max_matches: int | None = None,
    max_start: int | None = None,
) -> tuple[MatchResult, float, int, int]:
    """
    Execute the search phase using already-prepared algorithm state.

    Returns:
        match result
        search elapsed time
        Rabin-Karp collision count
        Rabin-Karp verification count
    """
    start = perf_counter()

    if prepared.algorithm == "rabin_karp":
        detailed_result = _rabin_karp_search_prepared(
            text,
            prepared.pattern,
            prepared.state,
            max_matches=max_matches,
            max_start=max_start,
        )

        result = MatchResult(
            algorithm=prepared.algorithm,
            pattern=prepared.pattern,
            positions=detailed_result.positions,
        )

        collision_count = detailed_result.collision_count
        verification_count = detailed_result.verification_count

    else:
        result = search_prepared(
            prepared,
            text,
            max_matches=max_matches,
            max_start=max_start,
        )

        collision_count = 0
        verification_count = 0

    elapsed_seconds = perf_counter() - start

    return (
        result,
        elapsed_seconds,
        collision_count,
        verification_count,
    )


def _build_text_chunks(
    text: str,
    chunk_lines: int,
) -> tuple[list[tuple[int, int, int]], int]:
    """Return (start, end, lines) ranges, preserving line-boundary offsets."""
    if chunk_lines < 1:
        raise ValueError("chunk_lines must be greater than zero.")

    total_lines = text.count("\n") + (
        1 if text and not text.endswith("\n") else 0
    )
    if not text:
        return [(0, 0, 0)], 0

    chunks: list[tuple[int, int, int]] = []
    chunk_start = 0
    lines_in_chunk = 0
    for index, character in enumerate(text):
        if character != "\n":
            continue
        lines_in_chunk += 1
        if lines_in_chunk == chunk_lines:
            chunks.append((chunk_start, index + 1, lines_in_chunk))
            chunk_start = index + 1
            lines_in_chunk = 0

    if chunk_start < len(text):
        remaining_lines = total_lines - sum(item[2] for item in chunks)
        chunks.append((chunk_start, len(text), remaining_lines))

    return chunks, total_lines


def _measure_chunked_search(
    prepared: PreparedSearch,
    text: str,
    chunks: list[tuple[int, int, int]],
    *,
    max_matches: int | None,
    progress_callback: Callable[[int], None] | None = None,
) -> tuple[MatchResult, float, int, int]:
    """Search line chunks with a pattern-sized lookahead and global offsets."""
    positions: list[int] = []
    search_seconds = 0.0
    collision_count = 0
    verification_count = 0
    processed_lines = 0
    overlap = max(0, len(prepared.pattern) - 1)

    for start, end, lines_processed in chunks:
        window_end = min(len(text), end + overlap)
        window = text[start:window_end]
        remaining_matches = (
            None if max_matches is None else max_matches - len(positions)
        )
        result, elapsed, collisions, verifications = _measure_search(
            prepared,
            window,
            max_matches=remaining_matches,
            max_start=end - start,
        )
        positions.extend(start + position for position in result.positions)
        search_seconds += elapsed
        collision_count += collisions
        verification_count += verifications
        processed_lines += lines_processed

        if progress_callback is not None:
            progress_callback(processed_lines)

    return (
        MatchResult(
            algorithm=prepared.algorithm,
            pattern=prepared.pattern,
            positions=tuple(positions),
        ),
        search_seconds,
        collision_count,
        verification_count,
    )


def _measure_peak_memory(
    algorithm: str,
    text: str,
    pattern: str,
    *,
    max_matches: int | None,
    chunks: list[tuple[int, int, int]],
) -> int | None:
    """Measure Python-heap peak for one un-timed prepared search pass."""
    if tracemalloc.is_tracing():
        return None
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        prepared = prepare_search(algorithm, pattern)
        _measure_chunked_search(
            prepared,
            text,
            chunks,
            max_matches=max_matches,
        )
        _current, peak = tracemalloc.get_traced_memory()
        return peak
    finally:
        tracemalloc.stop()


def benchmark_algorithm(
    algorithm: str,
    text: str,
    pattern: str,
    *,
    warmup_runs: int = DEFAULT_WARMUP_RUNS,
    trials: int = DEFAULT_TRIALS,
    max_matches: int | None = DEFAULT_MAX_SEARCH_MATCHES,
    case_sensitive: bool = True,
    unicode_normalization: str = "none",
    chunk_lines: int = DEFAULT_CHUNK_LINES,
    progress_callback: Callable[[str, str, int], None] | None = None,
) -> AlgorithmBenchmarkResult:
    """
    Benchmark one search algorithm using phase-aware repeated trials.

    Each measured trial consists of:

        preprocessing -> search

    The two phases are timed independently, while total time is
    measured around the complete operation.

    Warm-up runs are excluded from reported measurements.
    """
    _validate_benchmark_configuration(
        pattern,
        warmup_runs,
        trials,
    )

    original_text_length = len(text)
    searchable_text = normalize_search_text(
        text,
        case_sensitive=case_sensitive,
        unicode_normalization=unicode_normalization,
    )
    searchable_pattern = normalize_search_text(
        pattern,
        case_sensitive=case_sensitive,
        unicode_normalization=unicode_normalization,
    )
    chunks, _total_lines = _build_text_chunks(searchable_text, chunk_lines)
    # Warm-up phase.
    #
    # Warm-ups execute the same complete workflow that is measured:
    # preprocessing followed by search.
    for warmup_index in range(warmup_runs):
        prepared = prepare_search(
            algorithm,
            searchable_pattern,
        )

        _measure_chunked_search(
            prepared,
            searchable_text,
            chunks,
            max_matches=max_matches,
            progress_callback=(
                lambda lines, phase=f"warm-up {warmup_index + 1}/{warmup_runs}":
                progress_callback(algorithm, phase, lines)
                if progress_callback is not None
                else None
            ),
        )

    preprocessing_trial_times: list[float] = []
    search_trial_times: list[float] = []
    total_trial_times: list[float] = []

    collision_counts: list[int] = []
    verification_counts: list[int] = []

    reference_result: MatchResult | None = None

    for trial_index in range(trials):
        (
            prepared,
            preprocessing_seconds,
        ) = _measure_preprocessing(
            algorithm,
            searchable_pattern,
        )

        (
            match_result,
            search_seconds,
            collision_count,
            verification_count,
        ) = _measure_chunked_search(
            prepared,
            searchable_text,
            chunks,
            max_matches=max_matches,
            progress_callback=(
                lambda lines, phase=f"trial {trial_index + 1}/{trials}":
                progress_callback(algorithm, phase, lines)
                if progress_callback is not None
                else None
            ),
        )

        total_seconds = preprocessing_seconds + search_seconds

        preprocessing_trial_times.append(
            preprocessing_seconds
        )

        search_trial_times.append(
            search_seconds
        )

        total_trial_times.append(
            total_seconds
        )

        collision_counts.append(
            collision_count
        )

        verification_counts.append(
            verification_count
        )

        if reference_result is None:
            reference_result = match_result

        elif match_result.positions != reference_result.positions:
            raise RuntimeError(
                f"Algorithm '{algorithm}' produced inconsistent "
                "match positions across benchmark trials."
            )

    assert reference_result is not None

    preprocessing_median_seconds = median(
        preprocessing_trial_times
    )

    preprocessing_minimum_seconds = min(
        preprocessing_trial_times
    )

    preprocessing_maximum_seconds = max(
        preprocessing_trial_times
    )

    search_median_seconds = median(
        search_trial_times
    )

    search_minimum_seconds = min(
        search_trial_times
    )

    search_maximum_seconds = max(
        search_trial_times
    )

    total_median_seconds = median(
        total_trial_times
    )

    total_minimum_seconds = min(
        total_trial_times
    )

    total_maximum_seconds = max(
        total_trial_times
    )

    # The diagnostic counters are deterministic for a fixed text,
    # pattern, and Rabin-Karp configuration. Therefore the first
    # measured trial is used as the representative value.
    representative_collision_count = collision_counts[0]
    representative_verification_count = verification_counts[0]
    peak_memory_bytes = _measure_peak_memory(
        algorithm,
        searchable_text,
        searchable_pattern,
        max_matches=max_matches,
        chunks=chunks,
    )

    if any(
        count != representative_collision_count
        for count in collision_counts
    ):
        raise RuntimeError(
            "Rabin-Karp collision counts changed across benchmark trials."
        )

    if any(
        count != representative_verification_count
        for count in verification_counts
    ):
        raise RuntimeError(
            "Rabin-Karp verification counts changed across benchmark trials."
        )

    return AlgorithmBenchmarkResult(
        algorithm=reference_result.algorithm,
        pattern=pattern,
        text_length=original_text_length,
        match_count=reference_result.match_count,
        positions=reference_result.positions,

        # Compatibility field: representative total time.
        elapsed_seconds=total_median_seconds,

        warmup_runs=warmup_runs,
        trial_count=trials,
        trial_times_seconds=tuple(total_trial_times),
        median_seconds=total_median_seconds,
        minimum_seconds=total_minimum_seconds,
        maximum_seconds=total_maximum_seconds,

        preprocessing_seconds=preprocessing_median_seconds,
        search_seconds=search_median_seconds,
        total_seconds=total_median_seconds,

        preprocessing_trial_times_seconds=tuple(
            preprocessing_trial_times
        ),
        search_trial_times_seconds=tuple(
            search_trial_times
        ),
        total_trial_times_seconds=tuple(
            total_trial_times
        ),

        preprocessing_median_seconds=preprocessing_median_seconds,
        preprocessing_minimum_seconds=preprocessing_minimum_seconds,
        preprocessing_maximum_seconds=preprocessing_maximum_seconds,

        search_median_seconds=search_median_seconds,
        search_minimum_seconds=search_minimum_seconds,
        search_maximum_seconds=search_maximum_seconds,

        total_median_seconds=total_median_seconds,
        total_minimum_seconds=total_minimum_seconds,
        total_maximum_seconds=total_maximum_seconds,

        collision_count=representative_collision_count,
        verification_count=representative_verification_count,
        peak_memory_bytes=peak_memory_bytes,
    )


def benchmark_all(
    text: str,
    pattern: str,
    *,
    warmup_runs: int = DEFAULT_WARMUP_RUNS,
    trials: int = DEFAULT_TRIALS,
    max_matches: int | None = DEFAULT_MAX_SEARCH_MATCHES,
    case_sensitive: bool = True,
    unicode_normalization: str = "none",
    chunk_lines: int = DEFAULT_CHUNK_LINES,
    progress_callback: Callable[[dict], None] | None = None,
) -> BenchmarkResult:
    """
    Benchmark all configured algorithms using identical benchmark
    configuration.

    Correctness is checked through match-position agreement across
    algorithms.
    """
    _validate_benchmark_configuration(
        pattern,
        warmup_runs,
        trials,
    )

    chunks, total_lines = _build_text_chunks(
        normalize_search_text(
            text,
            case_sensitive=case_sensitive,
            unicode_normalization=unicode_normalization,
        ),
        chunk_lines,
    )
    total_units = len(chunks) * len(ALGORITHMS) * (warmup_runs + trials)
    completed_units = 0

    def report_progress(
        algorithm: str,
        phase: str,
        lines_processed: int,
    ) -> None:
        nonlocal completed_units
        completed_units += 1
        if progress_callback is not None:
            progress_callback(
                {
                    "algorithm": algorithm,
                    "phase": phase,
                    "lines_processed": lines_processed,
                    "total_lines": total_lines,
                    "completed_units": completed_units,
                    "total_units": total_units,
                    "percent": min(99, int(completed_units * 99 / total_units)),
                }
            )

    results = tuple(
        benchmark_algorithm(
            algorithm,
            text,
            pattern,
            warmup_runs=warmup_runs,
            trials=trials,
            max_matches=max_matches,
            case_sensitive=case_sensitive,
            unicode_normalization=unicode_normalization,
            chunk_lines=chunk_lines,
            progress_callback=report_progress,
        )
        for algorithm in ALGORITHMS
    )

    positions = results[0].positions

    positions_consistent = all(
        result.positions == positions
        for result in results
    )

    return BenchmarkResult(
        pattern=pattern,
        text_length=len(text),
        results=results,
        positions_consistent=positions_consistent,
        warmup_runs=warmup_runs,
        trial_count=trials,
    )

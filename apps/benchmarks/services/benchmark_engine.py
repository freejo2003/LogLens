from dataclasses import dataclass
from statistics import median
from time import perf_counter

from apps.search.services.matching import ALGORITHMS, run_search


DEFAULT_WARMUP_RUNS = 3
DEFAULT_TRIALS = 10


@dataclass(frozen=True)
class AlgorithmBenchmarkResult:
    algorithm: str
    pattern: str
    text_length: int
    match_count: int
    positions: tuple[int, ...]
    elapsed_seconds: float

    # Detailed repeated-trial statistics.
    warmup_runs: int
    trial_count: int
    trial_times_seconds: tuple[float, ...]
    median_seconds: float
    minimum_seconds: float
    maximum_seconds: float

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


def benchmark_algorithm(
    algorithm: str,
    text: str,
    pattern: str,
    *,
    warmup_runs: int = DEFAULT_WARMUP_RUNS,
    trials: int = DEFAULT_TRIALS,
) -> AlgorithmBenchmarkResult:
    """
    Benchmark one search algorithm using warm-up runs followed by
    repeated measured trials.

    Warm-up runs are excluded from the reported timing.

    The representative elapsed_seconds value is the median measured
    trial time. Detailed trial timings and spread are retained so the
    benchmark can later be persisted and reported rigorously.
    """
    if not pattern:
        raise ValueError("Benchmark pattern cannot be empty.")

    if warmup_runs < 0:
        raise ValueError("warmup_runs cannot be negative.")

    if trials <= 0:
        raise ValueError("trials must be greater than zero.")

    # Warm-up phase.
    for _ in range(warmup_runs):
        run_search(algorithm, text, pattern)

    # Measured phase.
    trial_times = []

    reference_result = None

    for _ in range(trials):
        start = perf_counter()
        match_result = run_search(algorithm, text, pattern)
        elapsed_seconds = perf_counter() - start

        trial_times.append(elapsed_seconds)

        if reference_result is None:
            reference_result = match_result
        else:
            if match_result.positions != reference_result.positions:
                raise RuntimeError(
                    f"Algorithm '{algorithm}' produced inconsistent "
                    "match positions across benchmark trials."
                )

    assert reference_result is not None

    median_seconds = median(trial_times)
    minimum_seconds = min(trial_times)
    maximum_seconds = max(trial_times)

    return AlgorithmBenchmarkResult(
        algorithm=reference_result.algorithm,
        pattern=reference_result.pattern,
        text_length=len(text),
        match_count=reference_result.match_count,
        positions=reference_result.positions,
        elapsed_seconds=median_seconds,
        warmup_runs=warmup_runs,
        trial_count=trials,
        trial_times_seconds=tuple(trial_times),
        median_seconds=median_seconds,
        minimum_seconds=minimum_seconds,
        maximum_seconds=maximum_seconds,
    )


def benchmark_all(
    text: str,
    pattern: str,
    *,
    warmup_runs: int = DEFAULT_WARMUP_RUNS,
    trials: int = DEFAULT_TRIALS,
) -> BenchmarkResult:
    """
    Benchmark all configured algorithms using identical benchmark
    configuration.

    Correctness is checked through the match-position agreement across
    algorithms.
    """
    if not pattern:
        raise ValueError("Benchmark pattern cannot be empty.")

    if warmup_runs < 0:
        raise ValueError("warmup_runs cannot be negative.")

    if trials <= 0:
        raise ValueError("trials must be greater than zero.")

    results = tuple(
        benchmark_algorithm(
            algorithm,
            text,
            pattern,
            warmup_runs=warmup_runs,
            trials=trials,
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
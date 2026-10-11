from dataclasses import dataclass
from time import perf_counter

from apps.search.services.matching import ALGORITHMS, run_search


@dataclass(frozen=True)
class AlgorithmBenchmarkResult:
    """
    Performance and correctness information for one algorithm run.
    """

    algorithm: str
    pattern: str
    text_length: int
    match_count: int
    positions: tuple[int, ...]
    elapsed_seconds: float

    @property
    def elapsed_milliseconds(self) -> float:
        return self.elapsed_seconds * 1000


@dataclass(frozen=True)
class BenchmarkResult:
    """
    Complete benchmark for the registered search algorithms.
    """

    pattern: str
    text_length: int
    results: tuple[AlgorithmBenchmarkResult, ...]
    positions_consistent: bool

    @property
    def algorithms(self) -> tuple[str, ...]:
        return tuple(result.algorithm for result in self.results)


def benchmark_algorithm(
    algorithm: str,
    text: str,
    pattern: str,
) -> AlgorithmBenchmarkResult:
    """
    Benchmark one search algorithm against an in-memory text.

    Only the algorithm execution is timed. Result construction happens
    after the timer stops so measurement is focused on the search
    operation itself.
    """
    start = perf_counter()

    match_result = run_search(
        algorithm,
        text,
        pattern,
    )

    elapsed_seconds = perf_counter() - start

    return AlgorithmBenchmarkResult(
        algorithm=match_result.algorithm,
        pattern=match_result.pattern,
        text_length=len(text),
        match_count=match_result.match_count,
        positions=match_result.positions,
        elapsed_seconds=elapsed_seconds,
    )


def benchmark_all(
    text: str,
    pattern: str,
) -> BenchmarkResult:
    """
    Run every registered search algorithm against the same
    in-memory text and pattern.

    The algorithms are executed independently but receive identical
    input so their results can be compared fairly.
    """
    if not pattern:
        raise ValueError("Benchmark pattern cannot be empty.")

    results = tuple(
        benchmark_algorithm(
            algorithm,
            text,
            pattern,
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
    )
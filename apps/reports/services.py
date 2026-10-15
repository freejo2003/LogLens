from dataclasses import dataclass
from typing import Iterable

from apps.benchmarks.models import AlgorithmMetric, BenchmarkRun


@dataclass(frozen=True)
class AlgorithmTheory:
    """
    Theoretical complexity and algorithm characteristics used
    by the CIA theoretical-vs-empirical report.
    """

    algorithm: str
    display_name: str
    preprocessing_complexity: str
    search_complexity: str
    overall_complexity: str
    space_complexity: str
    explanation: str


@dataclass(frozen=True)
class AlgorithmAnalysis:
    """
    Combined theoretical and empirical information for one
    algorithm in a persisted benchmark run.
    """

    algorithm: str
    display_name: str

    preprocessing_complexity: str
    search_complexity: str
    overall_complexity: str
    space_complexity: str
    explanation: str

    text_length: int
    pattern_length: int
    match_count: int

    preprocessing_median_seconds: float
    search_median_seconds: float
    total_median_seconds: float

    preprocessing_minimum_seconds: float
    preprocessing_maximum_seconds: float
    search_minimum_seconds: float
    search_maximum_seconds: float
    total_minimum_seconds: float
    total_maximum_seconds: float

    trial_count: int
    warmup_runs: int

    verification_count: int
    collision_count: int
    peak_memory_bytes: int | None

    @property
    def total_median_milliseconds(self) -> float:
        return self.total_median_seconds * 1000

    @property
    def preprocessing_median_milliseconds(self) -> float:
        return self.preprocessing_median_seconds * 1000

    @property
    def search_median_milliseconds(self) -> float:
        return self.search_median_seconds * 1000


@dataclass(frozen=True)
class BenchmarkAnalysis:
    """
    Structured theoretical-vs-empirical analysis of a completed
    BenchmarkRun.
    """

    benchmark_id: int
    pattern: str
    pattern_length: int
    text_length: int

    source_name: str
    source_checksum: str
    input_checksum: str

    status: str
    positions_consistent: bool

    warmup_runs: int
    trial_count: int

    algorithms: tuple[AlgorithmAnalysis, ...]

    @property
    def fastest_algorithm(self) -> AlgorithmAnalysis | None:
        if not self.algorithms:
            return None

        return min(
            self.algorithms,
            key=lambda item: item.total_median_seconds,
        )

    @property
    def slowest_algorithm(self) -> AlgorithmAnalysis | None:
        if not self.algorithms:
            return None

        return max(
            self.algorithms,
            key=lambda item: item.total_median_seconds,
        )

    @property
    def speedup_over_slowest(self) -> float | None:
        fastest = self.fastest_algorithm
        slowest = self.slowest_algorithm

        if fastest is None or slowest is None:
            return None

        if fastest.total_median_seconds <= 0:
            return None

        return (
            slowest.total_median_seconds
            / fastest.total_median_seconds
        )


ALGORITHM_THEORY: dict[str, AlgorithmTheory] = {
    "naive": AlgorithmTheory(
        algorithm="naive",
        display_name="Naive",
        preprocessing_complexity="O(1)",
        search_complexity="O(nm)",
        overall_complexity="O(nm)",
        space_complexity="O(1)",
        explanation=(
            "The Naive algorithm compares the pattern at each possible "
            "text position. In the worst case, up to m characters may be "
            "checked at each of the n possible alignments."
        ),
    ),
    "kmp": AlgorithmTheory(
        algorithm="kmp",
        display_name="KMP",
        preprocessing_complexity="O(m)",
        search_complexity="O(n)",
        overall_complexity="O(n + m)",
        space_complexity="O(m)",
        explanation=(
            "KMP preprocesses the pattern into a failure table and uses "
            "that information to avoid rechecking characters after a "
            "mismatch. The resulting search phase is linear in the text."
        ),
    ),
    "rabin_karp": AlgorithmTheory(
        algorithm="rabin_karp",
        display_name="Rabin-Karp",
        preprocessing_complexity="O(m)",
        search_complexity="O(n) expected",
        overall_complexity="O(n + m) expected; O(nm) worst case",
        space_complexity="O(m)",
        explanation=(
            "Rabin-Karp uses a rolling hash to identify candidate matches. "
            "Under normal hash behavior the expected search cost is linear, "
            "while excessive hash collisions can require character-level "
            "verification and produce the O(nm) worst case."
        ),
    ),
}


def get_algorithm_theory(algorithm: str) -> AlgorithmTheory:
    """
    Return the theoretical description for a registered algorithm.
    """
    try:
        return ALGORITHM_THEORY[algorithm]
    except KeyError as exc:
        raise ValueError(
            f"No theoretical complexity definition exists "
            f"for algorithm '{algorithm}'."
        ) from exc


def _metric_to_analysis(
    *,
    metric: AlgorithmMetric,
    pattern_length: int,
    warmup_runs: int,
    trial_count: int,
) -> AlgorithmAnalysis:
    theory = get_algorithm_theory(metric.algorithm)

    return AlgorithmAnalysis(
        algorithm=metric.algorithm,
        display_name=theory.display_name,

        preprocessing_complexity=(
            theory.preprocessing_complexity
        ),
        search_complexity=theory.search_complexity,
        overall_complexity=theory.overall_complexity,
        space_complexity=theory.space_complexity,
        explanation=theory.explanation,

        text_length=metric.text_length,
        pattern_length=pattern_length,
        match_count=metric.match_count,

        preprocessing_median_seconds=(
            metric.preprocessing_median_seconds
        ),
        search_median_seconds=(
            metric.search_median_seconds
        ),
        total_median_seconds=(
            metric.total_median_seconds
        ),

        preprocessing_minimum_seconds=(
            metric.preprocessing_minimum_seconds
        ),
        preprocessing_maximum_seconds=(
            metric.preprocessing_maximum_seconds
        ),
        search_minimum_seconds=(
            metric.search_minimum_seconds
        ),
        search_maximum_seconds=(
            metric.search_maximum_seconds
        ),
        total_minimum_seconds=(
            metric.total_minimum_seconds
        ),
        total_maximum_seconds=(
            metric.total_maximum_seconds
        ),

        trial_count=trial_count,
        warmup_runs=warmup_runs,

        verification_count=metric.verification_count,
        collision_count=metric.collision_count,
        peak_memory_bytes=metric.peak_memory_bytes,
    )


def build_benchmark_analysis(
    benchmark: BenchmarkRun,
) -> BenchmarkAnalysis:
    """
    Build a theoretical-vs-empirical analysis from a persisted
    BenchmarkRun.

    This function does not rerun any algorithm. It uses only the
    benchmark configuration and persisted AlgorithmMetric records.
    """
    if benchmark.status != BenchmarkRun.Status.SUCCEEDED:
        raise ValueError(
            "Only successful benchmark runs can be analyzed."
        )

    metrics = tuple(
        benchmark.algorithm_metrics
        .all()
        .order_by("algorithm")
    )

    if not metrics:
        raise ValueError(
            "The benchmark run does not contain algorithm metrics."
        )

    pattern_length = len(benchmark.pattern)

    algorithms = tuple(
        _metric_to_analysis(
            metric=metric,
            pattern_length=pattern_length,
            warmup_runs=(
                metric.warmup_runs
            ),
            trial_count=(
                metric.trial_count
            ),
        )
        for metric in metrics
    )

    source_name = ""

    if benchmark.source_file is not None:
        source_name = benchmark.source_file.original_name

    return BenchmarkAnalysis(
        benchmark_id=benchmark.pk,
        pattern=benchmark.pattern,
        pattern_length=pattern_length,
        text_length=benchmark.text_length,

        source_name=source_name,
        source_checksum=benchmark.source_checksum,
        input_checksum=benchmark.input_checksum,

        status=benchmark.status,
        positions_consistent=(
            benchmark.positions_consistent
        ),

        warmup_runs=min(
            algorithm.warmup_runs
            for algorithm in algorithms
        ),
        trial_count=min(
            algorithm.trial_count
            for algorithm in algorithms
        ),

        algorithms=get_empirical_order(algorithms),
    )


def build_analysis_for_owner(
    *,
    benchmark_id: int,
    owner,
) -> BenchmarkAnalysis:
    """
    Retrieve and analyze a benchmark belonging to the supplied owner.

    Ownership is enforced at the database query level.
    """
    benchmark = (
        BenchmarkRun.objects
        .filter(
            pk=benchmark_id,
            owner=owner,
        )
        .prefetch_related("algorithm_metrics")
        .first()
    )

    if benchmark is None:
        raise BenchmarkRun.DoesNotExist(
            f"Benchmark run {benchmark_id} was not found."
        )

    return build_benchmark_analysis(benchmark)


def calculate_relative_time(
    *,
    baseline_seconds: float,
    comparison_seconds: float,
) -> float | None:
    """
    Calculate how many times faster the baseline is compared with
    the comparison measurement.

    Example:
        baseline = 0.10
        comparison = 0.20

        result = 2.0

    Meaning the comparison took approximately twice as long.
    """
    if baseline_seconds <= 0:
        return None

    return comparison_seconds / baseline_seconds


def calculate_percentage_difference(
    *,
    baseline_seconds: float,
    comparison_seconds: float,
) -> float | None:
    """
    Calculate the percentage increase/decrease of comparison time
    relative to a baseline.
    """
    if baseline_seconds <= 0:
        return None

    return (
        (
            comparison_seconds
            - baseline_seconds
        )
        / baseline_seconds
    ) * 100


def get_empirical_order(
    analyses: Iterable[AlgorithmAnalysis],
) -> tuple[AlgorithmAnalysis, ...]:
    """
    Return algorithms ordered from fastest to slowest according
    to median total benchmark time.
    """
    return tuple(
        sorted(
            analyses,
            key=lambda item: item.total_median_seconds,
        )
    )

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class MatchResult:
    """
    Result of a pattern-matching operation.

    Positions are zero-based character offsets in the input text.
    """

    algorithm: str
    pattern: str
    positions: tuple[int, ...]

    @property
    def match_count(self) -> int:
        return len(self.positions)


@dataclass(frozen=True)
class PreparedSearch:
    """
    Prepared state for benchmark-oriented execution.

    The prepared state contains algorithm-specific preprocessing
    information. The search phase consumes this state without repeating
    the preprocessing work.
    """

    algorithm: str
    pattern: str
    state: object


@dataclass(frozen=True)
class RabinKarpSearchResult:
    """
    Detailed Rabin-Karp search result.

    collision_count counts hash matches that required character
    verification but were not actual pattern matches.

    verification_count counts every candidate position whose hash
    matched and therefore required character-by-character verification.
    """

    positions: tuple[int, ...]
    collision_count: int
    verification_count: int


MatchFunction = Callable[[str, str], list[int]]


class SearchMatchLimitError(ValueError):
    """Raised when a search would return more offsets than allowed."""


def _append_match(positions: list[int], position: int, max_matches: int | None) -> None:
    if max_matches is not None and len(positions) >= max_matches:
        raise SearchMatchLimitError(
            "The search exceeds the configured match-result limit. Narrow the source text or use a more specific pattern."
        )
    positions.append(position)


def naive_search(
    text: str,
    pattern: str,
    *,
    max_matches: int | None = None,
    max_start: int | None = None,
) -> list[int]:
    """
    Find all occurrences of pattern in text using the Naive
    String Matching algorithm.

    Overlapping matches are included.

    Example:
        naive_search("AAAA", "AA") -> [0, 1, 2]
    """
    if pattern == "":
        return []

    text_length = len(text)
    pattern_length = len(pattern)

    if pattern_length > text_length:
        return []

    positions: list[int] = []

    candidate_count = text_length - pattern_length + 1
    if max_start is not None:
        candidate_count = min(candidate_count, max(0, max_start))

    for start in range(candidate_count):
        match = True

        for offset in range(pattern_length):
            if text[start + offset] != pattern[offset]:
                match = False
                break

        if match:
            _append_match(positions, start, max_matches)

    return positions


def build_kmp_failure_table(pattern: str) -> list[int]:
    """
    Build the KMP failure/LPS table.

    LPS = Longest Proper Prefix which is also a Suffix.
    """
    if pattern == "":
        return []

    lps = [0] * len(pattern)

    prefix_length = 0
    current = 1

    while current < len(pattern):
        if pattern[current] == pattern[prefix_length]:
            prefix_length += 1
            lps[current] = prefix_length
            current += 1

        elif prefix_length > 0:
            prefix_length = lps[prefix_length - 1]

        else:
            lps[current] = 0
            current += 1

    return lps


def kmp_search_prepared(
    text: str,
    pattern: str,
    lps: list[int],
    *,
    max_matches: int | None = None,
    max_start: int | None = None,
) -> list[int]:
    """
    Execute KMP search using an already prepared LPS table.
    """
    if pattern == "":
        return []

    if len(pattern) > len(text):
        return []

    positions: list[int] = []

    text_index = 0
    pattern_index = 0

    while text_index < len(text):
        if text[text_index] == pattern[pattern_index]:
            text_index += 1
            pattern_index += 1

            if pattern_index == len(pattern):
                match_start = text_index - pattern_index
                if max_start is None or match_start < max_start:
                    _append_match(positions, match_start, max_matches)

                # Continue searching so overlapping matches are found.
                pattern_index = lps[pattern_index - 1]

        elif pattern_index > 0:
            pattern_index = lps[pattern_index - 1]

        else:
            text_index += 1

    return positions


def kmp_search(
    text: str, pattern: str, *, max_matches: int | None = None
) -> list[int]:
    """
    Find all occurrences of pattern in text using Knuth-Morris-Pratt.

    Overlapping matches are included.
    """
    if pattern == "":
        return []

    if len(pattern) > len(text):
        return []

    lps = build_kmp_failure_table(pattern)

    return kmp_search_prepared(
        text,
        pattern,
        lps,
        max_matches=max_matches,
    )


def _rabin_karp_prepare(pattern: str) -> tuple[int, int, int]:
    """
    Prepare Rabin-Karp pattern hash state.

    Returns:
        pattern_hash
        highest_power
        modulus
    """
    if pattern == "":
        return 0, 0, 1

    base = 256
    modulus = 1_000_000_007

    pattern_hash = 0

    for character in pattern:
        pattern_hash = (
            pattern_hash * base + ord(character)
        ) % modulus

    highest_power = pow(
        base,
        len(pattern) - 1,
        modulus,
    )

    return pattern_hash, highest_power, modulus


def _rabin_karp_search_prepared(
    text: str,
    pattern: str,
    prepared_state: tuple[int, int, int],
    *,
    max_matches: int | None = None,
    max_start: int | None = None,
) -> RabinKarpSearchResult:
    """
    Execute Rabin-Karp using already prepared pattern state.
    """
    if pattern == "":
        return RabinKarpSearchResult(
            positions=(),
            collision_count=0,
            verification_count=0,
        )

    text_length = len(text)
    pattern_length = len(pattern)

    if pattern_length > text_length:
        return RabinKarpSearchResult(
            positions=(),
            collision_count=0,
            verification_count=0,
        )

    pattern_hash, highest_power, modulus = prepared_state

    base = 256

    window_hash = 0

    for index in range(pattern_length):
        window_hash = (
            window_hash * base + ord(text[index])
        ) % modulus

    positions: list[int] = []

    collision_count = 0
    verification_count = 0

    candidate_count = text_length - pattern_length + 1
    if max_start is not None:
        candidate_count = min(candidate_count, max(0, max_start))

    for start in range(candidate_count):
        if window_hash == pattern_hash:
            verification_count += 1

            if text[
                start : start + pattern_length
            ] == pattern:
                _append_match(positions, start, max_matches)
            else:
                collision_count += 1

        if start < candidate_count - 1:
            outgoing = ord(text[start])
            incoming = ord(
                text[start + pattern_length]
            )

            window_hash = (
                (
                    window_hash
                    - outgoing * highest_power
                )
                * base
                + incoming
            ) % modulus

    return RabinKarpSearchResult(
        positions=tuple(positions),
        collision_count=collision_count,
        verification_count=verification_count,
    )


def rabin_karp_search(
    text: str, pattern: str, *, max_matches: int | None = None
) -> list[int]:
    """
    Find all occurrences of pattern in text using Rabin-Karp.

    A rolling hash identifies candidate positions. Candidates are
    verified character-by-character to avoid returning false matches
    caused by hash collisions.

    Overlapping matches are included.
    """
    prepared_state = _rabin_karp_prepare(pattern)

    result = _rabin_karp_search_prepared(
        text,
        pattern,
        prepared_state,
        max_matches=max_matches,
    )

    return list(result.positions)


def prepare_search(
    algorithm: str,
    pattern: str,
) -> PreparedSearch:
    """
    Prepare algorithm-specific search state.

    Naive string matching has no preprocessing requirement.

    KMP prepares the LPS/failure table.

    Rabin-Karp prepares the pattern hash and highest rolling-hash
    power.
    """
    if pattern == "":
        raise ValueError("Search pattern cannot be empty.")

    if algorithm == "naive":
        state = None

    elif algorithm == "kmp":
        state = build_kmp_failure_table(pattern)

    elif algorithm == "rabin_karp":
        state = _rabin_karp_prepare(pattern)

    else:
        supported = ", ".join(sorted(ALGORITHMS))
        raise ValueError(
            f"Unsupported search algorithm '{algorithm}'. "
            f"Supported algorithms: {supported}."
        )

    return PreparedSearch(
        algorithm=algorithm,
        pattern=pattern,
        state=state,
    )


def search_prepared(
    prepared: PreparedSearch,
    text: str,
    *,
    max_matches: int | None = None,
    max_start: int | None = None,
) -> MatchResult:
    """
    Execute a prepared search.

    Preprocessing is not repeated.
    """
    algorithm = prepared.algorithm
    pattern = prepared.pattern

    if algorithm == "naive":
        positions = naive_search(
            text,
            pattern,
            max_matches=max_matches,
            max_start=max_start,
        )

    elif algorithm == "kmp":
        positions = kmp_search_prepared(
            text,
            pattern,
            prepared.state,
            max_matches=max_matches,
            max_start=max_start,
        )

    elif algorithm == "rabin_karp":
        detailed_result = _rabin_karp_search_prepared(
            text,
            pattern,
            prepared.state,
            max_matches=max_matches,
            max_start=max_start,
        )
        positions = list(detailed_result.positions)

    else:
        supported = ", ".join(sorted(ALGORITHMS))
        raise ValueError(
            f"Unsupported search algorithm '{algorithm}'. "
            f"Supported algorithms: {supported}."
        )

    return MatchResult(
        algorithm=algorithm,
        pattern=pattern,
        positions=tuple(positions),
    )


def rabin_karp_search_detailed(
    text: str,
    pattern: str,
    *,
    max_matches: int | None = None,
) -> RabinKarpSearchResult:
    """
    Execute Rabin-Karp and return collision/verification counters.
    """
    prepared_state = _rabin_karp_prepare(pattern)

    return _rabin_karp_search_prepared(
        text,
        pattern,
        prepared_state,
        max_matches=max_matches,
    )


ALGORITHMS: dict[str, MatchFunction] = {
    "naive": naive_search,
    "kmp": kmp_search,
    "rabin_karp": rabin_karp_search,
}


def run_search(
    algorithm: str,
    text: str,
    pattern: str,
    *,
    max_matches: int | None = None,
) -> MatchResult:
    """
    Execute one registered search algorithm and return
    a normalized MatchResult.

    This compatibility API performs any required preprocessing
    internally, preserving the original behavior.
    """
    prepared = prepare_search(
        algorithm,
        pattern,
    )

    return search_prepared(
        prepared,
        text,
        max_matches=max_matches,
    )

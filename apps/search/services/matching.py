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


MatchFunction = Callable[[str, str], list[int]]


def naive_search(text: str, pattern: str) -> list[int]:
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

    for start in range(text_length - pattern_length + 1):
        match = True

        for offset in range(pattern_length):
            if text[start + offset] != pattern[offset]:
                match = False
                break

        if match:
            positions.append(start)

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


def kmp_search(text: str, pattern: str) -> list[int]:
    """
    Find all occurrences of pattern in text using Knuth-Morris-Pratt.

    Overlapping matches are included.
    """
    if pattern == "":
        return []

    if len(pattern) > len(text):
        return []

    lps = build_kmp_failure_table(pattern)

    positions: list[int] = []

    text_index = 0
    pattern_index = 0

    while text_index < len(text):
        if text[text_index] == pattern[pattern_index]:
            text_index += 1
            pattern_index += 1

            if pattern_index == len(pattern):
                positions.append(text_index - pattern_index)

                # Continue searching so overlapping matches are found.
                pattern_index = lps[pattern_index - 1]

        elif pattern_index > 0:
            pattern_index = lps[pattern_index - 1]

        else:
            text_index += 1

    return positions


def rabin_karp_search(text: str, pattern: str) -> list[int]:
    """
    Find all occurrences of pattern in text using Rabin-Karp.

    A rolling hash identifies candidate positions. Candidates are
    verified character-by-character to avoid returning false matches
    caused by hash collisions.

    Overlapping matches are included.
    """
    if pattern == "":
        return []

    text_length = len(text)
    pattern_length = len(pattern)

    if pattern_length > text_length:
        return []

    # Polynomial rolling hash parameters.
    base = 256
    modulus = 1_000_000_007

    pattern_hash = 0
    window_hash = 0

    highest_power = pow(
        base,
        pattern_length - 1,
        modulus,
    )

    for index in range(pattern_length):
        pattern_hash = (
            pattern_hash * base + ord(pattern[index])
        ) % modulus

        window_hash = (
            window_hash * base + ord(text[index])
        ) % modulus

    positions: list[int] = []

    for start in range(text_length - pattern_length + 1):
        if window_hash == pattern_hash:
            if text[
                start : start + pattern_length
            ] == pattern:
                positions.append(start)

        if start < text_length - pattern_length:
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

    return positions


ALGORITHMS: dict[str, MatchFunction] = {
    "naive": naive_search,
    "kmp": kmp_search,
    "rabin_karp": rabin_karp_search,
}


def run_search(
    algorithm: str,
    text: str,
    pattern: str,
) -> MatchResult:
    """
    Execute one registered search algorithm and return
    a normalized MatchResult.
    """
    try:
        matcher = ALGORITHMS[algorithm]
    except KeyError as exc:
        supported = ", ".join(sorted(ALGORITHMS))
        raise ValueError(
            f"Unsupported search algorithm '{algorithm}'. "
            f"Supported algorithms: {supported}."
        ) from exc

    positions = matcher(text, pattern)

    return MatchResult(
        algorithm=algorithm,
        pattern=pattern,
        positions=tuple(positions),
    )
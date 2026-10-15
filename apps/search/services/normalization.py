import unicodedata


UNICODE_NORMALIZATION_CHOICES = (
    ("none", "None"),
    ("NFC", "Canonical composition (NFC)"),
    ("NFD", "Canonical decomposition (NFD)"),
    ("NFKC", "Compatibility composition (NFKC)"),
    ("NFKD", "Compatibility decomposition (NFKD)"),
)
VALID_NORMALIZATIONS = frozenset(
    value for value, _label in UNICODE_NORMALIZATION_CHOICES
)


def normalize_search_text(
    value: str,
    *,
    case_sensitive: bool = True,
    unicode_normalization: str = "none",
) -> str:
    """Apply the exact Unicode and case settings used by search and benchmarks."""
    if unicode_normalization not in VALID_NORMALIZATIONS:
        raise ValueError("Unsupported Unicode normalization form.")
    normalized = (
        value
        if unicode_normalization == "none"
        else unicodedata.normalize(unicode_normalization, value)
    )
    return normalized if case_sensitive else normalized.casefold()

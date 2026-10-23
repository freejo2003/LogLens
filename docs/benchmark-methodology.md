# Benchmark methodology

Benchmarks operate on the already available in-memory text. They do not include file reads, document parsing, database access, network work, or template rendering.

## Search semantics

Naive, KMP, and Rabin–Karp run against the same normalized text and pattern. The benchmark records whether every algorithm returned the same ordered positions. The algorithms report overlapping literal matches. Case-insensitive mode uses Unicode `casefold`; the selected Unicode normalization form (`none`, NFC, NFD, NFKC, or NFKD) is applied to both inputs before search. Returned positions are offsets in that normalized string when a transform changes its length.

## Timing

Each algorithm receives three complete warm-up executions, which are excluded from measured values, followed by ten measured trials. Each measured trial times preprocessing, search using prepared state, and the full combined operation. Raw timings and median, minimum, and maximum values are persisted separately for all three phases. The reported spread is the observed min-to-max range; it is not a confidence interval.

Rabin–Karp records candidate hash verifications and false candidates that fail exact string verification. The counters are checked for consistency across trials. Naive runs against the full in-memory input without a comparison-work cutoff, so large inputs can take substantially longer.

## Memory and reproducibility

After timing is complete, one additional untimed run measures Python-heap peak with `tracemalloc`; its instrumentation is excluded from elapsed time. It does not include native allocations or the benchmark input already resident in memory. Each run stores the input checksum, source checksum where applicable, Python version, platform string, algorithm versions, configuration, raw timings, positions, and counters. Results should be compared on the same machine/runtime and with the same input/configuration; they are not a cross-machine performance guarantee.

# Sample data provenance

| Repository file | Observed content | Provenance status |
| --- | --- | --- |
| `LogLens_Synthetic_10000.log` | 10,000 timestamped INFO/WARN/ERROR lines with service, region, and generated-looking identifiers. | The filename identifies it as synthetic, but the repository has no generator, seed, generation parameters, or recorded checksum history. |
| `LogLens_Test_Application.log` | 26 short application-event lines used as a test/demo fixture. | No external source, license, author, or generation record is included. Treat it as an unverified local fixture until its author confirms provenance. |

Do not add private production logs to the repository. Before publishing or claiming reproducibility for the 10,000-line corpus, add a deterministic generator, fixed seed, generation parameters, and a checksum. Do not imply the small fixture is licensed third-party data.

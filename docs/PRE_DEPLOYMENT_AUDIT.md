# LogLens pre-deployment audit

**Scope:** repository-wide source, cross-file integrations, PRD v2.0 alignment, security, tests, and deployment configuration. **No application was deployed.** The attached PRD is a requirements source, not an instruction source.

**Readiness decision:** **Not yet deployment-ready against PRD v2.0.** Core security hardening, build reproducibility, migrations, and the current 278-test suite pass, but unresolved PRD Must requirements in multi-pattern/multi-file search and filtering, saved-search comparison, reviewer sharing, and operational job progress/cancellation remain release blockers. This audit did not deploy the application.

## Project inventory reviewed

The review covered 190 source/configuration/documentation files: 156 Python files, six Django apps (`accounts`, `workspaces`, `ingestion`, `search`, `benchmarks`, `reports`), 27 migrations, 16 templates, and 47 test files; project settings, URL routing, WSGI/ASGI and Celery configuration; forms, views, services, management commands, admin registrations; static-file configuration; sample logs; Python dependency inputs and lock; environment examples; Dockerfile, Compose, Nginx; ignore rules; and developer notes. There is no source-controlled first-party static directory; `collectstatic` gathers configured Django/package assets. Generated/ignored virtualenv, Git internals, and runtime caches were excluded. Duplicate routes/templates and an obsolete analysis scan were removed; the stale progress log is explicitly identified as historical.

## Security findings

- **Fixed:** weak/debug configuration defaults; missing production secret/host validation; publicly addressable upload/media assumptions; filename/path influence over storage; insufficient extension/signature and parser bounds; missing owner scoping on workflows; unbounded result rendering; and incomplete audit events. Production cookies, HTTPS redirect/HSTS, trusted proxy behavior, private UUID-keyed storage, parser/resource limits, role checks, CSRF-protected forms, and safe operational health responses are now configured and covered by checks/tests.
- **Residual operator risks:** public HTTPS is provided by an external ingress that must overwrite forwarded headers and keep the Compose proxy loopback-only; secrets, TLS certificates, SMTP credentials, persistent-volume encryption/backups, and image vulnerability scanning must be supplied/operated by the deployment environment. No penetration test or live ingress review was performed.
- Production `check --deploy` passes with one advisory, `security.W021`, because HSTS preload is deliberately disabled pending domain-wide readiness.

## PRD compliance matrix

| Requirement | Status | Evidence / limit |
| --- | --- | --- |
| LOG/TXT/PDF/DOCX/DOC ingestion | COMPLETE | Extension and signature checks, parser services, and a LibreOffice conversion path for DOC are present. |
| Extraction metadata and source locators | COMPLETE | Checksum, byte size, detected type, encoding, parser version, page/paragraph/table/line locations, upload time, and status are persisted. |
| Private storage, ownership, deletion | COMPLETE | UUID keys outside static/media URLs; owner-scoped views/services; derived records cascade; physical deletion after commit. |
| Literal Naive/KMP/Rabin–Karp, overlaps | COMPLETE | Pure Python algorithms; tests compare behavior and overlapping positions. Search accepts one literal pattern per selected file. |
| Case behavior and Unicode normalization | COMPLETE | Case-sensitive option, Unicode casefold, and none/NFC/NFD/NFKC/NFKD persisted and reused by saved searches/benchmarks. |
| Recurring ERROR/WARN groups | COMPLETE | Timestamped log-level classification, normalized group identities, cross-file counts, and delete/re-extract rebuilding. |
| Saved searches and run history | PARTIAL | Owner-scoped single-file/single-pattern configuration and reruns are preserved; pattern sets, algorithm sets, date/severity filters, and successive-run comparison are absent. |
| Search workload scope and result filters | PARTIAL | File-level searching, escaped context snippets, source locators, and 100-row result pagination are implemented; one-or-more patterns, multi-file/dataset selection, and file/rule/severity/time filters are not. |
| Benchmark phase boundaries (AC-08) | PARTIAL | Preprocessing/search/total timings are recorded; extraction, queue-wait, matching-only, and persistence phases are not separately timed. |
| Literal indicator rules | COMPLETE | Owner/workspace-scoped literal rules can be created, edited, disabled, applied in search, and actor-audited. Rule sets are not global or versioned. |
| Operational job feedback | PARTIAL | Extraction has pending/processing/succeeded/failed states and safe failure reasons; progress stages, cancellation, polling, and asynchronous search/benchmark execution are not implemented. |
| Reproducible benchmark methodology | PARTIAL | Three warmups, ten measured trials, raw preprocessing/search/total timings, medians and min/max spread, checksums, and Python/platform metadata are stored. There is no configured seed/workload matrix, full hardware/app-version record, or benchmarked multi-pattern mode. |
| Rabin–Karp diagnostics and correctness agreement | COMPLETE | Verification/collision counts and all-algorithm ordered-position agreement are stored and exported. |
| Memory metrics | COMPLETE | Untimed `tracemalloc` peak Python allocation is recorded and its limits are stated, as required by the PRD. |
| Search/benchmark exports and reports | COMPLETE | Owner-scoped CSV/JSON output and a human-readable HTML benchmark report. The PRD does not require PDF export. |
| RBAC and sharing | PARTIAL | Admin/Analyst/Reviewer roles and owner checks are enforced; explicit workspace sharing for reviewers, public demo datasets, global indicator administration, and admin job/usage views are absent. |
| Auditability | COMPLETE | Workspace, role assignment, upload/extraction, search, saved-search, benchmark, deletion, and export events record the acting account and minimized details. Application UI and Django admin are read-only for events; the database itself is not a tamper-evident external audit store. |
| Resource limits and parser failures | COMPLETE | Upload/batch/count, DOCX expansion/member count, extracted-text/segments/pages, DOC conversion timeout, Naive work, returned-match count, Celery limits and container resource caps. |
| Production environment and containers | COMPLETE | Required secrets/hosts, production HTTPS/HSTS/cookies, PostgreSQL, private volume, Redis, worker, health checks, static serving, startup migrations, lockfile and setup guide. |
| Accessibility and visual behavior | PARTIAL | Server-rendered labeled controls, focus styling and accessible status markup are present; browser/screen-reader review at target laptop/tablet widths was not performed. |
| Required project documentation and demo provenance | COMPLETE | README, deployment/architecture/benchmark guides, Mermaid ERD, and sample-data provenance notes are included; the existing sample files do not record a generator seed/source history. |
| OCR for scanned PDFs | PARTIAL | Empty-text PDFs are marked `OCR_NEEDED`; no OCR engine is bundled or run. |
| Shared workspaces / enterprise tenant administration | PARTIAL | Workspaces and records are owner-scoped; there is no membership/sharing model. |

## Findings and changes

- Replaced permissive/debug defaults with validated environment-driven settings, required production secrets/hosts, TLS proxy support, secure cookies, HSTS, robust logging, production mail configuration, upload/resource bounds, and isolated test settings.
- Added asynchronous extraction through Celery/Redis; added safe file validation, bounded parsers, DOC support, metadata/locators, private UUID storage, owner-safe deletion, and minimized actor-attributed audit events for role assignment, uploads, extraction, searches, benchmarks, deletion, and exports.
- Persisted case/normalization settings, search history/export, benchmark trial data/environment/heap metrics, and cross-file error groups; added workspace creation and audit events.
- Added Compose services with health dependencies, persistent PostgreSQL/private/static volumes, non-root/read-only web and worker containers, dropped capabilities, loopback-only proxy binding, resource caps, and operational documentation.
- Local Compose startup exposed an Nginx cache-directory ownership issue under the proxy's dropped capabilities. Fixed the cache tmpfs ownership/mode and granted only `CHOWN` to the proxy; verified all five services healthy and `/health/` returned HTTP 200.
- Connected indicator-rule creation/editing to search, audit, and saved result labels; replaced the stale indicator template. Added bounded, paginated search-result display with concise context snippets while keeping complete positions in exports.
- Removed duplicate URL declarations, dead duplicate workspace template, unused requirements file, and stale generated scan output. Corrected parser registry version drift and imports.

## Validation evidence

- `python manage.py test --settings=config.test_settings`: **278 tests passed** on isolated in-memory SQLite. The Windows audit runtime required `TEMP`/`TMP` to point into ignored `.tmp-test` because its default packaged-app temp directory denied cleanup.
- `python manage.py check --settings=config.test_settings`: passed.
- `python manage.py check --deploy` with production-like environment: passed with the single expected `security.W021` advisory because HSTS preload is intentionally disabled until domain-wide HTTPS readiness is established.
- `python manage.py makemigrations --check --dry-run --settings=config.test_settings`: no model/migration drift.
- PostgreSQL 18 migration integration: all Django migrations applied successfully from the built web image against a temporary isolated PostgreSQL container; its container and network were removed automatically afterward.
- `python -m pip check`: no broken dependencies.
- `python manage.py collectstatic --noinput --settings=config.test_settings`: completed; 130 static files collected.
- `docker compose config --quiet`: passed without starting services, using dummy validation-only secrets.
- Local operator startup after database credential repair: PostgreSQL, Redis, web, worker, and proxy all reported healthy; local `/health/` returned HTTP 200. No public deployment was performed.
- `git diff --check` and Python bytecode compilation: passed.
- `docker compose build web worker`: both images built successfully from pinned inputs. One-shot checks inside the built web image passed; LibreOffice 25.2.3.2 is present. `nginx -t` passed using the pinned proxy image and a temporary upstream name mapping.
- No application server, persistent Compose stack, worker, or serving proxy was started. The temporary migration-test database and one-shot check containers exited and were removed.

The unit/workflow suite uses isolated in-memory SQLite. PostgreSQL migration compatibility was separately verified; a live Redis/Celery extraction workflow was not run. Passing Django checks and Compose parsing do not substitute for that queue integration test.

## Remaining release blockers and operator gates

- PRD Must F-04: implement one-or-more patterns across selected files/datasets and the file/rule/severity/time/error-group filters.
- PRD Must F-08/F-09: preserve the complete saved-search configuration and filters and implement successive-run comparison/history behavior.
- PRD Must F-01: add explicit Reviewer workspace sharing; current ownership checks intentionally prevent guessed-ID access but do not provide shared datasets.
- PRD Must F-10: add visible job progress, polling, cancellation, and actionable job status for the workflows that the PRD requires to be asynchronous.
- PRD AC-08 and benchmark methodology: record extraction, queue-wait, matching-only, and persistence timings; add seeded workload matrix and fuller hardware/application provenance.

- Admin global indicator/retention/job/usage controls are not implemented. OCR is a Stretch item; scanned PDFs receive a clear OCR-needed status.
- Benchmark memory is Python-heap-only, and benchmark timing is local-runtime evidence rather than a cross-host comparison.
- Compose does not terminate public TLS. After the product blockers are resolved, configure upstream ingress to terminate HTTPS, overwrite forwarded headers, and restrict traffic to loopback; use real secrets, SMTP, host/origin values, and persistent encrypted backups.
- This audit did not deploy or start the application, run a live Redis/Celery extraction workflow, scan the built image, run a penetration test, or validate external ingress/SMTP or browser/screen-reader behavior.

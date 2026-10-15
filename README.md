# LogLens

LogLens is a Django application for privately ingesting log and document files, extracting searchable text with source locations, running literal string searches, grouping recurring `ERROR`/`WARN` messages, and comparing Naive, KMP, and Rabin–Karp search performance.

## Capabilities

- Supports `.log`, `.txt`, `.pdf`, `.docx`, and legacy `.doc` uploads.
- Keeps source files in private storage and scopes workspaces, files, searches, saved searches, benchmarks, and reports to their owner.
- Uses Celery and Redis for asynchronous extraction. PDF, DOCX, and text extraction retain page, paragraph, or line locators where available.
- Supports overlapping matches, case-sensitive or Unicode-casefold matching, and configurable Unicode normalization.
- Bounds returned matches per search or benchmark to prevent repetitive input from creating unbounded result arrays.
- Stores search history and reproducible benchmark runs with three warmups, ten measured trials, phase timings, medians, min/max spread, match agreement, Rabin–Karp diagnostics, runtime metadata, and Python-heap estimates.
- Includes Admin, Analyst, and Reviewer application roles, minimized audit events, CSV/JSON exports, and HTML analysis reports.

## Local development

Python 3.14 and PostgreSQL are the project defaults. The test settings use isolated in-memory SQLite so the test suite does not require a developer PostgreSQL service.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Edit `.env` for the local PostgreSQL credentials before migrating. For development, set `DJANGO_ENV=development`, `DJANGO_DEBUG=true`, `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`, and a matching local CSRF origin. A Django superuser has the LogLens Admin role automatically; create other accounts in Django Admin and assign their LogLens roles from **Manage Roles**. See the [deployment guide](docs/DEPLOYMENT.md) for the containerized setup.

## Tests and checks

```powershell
python manage.py test --settings=config.test_settings
python manage.py check --settings=config.test_settings
python manage.py makemigrations --check --dry-run --settings=config.test_settings
python -m pip check
```

See [benchmark methodology](docs/benchmark-methodology.md), [architecture](docs/architecture.md), [entity relationship diagram](docs/erd.md), [sample-data provenance](docs/sample-data.md), [deployment](docs/DEPLOYMENT.md), and the [pre-deployment audit](docs/PRE_DEPLOYMENT_AUDIT.md).

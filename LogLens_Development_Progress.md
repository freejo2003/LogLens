# LogLens — Development Progress Log

**Project:** LogLens  
**Course:** Advanced Algorithms Theory — CIA III, Component 1  
**Date started:** 08 October 2026  
**Current status:** Foundation setup completed; development paused.

---

## 1. Project Definition

LogLens is a browser-based log/document analysis application designed to:

- Upload multiple log/document formats.
- Extract searchable text.
- Search literal patterns and configurable indicators.
- Group recurring errors.
- Compare three string-matching algorithms:
  - Naive string matching
  - Knuth-Morris-Pratt (KMP)
  - Rabin-Karp
- Record benchmark results and supporting metadata.
- Provide reproducible algorithm comparisons using in-memory text.

The authoritative project requirements are defined in:

`LogLens_Product_Requirements_Document.pdf`

---

## 2. PRD Technology Stack

The planned primary stack is:

- Python 3.x
- Django
- Django templates
- Bootstrap
- Lightweight JavaScript
- PostgreSQL
- Celery
- Redis
- pypdf
- python-docx
- LibreOffice for legacy DOC conversion
- Optional Tesseract OCR
- Docker Compose
- Git
- Hosted Git service / CI

The logical architecture is:

```text
Browser
   |
   v
Django
   |
   +--> PostgreSQL
   |
   +--> Private file storage
   |
   +--> Celery --> Redis
   |
   +--> Extraction / parsing
   |
   +--> Matching algorithms
```

---

# 3. Initial Environment Verification

The project was developed on Windows using VS Code and PowerShell.

Verified tools:

```text
Python        3.14.6
Git           2.50.1.windows.1
Docker        29.8.1
Docker Compose 5.5.1
VS Code       1.140.0
```

The first `docker info` check showed that the Docker daemon was not running.

Docker Desktop was started and `docker info` was run again successfully.

Docker was confirmed operational with:

- Docker context: `desktop-linux`
- Server version: 29.8.1
- Linux/WSL2 backend
- 12 CPUs
- ~7.4 GiB Docker memory
- 0 containers initially
- 0 images initially

---

# 4. Project Directory Creation

Project root:

```text
C:\Mtech\Advanced Algorithm\CIA III\Component 1\LogLens
```

The project directory was created and entered:

```powershell
mkdir LogLens
cd LogLens
```

Git was initialized:

```powershell
git init
```

A Python virtual environment was created:

```powershell
python -m venv .venv
```

The environment was activated:

```powershell
.\.venv\Scripts\Activate.ps1
```

The active Python version was verified:

```text
Python 3.14.6
```

VS Code was opened from the project directory:

```powershell
code .
```

---

# 5. Django Foundation

Django was installed with:

```powershell
python -m pip install --upgrade pip
python -m pip install "Django==6.1.*"
```

Installed Django version:

```text
Django 6.1.2
```

The Django project was created:

```powershell
django-admin startproject config .
```

Initial Django validation:

```powershell
python manage.py check
```

Result:

```text
System check identified no issues (0 silenced).
```

An initial SQLite migration was performed during the early setup, but SQLite was later removed from the project because PostgreSQL is the intended database baseline.

`db.sqlite3` was deleted.

---

# 6. Git Ignore Configuration

A `.gitignore` file was created to exclude:

- Python cache files
- Virtual environments
- SQLite databases
- Environment files
- Uploaded media
- Generated static files
- IDE files
- OS files
- Logs
- Test/coverage artifacts
- Celery schedule files

Important exclusions include:

```gitignore
.venv/
db.sqlite3
*.sqlite3
.env
.env.*
media/
uploads/
staticfiles/
.vscode/
*.log
.pytest_cache/
.coverage
```

---

# 7. Initial Project Structure

The following directories were created:

```text
apps/
templates/
docs/
deploy/
tests/
```

The application directories were created:

```text
apps/accounts/
apps/workspaces/
apps/ingestion/
apps/search/
apps/benchmarks/
apps/reports/
```

Python package initialization files were added:

```text
apps/__init__.py
apps/accounts/__init__.py
apps/workspaces/__init__.py
apps/ingestion/__init__.py
apps/search/__init__.py
apps/benchmarks/__init__.py
apps/reports/__init__.py
```

The intended project structure follows the PRD's proposed organization.

---

# 8. Environment Configuration Template

Created:

```text
.env.example
```

Initial contents:

```env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=change-me

POSTGRES_DB=loglens
POSTGRES_USER=loglens
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0
```

This serves as the environment-variable template for the project.

---

# 9. Dependency Management

Created:

```text
requirements.txt
requirements-dev.txt
```

Current direct dependency in `requirements.txt`:

```text
Django==6.1.2
```

The virtual environment was inspected using:

```powershell
python -m pip freeze
```

At that stage, installed packages included:

```text
asgiref==3.12.1
Django==6.1.2
sqlparse==0.6.0
tzdata==2026.5
```

The full `pip freeze` output was deliberately not copied into `requirements.txt`; direct project dependencies are being maintained explicitly.

---

# 10. Docker Compose Infrastructure

A `compose.yaml` file was created.

The infrastructure services are:

```text
PostgreSQL 18
Redis 8
```

PostgreSQL configuration:

```text
Database:  loglens
User:      loglens
Password:  loglens_dev_password
Port:      5432
```

Redis:

```text
Port: 6379
```

PostgreSQL uses a named Docker volume:

```text
loglens_postgres_data
```

This volume preserves database data when the containers are stopped.

The Compose configuration was validated with:

```powershell
docker compose config
```

The configuration resolved successfully.

---

# 11. Docker Image Download Issue

The first attempt to start the services:

```powershell
docker compose up -d
```

encountered a Docker Hub network timeout while downloading the PostgreSQL image.

The error was a network/image-download timeout rather than a Compose configuration problem.

Redis eventually downloaded successfully.

PostgreSQL was then pulled directly:

```powershell
docker pull postgres:18
```

The PostgreSQL image downloaded successfully:

```text
Status: Downloaded newer image for postgres:18
```

The services were then started successfully.

---

# 12. PostgreSQL and Redis Running

The following command verified the services:

```powershell
docker compose ps
```

Result:

```text
NAME            IMAGE         SERVICE   STATUS
loglens-db      postgres:18   db        Up
loglens-redis   redis:8       redis     Up
```

Ports:

```text
PostgreSQL -> 5432
Redis      -> 6379
```

At this point the Docker infrastructure was operational.

---

# 13. PostgreSQL Python Driver

The PostgreSQL Python driver was installed:

```powershell
python -m pip install "psycopg[binary]"
```

Installed version:

```text
psycopg 3.3.6
```

It was verified with:

```powershell
python -c "import psycopg; print(psycopg.__version__)"
```

Output:

```text
3.3.6
```

---

# 14. Django PostgreSQL Configuration

Django's original SQLite database configuration was replaced with PostgreSQL configuration.

Current logical configuration:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "loglens",
        "USER": "loglens",
        "PASSWORD": "loglens_dev_password",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

Django was then migrated against PostgreSQL.

---

# 15. Django Core Migrations

The following Django migrations were successfully applied:

```text
contenttypes.0001_initial
auth.0001_initial
admin.0001_initial
admin.0002_logentry_remove_auto_add
admin.0003_logentry_add_action_flag_choices
contenttypes.0002_remove_content_type_name
auth.0002_alter_permission_name_max_length
auth.0003_update_proxy_permissions
auth.0004_alter_user_username_opts
auth.0005_alter_last_login_null
auth.0006_require_contenttypes_0002
auth.0007_alter_validators_add_error_messages
auth.0008_alter_user_username_opts
auth.0009_alter_user_last_name_max_length
auth.0010_alter_group_name_max_length
auth.0011_update_proxy_permissions
auth.0012_update_proxy_permissions
sessions.0001_initial
```

The important result is that Django successfully connected to PostgreSQL and created its core tables there.

---

# 16. PostgreSQL Database Verification

The PostgreSQL database was inspected directly:

```powershell
docker exec -it loglens-db psql -U loglens -d loglens -c "\dt"
```

The following core tables were confirmed:

```text
auth_group
auth_group_permissions
auth_permission
auth_user
auth_user_groups
auth_user_user_permissions
django_admin_log
django_content_type
django_migrations
django_session
```

Therefore:

```text
Django -> psycopg -> PostgreSQL 18
```

is working correctly.

---

# 17. Django Application Creation

The six planned Django applications were generated under `apps/`:

```text
accounts
workspaces
ingestion
search
benchmarks
reports
```

Each contains the standard Django files:

```text
admin.py
apps.py
models.py
tests.py
views.py
__init__.py
```

An initial attempt to run `startapp` again produced conflicts because the directories and some files already existed.

The existing files were retained rather than deleted.

---

# 18. Django App Registration

The six applications were added to `INSTALLED_APPS`:

```python
"apps.accounts",
"apps.workspaces",
"apps.ingestion",
"apps.search",
"apps.benchmarks",
"apps.reports",
```

Initially Django reported:

```text
ModuleNotFoundError: No module named 'accounts'
```

The cause was that the generated `AppConfig.name` values referred to the short module names instead of their actual package paths.

The six `apps.py` files were corrected to use:

```text
apps.accounts
apps.workspaces
apps.ingestion
apps.search
apps.benchmarks
apps.reports
```

After the correction:

```powershell
python manage.py check
```

returned:

```text
System check identified no issues (0 silenced).
```

This confirmed that all six Django applications are correctly recognized.

---

# 19. Workspace Model Started

Development then moved to the first LogLens data model.

The planned model is:

```python
class Workspace(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_workspaces",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
```

This model is intended to establish the ownership boundary for datasets, source files, searches, and benchmark activity.

At the point of pausing, the Workspace model had been prepared as the next implementation step.

A migration for this model had **not yet been confirmed as created or applied** at the time this progress log was written.

---

# 20. Pause / Resume Workflow

A pause/resume workflow was established to avoid unnecessary background resource usage.

## Pause behavior

The project should:

1. Commit repository changes.
2. Stop PostgreSQL and Redis containers.
3. Deactivate the Python virtual environment.

The pause script uses:

```powershell
docker compose stop
deactivate
```

The PostgreSQL Docker volume is intentionally preserved.

The following command must NOT be used for normal pausing:

```powershell
docker compose down -v
```

because `-v` removes the PostgreSQL volume and its stored database data.

## Resume behavior

The project can be resumed with:

```powershell
.\resume-loglens.ps1
```

The resume process:

1. Starts Docker services.
2. Activates `.venv`.
3. Displays Docker service status.

---

# 21. Git Commit Workflow

The pause script was updated to:

1. Display Git status.
2. Prompt for a commit message.
3. Run `git add .`
4. Run `git commit`.
5. Stop Docker services.
6. Deactivate `.venv`.

The intended workflow is:

```text
Work
  |
  v
Run pause-loglens.ps1
  |
  +--> Enter commit message
  |
  +--> Git add
  |
  +--> Git commit
  |
  +--> Stop PostgreSQL + Redis
  |
  +--> Deactivate .venv
  |
  v
Tell ChatGPT: "pause"
  |
  +--> Receive commit message summary
  +--> Receive work-progress summary
```

The script itself cannot understand the full conceptual discussion from the chat, so the detailed human-readable work summary is generated in the chat after the user says `pause`.

---

# 22. Current Project State

At the time of this progress log:

### Working

```text
Python virtual environment
Django
Django project configuration
PostgreSQL 18
Redis 8
Docker Compose
psycopg 3.3.6
Git repository
Six Django applications
PostgreSQL migrations
Django system checks
```

### Django applications

```text
accounts
workspaces
ingestion
search
benchmarks
reports
```

### Database

PostgreSQL is the project's active database.

Core Django tables have been successfully created.

### Not yet implemented

The following major LogLens functionality remains:

- User/account workflow
- Workspace CRUD/UI
- Source file uploads
- File ownership
- Text extraction
- Parser adapters
- Text segments
- Pattern/indicator configuration
- Naive string matching
- KMP
- Rabin-Karp
- Correctness test suite
- Benchmark engine
- Benchmark metadata
- Error grouping
- Search runs
- Match results
- Reports
- Celery worker
- Redis task queue integration
- Bootstrap UI
- Authentication workflow
- Dockerized Django web service
- Full Docker Compose application stack
- Synthetic benchmark corpus
- Documentation
- ERD
- Architecture documentation
- Benchmark methodology
- CI
- Final deployment configuration

---

# 23. Recommended Next Development Sequence

Continue in this order:

```text
1. Finish Workspace model
2. Create/apply Workspace migration
3. Configure authentication/ownership foundation
4. Implement SourceFile and TextSegment models
5. Build ingestion/extraction foundation
6. Implement pure-Python matching engine
   ├── Naive
   ├── KMP
   └── Rabin-Karp
7. Build correctness tests
8. Build search workflow
9. Build benchmark workflow
10. Add Celery + Redis
11. Add reports/error grouping
12. Build UI
13. Add Dockerized web/worker services
14. Add synthetic corpus and reproducibility documentation
15. Final testing and CI
```

The PRD's key algorithm requirement is that benchmark timing must operate on **in-memory text supplied directly to the algorithms**. Database full-text search must not be timed and labeled as Naive, KMP, or Rabin-Karp performance.

---

# 24. Safe Pause / Resume Commands

## Pause

```powershell
.\pause-loglens.ps1
```

## Resume

```powershell
.\resume-loglens.ps1
```

## Never use for a normal pause

```powershell
docker compose down -v
```

because it can delete the PostgreSQL data volume.

---

# 25. Current Milestone

## Milestone: Foundation

**Status: Completed**

The project has progressed from an empty directory to a functioning Django + PostgreSQL + Redis development foundation.

The next active implementation task is the **Workspace data model and its migration**.

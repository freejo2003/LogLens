# Deployment guide

This guide describes how an operator can reproduce a production-oriented Compose setup. It is documentation only; no deployment is performed by the audit.

## Requirements

- Docker Engine with the Compose plugin.
- A host with persistent storage for PostgreSQL data and private uploaded files.
- A TLS ingress/reverse proxy on the host or upstream. Compose deliberately publishes Nginx only on `127.0.0.1`; do not expose its HTTP port directly to the public internet.
- A routable SMTP relay if account email must be sent. The application logs to stdout/stderr for the container runtime to collect.

## Configure secrets and public URLs

Start from the sample, then replace every local-only value. Keep `.env` out of source control and restrict its file permissions. Generate the Django key with a cryptographically secure generator and use an independent random PostgreSQL password. Supply secrets through the deployment secret manager when available.

Production settings must include:

- `DJANGO_ENV=production`, `DJANGO_DEBUG=false`, a unique `DJANGO_SECRET_KEY` of at least 50 characters, and the public hostname plus `localhost,127.0.0.1` in `DJANGO_ALLOWED_HOSTS` (the loopback names are needed for internal health checks).
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://<public-hostname>` and a public ingress that overwrites `X-Forwarded-Proto` with `https`, sets `X-Forwarded-For` to the actual client address, preserves the public `Host`, and sends traffic only to the host-local Compose port. The Nginx login endpoint applies a per-client request limit; do not allow clients to reach it around the ingress.
- `DJANGO_SECURE_SSL_REDIRECT=true`, `DJANGO_SECURE_HSTS_SECONDS=31536000`, `DJANGO_HSTS_INCLUDE_SUBDOMAINS=true`, and `DJANGO_HSTS_PRELOAD=false` unless every subdomain is HTTPS-ready and preload enrollment is an intentional domain-wide decision.
- Strong, independent `POSTGRES_PASSWORD` and URL-safe `REDIS_PASSWORD` values (for example, generated with `secrets.token_urlsafe(48)`); never reuse the local-only values shown in `.env.example`.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and exactly one of `SMTP_USE_TLS` or `SMTP_USE_SSL` for SMTP delivery.

Set `LOGLENS_HTTP_PORT` to an unused loopback port if 8080 is occupied. The application rejects missing production secrets, wildcard hosts, debug mode, disabled HTTPS redirect, and non-positive HSTS duration at startup.

## Clean production-oriented setup

From the repository root, the operator can run the following after editing `.env` with real values and configuring the TLS ingress:

```powershell
Copy-Item .env.example .env
# Edit .env securely before continuing.
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose exec web python manage.py check --deploy
docker compose exec web python manage.py migrate --check
docker compose exec web python manage.py createsuperuser
Invoke-WebRequest http://127.0.0.1:8080/health/
```

Do not use sample credentials or expose port 8080 publicly. A created Django superuser has the LogLens Admin role automatically. Log in through the public TLS hostname, create additional accounts at `/admin/`, and assign them roles at `/accounts/roles/`. The web container applies migrations and collects static files before starting Gunicorn. PostgreSQL and Redis health checks gate web startup; the worker waits for web readiness, and the proxy waits for the web health endpoint. The web and worker containers run as an unprivileged user with read-only root filesystems, dropped Linux capabilities, bounded temporary storage, and resource limits. The Nginx proxy also uses a read-only root filesystem, bounded temporary mounts, dropped capabilities, and explicit CPU, memory, and process limits.

For a local-only Compose trial, use the development values in `.env.example`, which intentionally are not safe for a public deployment. The production-mode Django checks require real, consistent public host/origin values.

## Operations

- Check `docker compose ps` and `docker compose logs --since=15m web worker proxy db redis` for health and operational logs. The health route returns only `ok` or a generic 503 response and does not reveal dependency details.
- Back up PostgreSQL, the `private_media` volume, and the `redis_data` queue volume together on a consistent schedule. Restoring only the database or only uploads leaves broken references; Redis AOF/RDB persistence protects queued extraction work across routine restarts. Protect backups with the same access controls as originals.
- Static files live in the named `static_files` volume. Private originals live in `private_media`; neither is public media.
- Schema changes are versioned under each app's migrations directory. Review a migration before the rollout; `migrate --check` verifies whether migrations remain unapplied. No automatic database rollback is attempted.
- For planned maintenance, stop the proxy first, then web and worker; keep PostgreSQL and private storage until the backup and restore plan is verified.
- The Compose stack has no scheduled retention purge. `retention_until` and `deleted_at` are not currently used for automated retention; deletion is user-driven.
- Keep the image and Python dependency lock current with the repository review cadence. Verify and deliberately refresh the pinned base-image digests, rebuild, and scan the image before releases.
- Container base images are digest-pinned. The application image uses a fixed Debian Trixie snapshot (2026-10-15) for LibreOffice and OS dependencies so rebuilding does not silently pick different packages; APT still verifies signed repository metadata and package checksums. Advance that snapshot and the image digests in a planned security update, then rebuild and scan.

## Capacity and input limits

The defaults allow 25 MiB per file (hard cap 50 MiB), 50 MiB per batch (hard cap 50 MiB, matching the Nginx 52 MiB request-body limit), ten files per request, 100 MiB expanded DOCX data, five million estimated Naive comparisons, 100,000 returned match offsets, 1,000 PDF pages, five MiB extracted text, and 100,000 segments. Celery concurrency is bounded to four worker processes. Container memory/CPU/PID limits are in `compose.yaml`; tune them together with these application caps and load tests before accepting larger workloads.

+

# Render demo hosting

The repository includes a Render Blueprint at `render.yaml`. It creates one Django Docker web service and a separate Render PostgreSQL database. Django serves the rendered pages and static files in the same web service. This demo uses Celery eager mode, so extraction tasks run inline during the web request; no worker or Redis service is created.

## Important demo limits

- The blueprint selects Render's free web and PostgreSQL plans. Free PostgreSQL has a 1 GB limit, no backups, and expires after 30 days. Treat the database as disposable demo data; export anything you need to keep. [Render free service limits](https://render.com/docs/free)
- The free web service may sleep when idle and has limited CPU and memory. Gunicorn uses one worker with two request threads and a five-minute timeout so a long benchmark does not immediately block health checks or get killed at 60 seconds. Larger Naive benchmarks can still exceed the free instance's available compute; use a larger plan or run them locally if they do not finish within five minutes.
- Uploaded originals are stored on the service's local filesystem. They can disappear on restart or redeploy. The separate database keeps extracted records, but an original may be unavailable afterward.
- Extraction/search work executes inline rather than in a durable worker. Benchmarks use a single in-process background thread and report progress in 300-line chunks; only one benchmark can run at a time. A service restart interrupts that run and marks it failed, so it must be started again. The free instance still has limited CPU and memory, and this setup is for a short demonstration, not production.
- SMTP credentials are not configured in this demo. Outbound email features are therefore not ready to use.

## Create the Render services

1. Push the project repository, including `render.yaml`, to a Git provider Render can access.
2. In Render, create a Blueprint from that repository. Review the proposed services: `loglens-web` and `loglens-db`, both on the free plan in Oregon.
3. Create the Blueprint. Render generates `DJANGO_SECRET_KEY` and connects the web service to PostgreSQL over the private network.
4. Wait for the web service to build and deploy. It runs migrations and `collectstatic`, starts Gunicorn on Render's assigned port, and reports readiness through `/health/`.
5. If Render Shell is unavailable, add temporary `LOGLENS_BOOTSTRAP_SUPERUSER=true`, `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` environment variables to the web service. The startup script creates the account once; remove all four variables after the service is live. The bootstrap command never changes an existing account. Then sign in at `/admin/` and confirm CSS and JavaScript load, sign-in works, and a small upload extracts successfully.

The app automatically trusts the `RENDER_EXTERNAL_HOSTNAME` for `ALLOWED_HOSTS` and CSRF. If adding a custom domain, set `DJANGO_ALLOWED_HOSTS` to include it and `DJANGO_CSRF_TRUSTED_ORIGINS` to its full `https://` origin. HTTPS redirect and secure cookies are enabled in production.

Do not create a public media bucket or attach storage credentials for this demo. To retain uploaded originals across deploys, the application will need a separate durable private-storage implementation.

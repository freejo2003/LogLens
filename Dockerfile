FROM python:3.14.8-slim-trixie@sha256:89fb7d3da20043c370643435258bdd7ab755d326d359001d02988ed15ae5219e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources \
    && printf '%s\n' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20261015T000000Z/ trixie main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/20261015T000000Z/ trixie-security main' \
      > /etc/apt/sources.list \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install --no-install-recommends -y libreoffice-writer \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 loglens \
    && useradd --system --uid 10001 --gid loglens --create-home --shell /usr/sbin/nologin loglens \
    && install -d -o loglens -g loglens /app/staticfiles /var/lib/loglens/private_media

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY --chown=loglens:loglens . /app

USER loglens:loglens
EXPOSE 8000


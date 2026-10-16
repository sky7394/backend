# Docker setup

The image uses Python 3.13 (matching pyproject.toml), runs as UID/GID 10001,
and starts Uvicorn without reload. The supplied Compose file is for local
development: it bind-mounts the source and enables Uvicorn reload.

## Start locally

If you do not already have `.env`, copy `.env.example` to `.env`. Set a random
`JWT_SECRET`, for example using `python -c 'import secrets; print(secrets.token_hex(32))'`.
Keep any existing provider credentials in your own `.env`.

`app/core/config.py` has no database credential defaults. Compose defines explicit
development defaults: user/database `gapcode`, password `gapcode_dev_password`.
Override these together with `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.
For this interpolated database URL, use URL-safe values (a hexadecimal random
password is suitable). Existing PostgreSQL volumes retain their original credentials.
Compose overrides `DATABASE_URL` and `REDIS_URL` from `.env` to use `db` and `redis`.

```sh
docker compose config --quiet
docker compose build
docker compose up -d db redis
```

Apply migrations before serving requests. The existing Alembic environment reads
`sqlalchemy.url` from its config rather than `DATABASE_URL`; this command supplies
the container URL explicitly and uses the installed synchronous psycopg2 driver:

```sh
docker compose run --rm -T backend python - <<'PY'
import os
from alembic import command
from alembic.config import Config

config = Config("alembic.ini")
url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
command.upgrade(config, "head")
PY

docker compose up -d backend celery_worker
docker compose ps
docker compose logs -f backend celery_worker
curl --fail http://127.0.0.1:8000/
docker compose exec celery_worker celery -A app.tasks.celery_app inspect registered
```

The worker explicitly imports `app.tasks.exam_tasks` to register `exam.generate`.
PostgreSQL, Redis AOF data, and generated PDFs use named volumes. PostgreSQL and
Redis are not published to the host. The API is published on loopback port 8000
(override `BACKEND_PORT` if needed). `docker compose down` retains named volumes;
`docker compose down --volumes` deletes them.

## Production image

Deploy the built image with its default command, without the development bind
mount or `--reload`. Inject environment variables through your deployment's secret
management, supply production database/Redis URLs, and run migrations once as a
release step. Use an ingress/reverse proxy for TLS and appropriate access controls.
The root endpoint healthcheck checks HTTP liveness, not database readiness.

The virtual environment lives at `/opt/venv`, so the development mount at `/app`
does not hide dependencies. Vazirmatn is installed at the exact system path used
by the PDF renderer; DejaVu and FreeFont are also installed. The runtime includes
DOCX, Arabic reshaping, and bidi dependencies declared in `requirements.txt`.

For reproducible releases, lock all dependencies and pin image digests after your
build has passed deployment tests; the repository currently uses several unpinned
requirements. Docker configuration alone does not harden the app's existing CORS
or exception-response behavior; review those settings before public deployment.

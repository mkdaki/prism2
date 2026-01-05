#!/usr/bin/env sh
set -eu

runMigrations="${RUN_MIGRATIONS:-1}"
retryCount="${MIGRATION_RETRY_COUNT:-30}"
retryDelaySeconds="${MIGRATION_RETRY_DELAY_SECONDS:-1}"

if [ "${runMigrations}" = "1" ] || [ "${runMigrations}" = "true" ]; then
    echo "[entrypoint] RUN_MIGRATIONS=${runMigrations}: applying migrations (alembic upgrade head)"
    attempt=0
    while true; do
        if alembic -c /app/alembic.ini upgrade head; then
            break
        fi

        attempt=$((attempt + 1))
        if [ "${attempt}" -ge "${retryCount}" ]; then
            echo "[entrypoint] migration failed after ${attempt} attempts" >&2
            exit 1
        fi

        echo "[entrypoint] migration failed; retrying in ${retryDelaySeconds}s (attempt ${attempt}/${retryCount})" >&2
        sleep "${retryDelaySeconds}"
    done
else
    echo "[entrypoint] RUN_MIGRATIONS=${runMigrations}: skipping migrations"
fi

exec "$@"



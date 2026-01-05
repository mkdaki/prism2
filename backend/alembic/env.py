import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.models import Base


# Alembic Config object, which provides access to the values within the .ini file.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata is required for 'autogenerate' support.
targetMetadata = Base.metadata


def getDatabaseUrl() -> str:
    """目的: Alembicで利用するDB接続URLを環境変数から取得する。"""
    return os.environ["DATABASE_URL"]


def runMigrationsOffline() -> None:
    """目的: DBへ接続せずに、オフラインでマイグレーションを生成/実行できる設定で動かす。"""
    url = getDatabaseUrl()
    context.configure(
        url=url,
        target_metadata=targetMetadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def runMigrationsOnline() -> None:
    """目的: DBへ接続して、オンラインでマイグレーションを適用する。"""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = getDatabaseUrl()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=targetMetadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    runMigrationsOffline()
else:
    runMigrationsOnline()



"""Database migrations (very small, no Alembic).

Why this exists:
- SQLAlchemy `Base.metadata.create_all()` only creates missing tables; it does NOT
  add missing columns to existing tables.
- When we evolve the schema (e.g. add follower_count), deployments that reuse an
  existing DB (SQLite file volume, persistent Postgres) will start throwing 500s.

This module applies a tiny set of idempotent migrations at startup.
"""

from __future__ import annotations

from typing import Iterable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _get_columns(engine: Engine, table: str) -> set[str]:
    insp = inspect(engine)
    try:
        cols = insp.get_columns(table)
    except Exception:
        # Table may not exist yet
        return set()
    return {c["name"] for c in cols}


def _add_column(engine: Engine, table: str, column_name: str, ddl: str) -> None:
    """Add a column if it does not exist.

    `ddl` should be the column definition part after the column name, e.g.
    "INTEGER DEFAULT 0".
    """

    dialect = engine.dialect.name

    # SQLite doesn't support ADD COLUMN IF NOT EXISTS reliably across versions.
    if dialect == "sqlite":
        existing = _get_columns(engine, table)
        if column_name in existing:
            return
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {ddl}"))
        return

    # Postgres supports IF NOT EXISTS.
    if dialect == "postgresql":
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column_name} {ddl}"))
        return

    # Fallback: best-effort check then ALTER.
    existing = _get_columns(engine, table)
    if column_name in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {ddl}"))


def _ensure_schema_migrations_table(engine: Engine) -> None:
    dialect = engine.dialect.name
    if dialect == "sqlite":
        ddl = "CREATE TABLE IF NOT EXISTS schema_migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, version INTEGER NOT NULL)"
    else:
        ddl = "CREATE TABLE IF NOT EXISTS schema_migrations (id SERIAL PRIMARY KEY, version INTEGER NOT NULL)"

    with engine.begin() as conn:
        conn.execute(text(ddl))


def _get_current_version(engine: Engine) -> int:
    _ensure_schema_migrations_table(engine)
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT version FROM schema_migrations ORDER BY id DESC LIMIT 1")
        ).fetchone()
    return int(row[0]) if row else 0


def _set_version(engine: Engine, version: int) -> None:
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO schema_migrations (version) VALUES (:v)"), {"v": version})


def ensure_schema(engine: Engine) -> None:
    """Bring the DB schema up to date.

    Safe to call repeatedly.
    """

    version = _get_current_version(engine)

    # v1: add follower_count/following_count to agents
    if version < 1:
        _add_column(engine, "agents", "follower_count", "INTEGER DEFAULT 0")
        _add_column(engine, "agents", "following_count", "INTEGER DEFAULT 0")

        # Backfill NULLs (SQLite may leave existing rows as NULL depending on ddl)
        with engine.begin() as conn:
            conn.execute(text("UPDATE agents SET follower_count = 0 WHERE follower_count IS NULL"))
            conn.execute(text("UPDATE agents SET following_count = 0 WHERE following_count IS NULL"))

        _set_version(engine, 1)
        version = 1

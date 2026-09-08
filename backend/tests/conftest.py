"""Shared pytest fixtures for the backend test suite.

Test database strategy
-----------------------
* Tests run against a real PostgreSQL database (never SQLite), because
  several of the behaviors we need confidence in - CHECK constraints,
  UNIQUE constraints - are enforced by Postgres itself and are not
  reliably emulated by other engines.
* The schema is built by running the project's actual Alembic migrations
  against a dedicated test database (default: `adaptive_planner_test`),
  never the development database. This also means our tests exercise the
  same schema Postgres would have in dev/production, catching drift
  between the SQLAlchemy models and the migrations.
* Every test runs inside a SAVEPOINT that is rolled back afterwards, so
  tests never depend on each other or on leftover data, and don't require
  wiping tables by hand.

Environment variables
----------------------
* TEST_DATABASE_URL - overrides the test database connection string.
  Defaults to a local Postgres instance matching the project's existing
  `.env.example` conventions.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env so a locally-added `TEST_DATABASE_URL` line is picked
# up the same way `DATABASE_URL` already is for the app. `override=False`
# means a real shell environment variable (e.g. set in CI) still wins.
load_dotenv(BACKEND_DIR / ".env", override=False)

# `app.config.Settings.database_url` is a required field read from the
# `DATABASE_URL` environment variable / `.env` file, and `alembic/env.py`
# resolves its migration target from that same setting. We pin it to the
# test database *before* importing any app module (including via Alembic)
# so migrations, and any code path that isn't explicitly overridden below,
# can never reach the real development database.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/adaptive_planner_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config


@pytest.fixture(scope="session", autouse=True)
def _test_schema() -> Generator[None, None, None]:
    """Rebuild the test database schema from the real Alembic migrations
    once per test session, so tests never depend on whatever state the
    test database happened to be left in by a previous run.
    """
    config = _alembic_config()

    try:
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    except Exception as exc:  # pragma: no cover - developer-facing message
        pytest.exit(
            "Could not prepare the test database. Is PostgreSQL running "
            f"and reachable at {TEST_DATABASE_URL!r}? "
            f"(set TEST_DATABASE_URL to override)\nOriginal error: {exc}"
        )

    yield


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """A Session bound to a single connection, wrapped in an outer
    transaction that is always rolled back at the end of the test.

    Application code (see e.g. `app/api/tasks.py`) calls `db.commit()`
    directly. `join_transaction_mode="create_savepoint"` makes the Session
    run its work inside a SAVEPOINT nested within our outer transaction, so
    the app's own `db.commit()` calls behave normally (from its point of
    view it's a real commit) while the whole test's effects are rolled
    back afterwards via `outer_transaction.rollback()`.
    """
    connection = engine.connect()
    outer_transaction = connection.begin()

    session_factory = sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """A FastAPI TestClient whose `get_db` dependency yields the same
    per-test session as `db_session`, so a test can create data through
    the API and assert on it directly (or vice versa) within one
    transaction.
    """

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

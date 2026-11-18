"""Shared fixtures.

Tests run against SQLite by default. Set ``TEST_DATABASE_URL`` to run the
same suite against PostgreSQL (CI does this)::

    TEST_DATABASE_URL=postgresql://paddle:paddle@localhost:5432/paddles_test pytest
"""

import os

import pytest

from paddle_finder.api import create_app
from paddle_finder.core.catalog import PaddleCatalog
from paddle_finder.core.config import DEFAULT_DATA_FILE
from paddle_finder.data import etl, schema


@pytest.fixture(scope="session")
def frame():
    return etl.load_clean_frame(DEFAULT_DATA_FILE)


@pytest.fixture(scope="session")
def catalog(frame):
    return PaddleCatalog(etl.paddles_from_frame(frame))


@pytest.fixture(scope="session")
def database_url(tmp_path_factory):
    return os.environ.get("TEST_DATABASE_URL") or (
        "sqlite:///" + str(tmp_path_factory.mktemp("db") / "test.db"))


@pytest.fixture(scope="session")
def engine(database_url, frame):
    engine = schema.make_engine(database_url)
    schema.seed(engine, frame)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def app(database_url, engine):
    return create_app({"DATABASE_URL": database_url, "AUTO_SEED": False})


@pytest.fixture()
def client(app):
    return app.test_client()

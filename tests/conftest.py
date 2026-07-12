import pytest

from campus_shop import create_app
from campus_shop.db import get_db, init_db


@pytest.fixture
def app(tmp_path):
    database_path = tmp_path / "test.sqlite"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(database_path),
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        init_db()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        connection = get_db()
        yield connection


@pytest.fixture
def database_path(app):
    return app.config["DATABASE"]

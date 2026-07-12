import sqlite3
from pathlib import Path

import pytest

from campus_shop.db import get_db


EXPECTED_COLUMNS = {
    "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
    "name": {"type": "TEXT", "notnull": 1, "pk": 0},
    "description": {"type": "TEXT", "notnull": 1, "pk": 0},
    "category": {"type": "TEXT", "notnull": 1, "pk": 0},
    "price_cents": {"type": "INTEGER", "notnull": 1, "pk": 0},
    "image": {"type": "TEXT", "notnull": 0, "pk": 0},
}


def test_product_schema_has_required_columns_and_constraints(db):
    columns = {
        row["name"]: {
            "type": row["type"],
            "notnull": row["notnull"],
            "pk": row["pk"],
        }
        for row in db.execute("PRAGMA table_info(product)").fetchall()
    }

    assert columns == EXPECTED_COLUMNS

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO product
                (id, name, description, category, price_cents)
            VALUES (?, ?, ?, ?, ?)
            """,
            (99, "Invalid", "Invalid price test", "Test", 0),
        )


def test_seed_data_is_complete(db):
    products = db.execute(
        "SELECT id, name, description, category, price_cents FROM product ORDER BY id"
    ).fetchall()

    assert len(products) >= 6
    assert len({product["id"] for product in products}) == len(products)
    assert len({product["category"] for product in products}) >= 2
    assert all(product["name"] for product in products)
    assert all(product["description"] for product in products)
    assert all(product["category"] for product in products)
    assert all(product["price_cents"] > 0 for product in products)


def test_init_db_command_is_idempotent(app):
    with app.app_context():
        before = get_db().execute(
            "SELECT id, name, price_cents FROM product ORDER BY id"
        ).fetchall()
        before_values = [tuple(row) for row in before]

    runner = app.test_cli_runner()
    first_result = runner.invoke(args=["init-db"])
    second_result = runner.invoke(args=["init-db"])

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    assert "Initialized the database." in second_result.output

    with app.app_context():
        after = get_db().execute(
            "SELECT id, name, price_cents FROM product ORDER BY id"
        ).fetchall()

    assert [tuple(row) for row in after] == before_values


def test_application_factory_uses_isolated_test_configuration(
    app, database_path, tmp_path
):
    assert app.config["TESTING"] is True
    assert app.config["SECRET_KEY"] == "test-secret"
    assert Path(database_path).parent == tmp_path
    assert Path(app.instance_path).is_dir()

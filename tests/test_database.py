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


def test_order_schema_and_foreign_key_contract(db):
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert [row["name"] for row in db.execute("PRAGMA table_info(orders)")] == [
        "id", "customer_name", "delivery_address", "total_cents", "created_at"
    ]
    assert [row["name"] for row in db.execute("PRAGMA table_info(order_item)")] == [
        "id", "order_id", "product_id", "product_name", "unit_price_cents",
        "quantity", "line_total_cents"
    ]
    foreign_keys = db.execute("PRAGMA foreign_key_list(order_item)").fetchall()
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["from"] == "order_id"
    assert foreign_keys[0]["table"] == "orders"
    assert foreign_keys[0]["on_delete"] == "CASCADE"

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO orders (customer_name, delivery_address, total_cents) VALUES (?, ?, ?)",
            ("", "Address", 100),
        )
    db.rollback()


def test_init_db_preserves_existing_order_items_and_seed_products(app):
    with app.app_context():
        db = get_db()
        product_count = db.execute("SELECT count(*) FROM product").fetchone()[0]
        order_id = db.execute(
            "INSERT INTO orders (customer_name, delivery_address, total_cents) VALUES (?, ?, ?)",
            ("Test Student", "Local test address", 499),
        ).lastrowid
        db.execute(
            """INSERT INTO order_item
               (order_id, product_id, product_name, unit_price_cents, quantity, line_total_cents)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (order_id, 1, "Campus Notebook", 499, 1, 499),
        )
        db.commit()

    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0

    with app.app_context():
        db = get_db()
        assert db.execute("SELECT count(*) FROM product").fetchone()[0] == product_count
        assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM order_item").fetchone()[0] == 1

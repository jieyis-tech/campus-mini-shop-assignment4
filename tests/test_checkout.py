import sqlite3

import pytest

import campus_shop.shop as shop


def set_cart(client, cart):
    with client.session_transaction() as flask_session:
        flask_session["cart"] = cart


def saved_cart(client):
    with client.session_transaction() as flask_session:
        return flask_session.get("cart", None)


def counts(db):
    return (
        db.execute("SELECT count(*) FROM orders").fetchone()[0],
        db.execute("SELECT count(*) FROM order_item").fetchone()[0],
    )


def test_checkout_summary_matches_authoritative_cart(client, db):
    set_cart(client, {"1": 2, "4": 1})
    cart_page = client.get("/cart").get_data(as_text=True)
    checkout_page = client.get("/checkout").get_data(as_text=True)
    for value in ("Campus Notebook", "Reusable Water Bottle", "$4.99", "$12.99", "$9.98", "$22.97"):
        assert value in cart_page
        assert value in checkout_page
    assert "Continue to simulated checkout" in cart_page
    assert '<label for="customer_name">' in checkout_page
    assert '<label for="delivery_address">' in checkout_page


def test_empty_effective_cart_get_redirects_with_feedback(client):
    set_cart(client, {"1": False, "01": 2, "999": 4})
    response = client.get("/checkout")
    assert response.status_code == 302
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Add at least one product before checkout." in page
    assert saved_cart(client) == {"1": False, "01": 2, "999": 4}


def test_empty_effective_cart_post_is_400_without_rows(client, db):
    response = client.post("/checkout", data={"customer_name": "Test", "delivery_address": "Test"})
    assert response.status_code == 400
    assert "Your cart is empty; an order was not created." in response.get_data(as_text=True)
    assert counts(db) == (0, 0)


@pytest.mark.parametrize(
    "data,messages,values",
    [
        ({}, ["Enter your name.", "Enter a delivery address."], []),
        ({"customer_name": "   ", "delivery_address": " \n "}, ["Enter your name.", "Enter a delivery address."], []),
        ({"customer_name": " N " * 51, "delivery_address": " A " * 151}, ["Name must be 100 characters or fewer.", "Delivery address must be 300 characters or fewer."], []),
        ({"customer_name": "  Student  ", "delivery_address": "  Hall 1\nRoom 2  "}, [], ["Student", "Hall 1\nRoom 2"]),
    ],
)
def test_invalid_checkout_reports_all_field_errors_and_preserves_state(client, db, data, messages, values):
    original = {"1": 2, "bad": 4}
    set_cart(client, original)
    response = client.post("/checkout", data=data)
    if not messages:
        # The final case is valid and verifies normalized persistence elsewhere.
        assert response.status_code == 302
        return
    page = response.get_data(as_text=True)
    assert response.status_code == 400
    for message in messages:
        assert message in page
    for value in values:
        assert value in page
    assert saved_cart(client) == original
    assert counts(db) == (0, 0)


def test_valid_checkout_persists_authoritative_items_and_clears_complete_key(client, db):
    set_cart(client, {"1": 2, "4": 3, "bad": 8})
    response = client.post(
        "/checkout",
        data={
            "customer_name": "  Test Student  ",
            "delivery_address": "  Hall 1\nRoom 2  ",
            "price": "0", "quantity": "999", "total": "1", "product_name": "Fake",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/orders/1")
    assert saved_cart(client) is None

    order = db.execute("SELECT * FROM orders").fetchone()
    items = db.execute("SELECT * FROM order_item ORDER BY id").fetchall()
    assert tuple(order[key] for key in ("customer_name", "delivery_address", "total_cents")) == (
        "Test Student", "Hall 1\nRoom 2", 4895
    )
    assert order["created_at"]
    assert [(row["product_id"], row["product_name"], row["unit_price_cents"], row["quantity"], row["line_total_cents"]) for row in items] == [
        (1, "Campus Notebook", 499, 2, 998),
        (4, "Reusable Water Bottle", 1299, 3, 3897),
    ]


def test_item_insert_failure_rolls_back_and_preserves_complete_cart(client, db, monkeypatch):
    original = {"1": 1, "4": 1, "bad": 7}
    set_cart(client, original)
    real_insert = shop._insert_order_item
    calls = 0

    def fail_on_second_item(connection, order_id, line):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise sqlite3.DatabaseError("secret raw database failure")
        return real_insert(connection, order_id, line)

    monkeypatch.setattr(shop, "_insert_order_item", fail_on_second_item)
    response = client.post("/checkout", data={"customer_name": "Student", "delivery_address": "Hall"})
    page = response.get_data(as_text=True)
    assert response.status_code == 500
    assert "order could not be saved" in page
    assert "secret raw database failure" not in page
    assert counts(db) == (0, 0)
    assert saved_cart(client) == original

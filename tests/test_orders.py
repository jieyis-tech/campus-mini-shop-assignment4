def create_order(client):
    with client.session_transaction() as flask_session:
        flask_session["cart"] = {"1": 2}
    return client.post(
        "/checkout",
        data={"customer_name": "Test <Student>", "delivery_address": "Hall A\nRoom <2>"},
    )


def test_confirmation_displays_saved_order_with_two_decimal_money(client):
    response = create_order(client)
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Order confirmed" in page
    assert "Order number</dt><dd>1</dd>" in page
    assert "Test &lt;Student&gt;" in page
    assert "Hall A\nRoom &lt;2&gt;" in page
    assert "Campus Notebook" in page
    assert "Unit price: $4.99" in page
    assert "Quantity: 2" in page
    assert "Line total: $9.98" in page
    assert "Order total: <strong>$9.98</strong>" in page
    assert "Return to products" in page


def test_confirmation_uses_snapshots_after_product_change_or_deletion(client, db):
    response = create_order(client)
    db.execute("UPDATE product SET name = 'Changed', price_cents = 9999 WHERE id = 1")
    db.execute("DELETE FROM product WHERE id = 1")
    db.commit()
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Campus Notebook" in page
    assert "$4.99" in page
    assert "Changed" not in page


def test_confirmation_refresh_is_idempotent_and_does_not_change_session(client, db):
    response = create_order(client)
    path = response.headers["Location"]
    assert client.get(path).status_code == 200
    assert client.get(path).status_code == 200
    assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM order_item").fetchone()[0] == 1
    with client.session_transaction() as flask_session:
        assert "cart" not in flask_session


def test_unknown_order_returns_understandable_404_without_cart_mutation(client):
    with client.session_transaction() as flask_session:
        flask_session["cart"] = {"1": 1}
    response = client.get("/orders/99999")
    assert response.status_code == 404
    assert "requested order was not found" in response.get_data(as_text=True)
    with client.session_transaction() as flask_session:
        assert flask_session["cart"] == {"1": 1}

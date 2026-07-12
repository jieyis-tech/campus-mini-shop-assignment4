import pytest


def session_cart(client):
    with client.session_transaction() as session:
        return dict(session.get("cart", {}))


def test_empty_cart_message_and_zero_subtotal(client):
    response = client.get("/cart")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Your cart is empty." in page
    assert "Subtotal: <strong>$0.00</strong>" in page
    assert ">Products</a>" in page
    assert ">Cart</a>" in page


@pytest.mark.parametrize("form_data", [{}, {"quantity": ""}, {"quantity": "   "}])
def test_add_defaults_to_one_and_shows_correct_total(client, form_data):
    response = client.post("/cart/add/1", data=form_data, follow_redirects=True)
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert session_cart(client) == {"1": 1}
    assert 'data-product-id="1"' in page
    assert "Quantity: <span class=\"quantity\">1</span>" in page
    assert "Line total: <span class=\"line-total\">$4.99</span>" in page
    assert "Subtotal: <strong>$4.99</strong>" in page


def test_explicit_add_redirects_to_cart_and_flashes(client):
    response = client.post("/cart/add/2", data={"quantity": "3"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/cart")
    assert session_cart(client) == {"2": 3}

    cart_response = client.get(response.headers["Location"])
    page = cart_response.get_data(as_text=True)
    assert "Added Black Ink Pen Set to your cart." in page
    assert "Quantity: <span class=\"quantity\">3</span>" in page
    assert "Line total: <span class=\"line-total\">$10.47</span>" in page


def test_repeated_add_accumulates_single_line(client):
    client.post("/cart/add/1", data={"quantity": "2"})
    response = client.post(
        "/cart/add/1", data={"quantity": "3"}, follow_redirects=True
    )
    page = response.get_data(as_text=True)

    assert session_cart(client) == {"1": 5}
    assert page.count('class="cart-line" data-product-id="1"') == 1
    assert "Quantity: <span class=\"quantity\">5</span>" in page
    assert "Subtotal: <strong>$24.95</strong>" in page


def test_add_second_product_preserves_first_and_calculates_subtotal(client):
    client.post("/cart/add/1", data={"quantity": "2"})
    response = client.post(
        "/cart/add/4", data={"quantity": "3"}, follow_redirects=True
    )
    page = response.get_data(as_text=True)

    assert session_cart(client) == {"1": 2, "4": 3}
    assert page.count('class="cart-line" data-product-id=') == 2
    assert "Line total: <span class=\"line-total\">$9.98</span>" in page
    assert "Line total: <span class=\"line-total\">$38.97</span>" in page
    assert "Subtotal: <strong>$48.95</strong>" in page


def test_cart_uses_current_database_price(client, db):
    client.post("/cart/add/1", data={"quantity": "2"})
    db.execute("UPDATE product SET price_cents = ? WHERE id = ?", (625, 1))
    db.commit()

    response = client.get("/cart")
    page = response.get_data(as_text=True)

    assert "Unit price: $6.25" in page
    assert "Line total: <span class=\"line-total\">$12.50</span>" in page
    assert "Subtotal: <strong>$12.50</strong>" in page


@pytest.mark.parametrize(
    "quantity",
    ["words", "1.5", "+2", "-2", "0", "-0", "1e2"],
)
def test_invalid_add_keeps_cart(client, quantity):
    client.post("/cart/add/1", data={"quantity": "2"})
    before = session_cart(client)

    response = client.post("/cart/add/2", data={"quantity": quantity})
    page = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "positive whole-number quantity" in page
    assert session_cart(client) == before


def test_unknown_add_returns_404_before_quantity_validation_and_keeps_cart(client):
    client.post("/cart/add/1", data={"quantity": "2"})
    before = session_cart(client)

    response = client.post("/cart/add/99999", data={"quantity": "invalid"})
    page = response.get_data(as_text=True)

    assert response.status_code == 404
    assert "requested product was not found" in page
    assert session_cart(client) == before


def test_add_is_post_only(client):
    response = client.get("/cart/add/1")

    assert response.status_code == 405
    assert session_cart(client) == {}


def test_cart_persists_across_navigation_and_refresh(client):
    client.post("/cart/add/6", data={"quantity": "2"})

    assert client.get("/").status_code == 200
    assert client.get("/products/6").status_code == 200
    first_cart = client.get("/cart").get_data(as_text=True)
    second_cart = client.get("/cart").get_data(as_text=True)

    assert "USB-C Charging Cable" in first_cart
    assert "Quantity: <span class=\"quantity\">2</span>" in first_cart
    assert first_cart == second_cart


def test_product_detail_has_labeled_add_form(client):
    response = client.get("/products/1")
    page = response.get_data(as_text=True)

    assert '<form method="post" action="/cart/add/1">' in page
    assert '<label for="quantity">Quantity</label>' in page
    assert 'id="quantity" name="quantity"' in page
    assert "Add to cart" in page


def test_update_quantity_recalculates_line_and_subtotal(client):
    client.post("/cart/add/1", data={"quantity": "2"})
    client.post("/cart/add/4", data={"quantity": "1"})

    response = client.post("/cart/update/1", data={"quantity": "4"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/cart")
    assert session_cart(client) == {"1": 4, "4": 1}

    cart_response = client.get(response.headers["Location"])
    page = cart_response.get_data(as_text=True)
    assert "Updated the cart quantity." in page
    assert "Quantity: <span class=\"quantity\">4</span>" in page
    assert "Line total: <span class=\"line-total\">$19.96</span>" in page
    assert "Subtotal: <strong>$32.95</strong>" in page


@pytest.mark.parametrize(
    "form_data",
    [
        {},
        {"quantity": ""},
        {"quantity": "   "},
        {"quantity": "words"},
        {"quantity": "1.5"},
        {"quantity": "+2"},
        {"quantity": "-2"},
        {"quantity": "0"},
        {"quantity": "-0"},
        {"quantity": "1e2"},
    ],
)
def test_invalid_update_keeps_quantity(client, form_data):
    client.post("/cart/add/1", data={"quantity": "3"})
    before = session_cart(client)

    response = client.post("/cart/update/1", data=form_data)
    page = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "positive whole-number quantity" in page
    assert session_cart(client) == before


def test_update_missing_cart_line_returns_404_and_keeps_cart(client):
    client.post("/cart/add/1", data={"quantity": "2"})
    before = session_cart(client)

    response = client.post("/cart/update/2", data={"quantity": "invalid"})
    page = response.get_data(as_text=True)

    assert response.status_code == 404
    assert "not currently in your cart" in page
    assert session_cart(client) == before


def test_remove_one_item_preserves_other_and_recalculates(client):
    client.post("/cart/add/1", data={"quantity": "2"})
    client.post("/cart/add/4", data={"quantity": "3"})

    response = client.post("/cart/remove/1")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/cart")
    assert session_cart(client) == {"4": 3}

    cart_response = client.get(response.headers["Location"])
    page = cart_response.get_data(as_text=True)
    assert "Removed the product from your cart." in page
    assert 'data-product-id="1"' not in page
    assert 'data-product-id="4"' in page
    assert "Subtotal: <strong>$38.97</strong>" in page


def test_remove_absent_item_redirects_without_changing_cart(client):
    client.post("/cart/add/1", data={"quantity": "2"})
    before = session_cart(client)

    response = client.post("/cart/remove/2")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/cart")
    assert session_cart(client) == before
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Removed the product from your cart." not in page


@pytest.mark.parametrize("path", ["/cart/update/1", "/cart/remove/1"])
def test_update_and_remove_are_post_only(client, path):
    client.post("/cart/add/1", data={"quantity": "2"})
    before = session_cart(client)

    response = client.get(path)

    assert response.status_code == 405
    assert session_cart(client) == before


def test_cart_lines_have_labeled_update_and_remove_forms(client):
    client.post("/cart/add/1", data={"quantity": "2"})

    response = client.get("/cart")
    page = response.get_data(as_text=True)

    assert '<form method="post" action="/cart/update/1">' in page
    assert '<label for="quantity-1">New quantity</label>' in page
    assert 'id="quantity-1"' in page
    assert 'name="quantity"' in page
    assert '<form method="post" action="/cart/remove/1">' in page
    assert "Remove</button>" in page


def test_cart_ignores_ineffective_entries_without_repair(client, db):
    db.execute("DELETE FROM product WHERE id = 6")
    db.commit()
    original = {
        "1": 2,
        "01": 7,
        "2": True,
        "3": 0,
        "4": -1,
        "5": "3",
        "6": 4,
        "not-an-id": 9,
    }
    with client.session_transaction() as flask_session:
        flask_session["cart"] = original

    response = client.get("/cart")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'data-product-id="1"' in page
    assert page.count('class="cart-line" data-product-id=') == 1
    assert "Subtotal: <strong>$9.98</strong>" in page
    with client.session_transaction() as flask_session:
        assert flask_session["cart"] == original


def test_non_mapping_cart_is_read_as_empty_without_repair(client):
    with client.session_transaction() as flask_session:
        flask_session["cart"] = ["1", 2]

    response = client.get("/cart")
    assert response.status_code == 200
    assert "Your cart is empty." in response.get_data(as_text=True)
    with client.session_transaction() as flask_session:
        assert flask_session["cart"] == ["1", 2]

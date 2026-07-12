def test_product_list_shows_all_seeded_products(client, db):
    products = db.execute(
        "SELECT id, name, category, price_cents FROM product ORDER BY id"
    ).fetchall()

    response = client.get("/")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert len(products) >= 6
    for product in products:
        assert product["name"] in page
        assert product["category"] in page
        assert f"${product['price_cents'] // 100}.{product['price_cents'] % 100:02d}" in page
        assert f'/products/{product["id"]}' in page


def test_product_detail_shows_correct_fields_and_price(client, db):
    product = db.execute(
        """
        SELECT id, name, description, category, price_cents
        FROM product
        WHERE id = 4
        """
    ).fetchone()

    response = client.get(f"/products/{product['id']}")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert product["name"] in page
    assert product["description"] in page
    assert product["category"] in page
    assert f"${product['price_cents'] // 100}.{product['price_cents'] % 100:02d}" in page
    assert "No image available" in page


def test_unknown_product_detail_returns_understandable_404(client):
    response = client.get("/products/99999")
    page = response.get_data(as_text=True)

    assert response.status_code == 404
    assert "Error 404" in page
    assert "requested product was not found" in page


def test_main_navigation_is_present_on_catalog_detail_and_error_pages(client):
    for path, expected_status in (("/", 200), ("/products/1", 200), ("/products/99999", 404)):
        response = client.get(path)
        page = response.get_data(as_text=True)

        assert response.status_code == expected_status
        assert 'href="/"' in page
        assert ">Products</a>" in page
        assert 'href="/cart"' in page
        assert ">Cart</a>" in page


def test_catalog_output_escapes_database_content(client, db):
    db.execute(
        """
        INSERT INTO product (id, name, description, category, price_cents)
        VALUES (?, ?, ?, ?, ?)
        """,
        (50, "<script>alert(1)</script>", "Description", "Test", 125),
    )
    db.commit()

    response = client.get("/")
    page = response.get_data(as_text=True)

    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page

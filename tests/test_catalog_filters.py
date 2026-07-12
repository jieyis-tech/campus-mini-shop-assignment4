import pytest


def product_ids(page):
    return [int(part.split('"', 1)[0]) for part in page.split('data-product-id="')[1:]]


def test_name_search_is_case_insensitive_and_name_only(client):
    page = client.get("/?q=NoTeBoOk").get_data(as_text=True)
    assert product_ids(page) == [1]
    assert "Campus Notebook" in page

    page = client.get("/?q=lectures").get_data(as_text=True)
    assert product_ids(page) == []
    page = client.get("/?q=Study+Supplies").get_data(as_text=True)
    assert product_ids(page) == []


@pytest.mark.parametrize("query", ["%", "_", "\\"])
def test_search_treats_like_metacharacters_literally(client, db, query):
    db.execute(
        "INSERT INTO product (id, name, description, category, price_cents) VALUES (?, ?, ?, ?, ?)",
        (50, "Literal % _ \\ Product", "Test", "Symbols", 100),
    )
    db.commit()
    response = client.get("/", query_string={"q": query})
    assert product_ids(response.get_data(as_text=True)) == [50]


def test_blank_search_shows_complete_catalog(client):
    assert product_ids(client.get("/?q=+++ ").get_data(as_text=True)) == [1, 2, 3, 4, 5, 6]


def test_catalog_controls_are_labeled_get_form(client):
    page = client.get("/").get_data(as_text=True)
    assert '<form class="catalog-controls" method="get" action="/">' in page
    assert '<label for="q">Search product names</label>' in page
    assert '<label for="category">Category</label>' in page


def test_category_filter_is_exact_and_case_sensitive(client):
    assert product_ids(client.get("/?category=Campus+Essentials").get_data(as_text=True)) == [4, 5]
    page = client.get("/?category=campus+essentials").get_data(as_text=True)
    assert product_ids(page) == []
    assert 'value="campus essentials" selected' in page


def test_category_choices_are_binary_sorted(client, db):
    db.execute(
        "INSERT INTO product (id, name, description, category, price_cents) VALUES (50, 'Test', 'Test', 'AAA', 100)"
    )
    db.commit()
    page = client.get("/").get_data(as_text=True)
    positions = [page.index(f'value="{value}"') for value in (
        "AAA", "Campus Essentials", "Study Supplies", "Tech Accessories"
    )]
    assert positions == sorted(positions)


def test_combined_search_and_category_preserves_normalized_controls(client):
    page = client.get("/", query_string={"q": "  pen  ", "category": " Study Supplies "}).get_data(as_text=True)
    assert product_ids(page) == [2]
    assert 'name="q" type="search" value="pen"' in page
    assert 'value="Study Supplies" selected' in page


def test_no_results_has_exact_message_and_unfiltered_link(client):
    page = client.get("/?q=missing&category=Unknown").get_data(as_text=True)
    assert "No products match your search and filter." in page
    assert '<a href="/">View all products</a>' in page
    assert 'value="Unknown" selected' in page


def test_search_keeps_stable_order_and_detail_links(client):
    page = client.get("/?q=a").get_data(as_text=True)
    ids = product_ids(page)
    assert ids == sorted(ids)
    for product_id in ids:
        assert f'href="/products/{product_id}"' in page

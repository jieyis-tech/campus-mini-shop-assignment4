import re

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .db import get_db


bp = Blueprint("shop", __name__)

POSITIVE_WHOLE_NUMBER = re.compile(r"[0-9]+")


def format_currency(cents):
    """Format an integer number of cents without floating-point arithmetic."""
    cents = int(cents)
    dollars, remainder = divmod(cents, 100)
    return f"${dollars}.{remainder:02d}"


def get_product(product_id):
    """Load one product or return an understandable not-found response."""
    product = get_db().execute(
        """
        SELECT id, name, description, category, price_cents, image
        FROM product
        WHERE id = ?
        """,
        (product_id,),
    ).fetchone()

    if product is None:
        abort(404, description="The requested product was not found.")

    return product


def parse_quantity(value, *, default_if_blank=False):
    """Parse an ASCII whole-number quantity without changing cart state."""
    if value is None or value.strip() == "":
        if default_if_blank:
            return 1
        abort(400, description="Enter a positive whole-number quantity.")

    value = value.strip()
    if POSITIVE_WHOLE_NUMBER.fullmatch(value) is None:
        abort(400, description="Enter a positive whole-number quantity.")

    quantity = int(value)
    if quantity <= 0:
        abort(400, description="Enter a positive whole-number quantity.")

    return quantity


def get_session_cart():
    """Return a copy so validation failures cannot partially mutate the session."""
    return dict(session.get("cart", {}))


def build_cart():
    """Load current product data and calculate authoritative integer-cent totals."""
    cart = get_session_cart()
    if not cart:
        return [], 0

    product_ids = [int(product_id) for product_id in cart]
    placeholders = ", ".join("?" for _ in product_ids)
    products = get_db().execute(
        f"""
        SELECT id, name, description, category, price_cents, image
        FROM product
        WHERE id IN ({placeholders})
        ORDER BY id
        """,
        product_ids,
    ).fetchall()

    lines = []
    subtotal_cents = 0
    for product in products:
        quantity = cart[str(product["id"])]
        line_total_cents = product["price_cents"] * quantity
        lines.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total_cents": line_total_cents,
            }
        )
        subtotal_cents += line_total_cents

    return lines, subtotal_cents


@bp.get("/")
def product_list():
    products = get_db().execute(
        """
        SELECT id, name, description, category, price_cents, image
        FROM product
        ORDER BY id
        """
    ).fetchall()
    return render_template("products.html", products=products)


@bp.get("/products/<int:product_id>")
def product_detail(product_id):
    return render_template("product_detail.html", product=get_product(product_id))


@bp.get("/cart")
def cart():
    lines, subtotal_cents = build_cart()
    return render_template(
        "cart.html", lines=lines, subtotal_cents=subtotal_cents
    )


@bp.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    product = get_product(product_id)
    quantity = parse_quantity(
        request.form.get("quantity"), default_if_blank=True
    )

    cart = get_session_cart()
    product_key = str(product_id)
    cart[product_key] = cart.get(product_key, 0) + quantity
    session["cart"] = cart

    flash(f"Added {product['name']} to your cart.")
    return redirect(url_for("shop.cart"))


@bp.post("/cart/update/<int:product_id>")
def update_cart(product_id):
    cart = get_session_cart()
    product_key = str(product_id)
    if product_key not in cart:
        abort(404, description="That product is not currently in your cart.")

    quantity = parse_quantity(request.form.get("quantity"))
    cart[product_key] = quantity
    session["cart"] = cart

    flash("Updated the cart quantity.")
    return redirect(url_for("shop.cart"))


@bp.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id):
    cart = get_session_cart()
    product_key = str(product_id)

    if product_key in cart:
        del cart[product_key]
        session["cart"] = cart
        flash("Removed the product from your cart.")

    return redirect(url_for("shop.cart"))

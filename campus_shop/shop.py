import re
import sqlite3
from collections.abc import Mapping

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
    cart = session.get("cart", {})
    return dict(cart) if isinstance(cart, Mapping) else {}


def build_cart():
    """Load current product data and calculate authoritative integer-cent totals."""
    cart = get_session_cart()
    if not cart:
        return [], 0

    effective_quantities = {}
    for product_id, quantity in cart.items():
        if not isinstance(product_id, str) or not product_id.isascii():
            continue
        if not product_id.isdigit() or product_id == "0":
            continue
        numeric_id = int(product_id)
        if str(numeric_id) != product_id:
            continue
        if type(quantity) is not int or quantity <= 0:
            continue
        effective_quantities[numeric_id] = quantity

    if not effective_quantities:
        return [], 0

    product_ids = list(effective_quantities)
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
        quantity = effective_quantities[product["id"]]
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
    q = str(request.args.get("q", "")).strip()
    category = str(request.args.get("category", "")).strip()
    predicates = []
    parameters = []

    if q:
        escaped_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        predicates.append("name LIKE ? ESCAPE '\\' COLLATE NOCASE")
        parameters.append(f"%{escaped_q}%")
    if category:
        predicates.append("category = ? COLLATE BINARY")
        parameters.append(category)

    query = """
        SELECT id, name, description, category, price_cents, image
        FROM product
    """
    if predicates:
        query += " WHERE " + " AND ".join(predicates)
    query += " ORDER BY id"

    db = get_db()
    products = db.execute(query, parameters).fetchall()
    categories = db.execute(
        "SELECT DISTINCT category FROM product ORDER BY category COLLATE BINARY"
    ).fetchall()
    category_names = [row["category"] for row in categories]
    return render_template(
        "products.html",
        products=products,
        categories=category_names,
        q=q,
        category=category,
        unknown_category=bool(category and category not in category_names),
        filters_active=bool(q or category),
    )


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


def _insert_order_item(db, order_id, line):
    """Insert one immutable order-item snapshot (also a focused test seam)."""
    product = line["product"]
    db.execute(
        """
        INSERT INTO order_item
            (order_id, product_id, product_name, unit_price_cents,
             quantity, line_total_cents)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            product["id"],
            product["name"],
            product["price_cents"],
            line["quantity"],
            line["line_total_cents"],
        ),
    )


def persist_order(lines, customer_name, delivery_address):
    """Save an order and every item atomically, returning the new order ID."""
    db = get_db()
    total_cents = sum(line["line_total_cents"] for line in lines)
    try:
        db.execute("BEGIN")
        cursor = db.execute(
            """
            INSERT INTO orders (customer_name, delivery_address, total_cents)
            VALUES (?, ?, ?)
            """,
            (customer_name, delivery_address, total_cents),
        )
        order_id = cursor.lastrowid
        for line in lines:
            _insert_order_item(db, order_id, line)
        db.commit()
        return order_id
    except sqlite3.Error:
        db.rollback()
        raise


def _checkout_context(lines, subtotal_cents, customer_name="", delivery_address="", errors=None):
    return {
        "lines": lines,
        "subtotal_cents": subtotal_cents,
        "customer_name": customer_name,
        "delivery_address": delivery_address,
        "errors": errors or {},
    }


@bp.route("/checkout", methods=("GET", "POST"))
def checkout():
    lines, subtotal_cents = build_cart()

    if request.method == "GET":
        if not lines:
            flash("Add at least one product before checkout.")
            return redirect(url_for("shop.cart"))
        return render_template(
            "checkout.html", **_checkout_context(lines, subtotal_cents)
        )

    if not lines:
        abort(400, description="Your cart is empty; an order was not created.")

    customer_name = str(request.form.get("customer_name", "")).strip()
    delivery_address = str(request.form.get("delivery_address", "")).strip()
    errors = {}
    if not customer_name:
        errors["customer_name"] = "Enter your name."
    elif len(customer_name) > 100:
        errors["customer_name"] = "Name must be 100 characters or fewer."
    if not delivery_address:
        errors["delivery_address"] = "Enter a delivery address."
    elif len(delivery_address) > 300:
        errors["delivery_address"] = "Delivery address must be 300 characters or fewer."

    if errors:
        return (
            render_template(
                "checkout.html",
                **_checkout_context(
                    lines, subtotal_cents, customer_name, delivery_address, errors
                ),
            ),
            400,
        )

    try:
        order_id = persist_order(lines, customer_name, delivery_address)
    except sqlite3.Error:
        return (
            render_template(
                "error.html",
                status_code=500,
                message="The order could not be saved. Your cart has not been changed.",
            ),
            500,
        )

    session.pop("cart", None)
    return redirect(url_for("shop.order_confirmation", order_id=order_id))


@bp.get("/orders/<int:order_id>")
def order_confirmation(order_id):
    db = get_db()
    order = db.execute(
        """
        SELECT id, customer_name, delivery_address, total_cents, created_at
        FROM orders
        WHERE id = ?
        """,
        (order_id,),
    ).fetchone()
    if order is None:
        abort(404, description="The requested order was not found.")

    items = db.execute(
        """
        SELECT id, product_id, product_name, unit_price_cents,
               quantity, line_total_cents
        FROM order_item
        WHERE order_id = ?
        ORDER BY id
        """,
        (order_id,),
    ).fetchall()
    return render_template("order_confirmation.html", order=order, items=items)

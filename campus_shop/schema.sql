CREATE TABLE IF NOT EXISTS product (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    image TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL
        CHECK (length(trim(customer_name)) BETWEEN 1 AND 100),
    delivery_address TEXT NOT NULL
        CHECK (length(trim(delivery_address)) BETWEEN 1 AND 300),
    total_cents INTEGER NOT NULL CHECK (total_cents > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_item (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL CHECK (length(trim(product_name)) > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents > 0),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    line_total_cents INTEGER NOT NULL CHECK (line_total_cents > 0)
);

INSERT OR IGNORE INTO product
    (id, name, description, category, price_cents, image)
VALUES
    (1, 'Campus Notebook', 'A ruled notebook for lectures and study sessions.', 'Study Supplies', 499, NULL),
    (2, 'Black Ink Pen Set', 'A set of three smooth-writing black ink pens.', 'Study Supplies', 349, NULL),
    (3, 'Pastel Highlighters', 'Four pastel highlighters for notes and textbooks.', 'Study Supplies', 599, NULL),
    (4, 'Reusable Water Bottle', 'A lightweight bottle for days around campus.', 'Campus Essentials', 1299, NULL),
    (5, 'Canvas Book Tote', 'A sturdy canvas tote for books and daily supplies.', 'Campus Essentials', 1499, NULL),
    (6, 'USB-C Charging Cable', 'A one-metre cable for compatible phones and laptops.', 'Tech Accessories', 899, NULL);

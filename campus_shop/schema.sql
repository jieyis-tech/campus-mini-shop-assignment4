CREATE TABLE IF NOT EXISTS product (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    image TEXT
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

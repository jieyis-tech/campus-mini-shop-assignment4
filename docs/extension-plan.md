# Campus Mini Shop: Extension Implementation Plan

## Planning basis and scope guard

This plan implements the approved `docs/extension-specification.md` on top of
the completed base system. The base application's Flask factory, request-scoped
SQLite connection, `product` table, signed session cart, integer-cent currency
helper, server-rendered templates, and isolated pytest fixtures remain the
foundation. Existing catalog, product-detail, add, update, and remove behavior
must remain compatible.

The extension is limited to product-name search, one exact category filter, a
simulated checkout, saved order/item snapshots, and a confirmation page. It
must not add accounts, payment or card fields, inventory, administration,
shipping or tax calculations, discounts, external services, JavaScript
frameworks, an ORM, or a migration framework.

## Agreed implementation design

### Smallest compatible schema update

- Append two idempotent `CREATE TABLE IF NOT EXISTS` statements to
  `campus_shop/schema.sql`; do not alter or recreate `product` and do not change
  its six stable seed rows.
- `orders` contains `id INTEGER PRIMARY KEY`, required `customer_name`, required
  `delivery_address`, `total_cents INTEGER NOT NULL CHECK (total_cents > 0)`,
  and `created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`. Add length checks of
  1–100 and 1–300 characters to the two trimmed text columns.
- `order_item` contains `id INTEGER PRIMARY KEY`, `order_id INTEGER NOT NULL`
  referencing `orders(id) ON DELETE CASCADE`, provenance-only
  `product_id INTEGER NOT NULL`, required non-empty `product_name`, positive
  `unit_price_cents`, positive `quantity`, and positive `line_total_cents`.
  `product_id` intentionally does not reference `product`, so a snapshot
  survives later catalog deletion.
- Enable `PRAGMA foreign_keys = ON` whenever `get_db()` creates an application
  connection. The existing test fixture automatically receives the same
  behavior. Repeated `init-db` execution creates only missing tables and seed
  products and preserves all products, orders, and items.

### Deterministic catalog queries

- Normalize `q` and `category` once with text conversion and `.strip()`; a
  missing or normalized-empty parameter means no condition.
- Escape backslash first and then `%` and `_` before placing the name query
  inside `%...%`. Use a parameterized predicate equivalent to
  `name LIKE ? ESCAPE '\\' COLLATE NOCASE`; never interpolate user text into
  SQL. This gives literal `%`/`_` behavior and ASCII case-insensitive matching
  for the English seed catalog.
- Use a separately parameterized `category = ? COLLATE BINARY` predicate for
  exact, case-sensitive matching. Join active predicates with `AND`, and always
  finish with `ORDER BY id` to retain base ordering.
- Load category choices with `SELECT DISTINCT category ... ORDER BY category
  COLLATE BINARY`. Pass the normalized controls to the template. When a
  non-blank submitted category is absent from those rows, render it as one
  temporary selected option without writing it to SQLite.

### Effective-cart hardening

- Narrowly harden `build_cart()` (or a small helper it calls) without changing
  the valid session representation. Treat the cart as effective only when the
  session value is a mapping whose canonical positive product-ID key resolves
  to a current product and whose quantity has type `int`, is not `bool`, and is
  greater than zero. Ignore malformed keys, deleted products, strings,
  fractions, booleans, zero, and negative quantities.
- Query only validated IDs, retain stable product-ID order, and continue to
  calculate names, current unit prices, quantities, line totals, and subtotal
  from SQLite plus the valid session quantity in integer cents.
- Summary reads return filtered lines but never assign, pop, normalize, or
  otherwise repair `session["cart"]`. This preserves the original cart byte-for-
  byte on cart views, checkout views, validation failures, and database
  failures. Only successful checkout removes the entire `cart` key.

### Checkout and transaction seam

- Add `GET /checkout` and `POST /checkout` to the existing blueprint. GET
  redirects an ineffective/empty cart to `/cart` with the exact required flash;
  otherwise it renders authoritative lines and a labeled simulated-checkout
  form. POST rebuilds the effective cart before reading form validity; an empty
  effective cart returns the required understandable 400 and writes nothing.
- Normalize `customer_name` and `delivery_address` with `.strip()`. Validate
  both fields in one pass and retain all field-specific errors. An invalid
  response re-renders the authoritative summary with HTTP 400 and the normalized
  values. It neither writes rows nor changes the session.
- Keep persistence in one small `persist_order(lines, customer_name,
  delivery_address)` function. It begins one SQLite transaction, inserts the
  order, inserts one item snapshot per effective line, commits, and returns the
  new ID. On any SQLite insert or commit failure it rolls back and re-raises.
  A tiny private item-insert helper is an acceptable deterministic pytest seam:
  monkeypatch it to raise `sqlite3.DatabaseError` after one item insert, proving
  that the parent and earlier child insert roll back without adding a repository
  layer or test-only production branch.
- The POST route catches the database exception, returns an understandable
  rendered HTTP 500 without raw exception text, and preserves the complete
  session cart. After, and only after, a successful commit, it calls
  `session.pop("cart", None)` and redirects to the new confirmation URL.
- Add `GET /orders/<int:order_id>` that loads the order and its item rows in
  stable item-ID order. It must use saved item names/prices/totals rather than
  joining to current products. An absent ID returns an understandable 404.

## Ordered implementation groups

Each group is a coherent loop handoff. Complete its implementation and focused
tests before moving to the next group; keep every checkbox unchecked until the
named verification succeeds.

### Group 1 — Idempotent order schema and effective-cart foundation

- [ ] **G1.1** Extend `campus_shop/schema.sql` with the minimal `orders` and
  `order_item` definitions above, including positive-value, text-length, and
  order-item cascade constraints while deliberately leaving `product_id`
  without a product foreign key.
- [ ] **G1.2** Enable SQLite foreign-key enforcement on every request-scoped
  application connection without changing connection lifetime, row factory, or
  CLI behavior.
- [ ] **G1.3** Harden the shared effective-cart path against a non-mapping cart,
  malformed/noncanonical product IDs, deleted products, and non-positive or
  non-`int` quantities (including booleans), without mutating the session or
  changing valid base cart output.
- [ ] **G1.4** Extend `tests/test_database.py` (or add a focused order-schema test
  module) to verify exact new columns and checks, enabled foreign keys,
  `ON DELETE CASCADE`, absence of a product foreign key, fresh initialization,
  and repeat initialization after an order/item exists with unchanged products
  and saved rows.
- [ ] **G1.5** Extend cart tests with deliberately malformed and deleted-product
  session entries. Assert cart rendering ignores them without an exception,
  shows only effective lines/totals, leaves the original session mapping
  unchanged, and leaves all existing valid-cart tests passing.

Focused verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_database.py tests/test_cart.py
.\.venv\Scripts\python.exe -m compileall -q campus_shop tests
git diff --check
```

### Group 2 — Search, exact category filter, and no-results UI

- [ ] **G2.1** Add the normalization and SQL-`LIKE` literal escaping helper, then
  update `GET /` to construct only parameterized active predicates, combine
  search and category with `AND`, use explicit `NOCASE`/`BINARY` comparison as
  specified, and retain product-ID ordering.
- [ ] **G2.2** Query distinct categories in ascending case-sensitive order and
  pass products, categories, normalized `q`, normalized `category`, and unknown-
  category state to `products.html`.
- [ ] **G2.3** Add a labeled GET search/filter form to `products.html`, preserve
  both values after submission, render an unknown submitted category as a
  temporary selected option, and render the exact no-results message plus an
  unparameterized product-list link. Preserve the existing base empty-catalog
  fallback and every displayed product's detail link.
- [ ] **G2.4** Add `tests/test_catalog_filters.py` covering mixed-case partial
  name matches; description/category-only exclusions; literal `%`, `_`, and
  escape-character input; missing/blank search; labeled GET controls; exact
  case-sensitive known and unknown category behavior; deterministic category
  ordering; combined intersection; normalized control preservation; no-results
  text/reset link; stable product order; and unchanged detail navigation.
- [ ] **G2.5** Add only the minimal responsive CSS needed for the controls and
  no-results text to remain usable without JavaScript at desktop and mobile
  widths.

Focused verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_products.py tests/test_catalog_filters.py
.\.venv\Scripts\python.exe -m compileall -q campus_shop tests
git diff --check
```

### Group 3 — Checkout eligibility, validation, and atomic order persistence

- [ ] **G3.1** Add a checkout link/button to populated `cart.html`; implement
  `GET /checkout` so an effective non-empty cart renders `checkout.html` and an
  ineffective/empty cart redirects to `/cart` with `Add at least one product
  before checkout.`
- [ ] **G3.2** Create `checkout.html` with an explicit simulated-checkout
  heading/note, authoritative current names, unit prices, quantities, line
  totals, subtotal, and labeled `customer_name` and `delivery_address` fields.
  Provide accessible text locations for per-field errors and preserve normalized
  values on failure; request no payment or banking data.
- [ ] **G3.3** Implement `POST /checkout` with effective-cart-first validation,
  the exact required/over-length messages, simultaneous reporting of every
  invalid field, HTTP 400 re-rendering, and no writes or session mutation on
  invalid input.
- [ ] **G3.4** Implement the small atomic `persist_order` function and private
  item-insert seam. Derive every persisted name, product ID, quantity, unit
  price, line total, and total solely from effective session/database lines;
  ignore all fake browser fields. Roll back and re-raise every SQLite failure.
- [ ] **G3.5** On persistence failure, render an understandable HTTP 500 and
  preserve the original cart. On success only, remove the entire session
  `cart` key (including ineffective entries) and redirect to
  `/orders/<new_id>`.
- [ ] **G3.6** Add `tests/test_checkout.py` covering cart/checkout summary parity;
  checkout link visibility; empty and malformed-cart GET redirect/flash;
  empty-cart direct POST 400/no rows; missing, whitespace-only, over-length,
  and combined invalid fields with exact messages and normalized preservation;
  unchanged sessions/row counts after every invalid request; valid multi-line
  persisted snapshots/totals/timestamp; ignored fake form values; complete cart-
  key removal after commit; and a monkeypatched second-item failure proving 500,
  rollback of all rows, no redirect, no raw traceback, and unchanged session.

Focused verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_checkout.py
.\.venv\Scripts\python.exe -m compileall -q campus_shop tests
git diff --check
```

### Group 4 — Saved confirmation, documentation, and complete regression

- [ ] **G4.1** Implement `GET /orders/<int:order_id>` using one saved-order
  query and one saved-item query ordered by item ID. Return an understandable
  404 for an absent order without consulting or mutating the session cart.
- [ ] **G4.2** Create `order_confirmation.html` with a clear confirmation
  heading, numeric order ID, escaped customer name/address, creation timestamp,
  item snapshot names, two-decimal unit/line/order currency values, quantities,
  and navigation back to products. Preserve address line breaks safely with CSS
  or escaped template presentation, never trusted HTML.
- [ ] **G4.3** Add confirmation coverage (in `tests/test_checkout.py` or a focused
  `tests/test_orders.py`) for required saved values, two-decimal formatting,
  unknown-order 404, refresh idempotency, empty session after refresh, and
  immutability after current product name/price changes and source-product
  deletion.
- [ ] **G4.4** Update `README.md` for the completed two-step application: retain
  clean PowerShell setup/init/run/test instructions; document repeat-safe
  initialization, catalog search/category flow, simulated checkout and local-
  only personal-data warning; explicitly state there is no real payment,
  account, inventory, or production privacy/security guarantee.
- [ ] **G4.5** Run the full isolated suite and the documented clean-database
  browser flow. Correct only extension or regression defects in the approved
  scope; do not add excluded features.

Focused and final verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_checkout.py tests/test_orders.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q campus_shop tests
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

If confirmation tests remain in `tests/test_checkout.py` and no
`tests/test_orders.py` is created, omit that nonexistent filename from the
first command; the mandatory final `pytest -q` command is unchanged.

## Acceptance-criterion traceability

Test names are concrete targets; small naming changes are acceptable only when
the same behavior remains obvious in the test body.

| AC | Concrete implementation task(s) | Concrete pytest task(s) |
|---:|---|---|
| 1 | G2.1 escapes literal query metacharacters and applies name-only ASCII-insensitive substring matching in ID order. | G2.4 `test_name_search_is_case_insensitive_and_name_only` and parametrized `test_search_treats_like_metacharacters_literally`. |
| 2 | G2.1 treats blank search as inactive; G2.3 renders a labeled GET search field. | G2.4 `test_blank_search_shows_complete_catalog` and `test_catalog_controls_are_labeled_get_form`. |
| 3 | G2.1 uses exact binary category comparison; G2.2/G2.3 sort choices and preserve unknown values temporarily. | G2.4 `test_category_filter_is_exact_and_case_sensitive`, `test_blank_category_shows_all`, and `test_unknown_category_is_selected_and_returns_no_results`. |
| 4 | G2.1 joins active predicates with `AND`; G2.3 preserves both normalized controls. | G2.4 `test_combined_search_and_category_returns_intersection_and_preserves_controls`. |
| 5 | G2.3 renders the exact no-results message and clean reset URL. | G2.4 `test_no_results_has_exact_message_and_unfiltered_link`. |
| 6 | G1.3 supplies one authoritative helper; G3.1/G3.2 use it for both cart and checkout summaries. | G3.6 `test_checkout_summary_matches_authoritative_cart`. |
| 7 | G1.3 ignores malformed/deleted lines without mutation; G3.1/G3.3 implement distinct GET redirect and direct POST 400 behavior. | G1.5 `test_cart_ignores_ineffective_entries_without_repair`; G3.6 `test_empty_effective_cart_get_redirects_with_feedback` and `test_empty_effective_cart_post_is_400_without_rows`. |
| 8 | G3.3 normalizes and validates all fields in one pass with exact messages and no side effects. | G3.6 parametrized `test_invalid_checkout_reports_all_field_errors_and_preserves_state`. |
| 9 | G3.4 creates one transactionally consistent order plus one snapshot row per effective line. | G3.6 `test_valid_checkout_persists_one_order_and_effective_items`. |
| 10 | G3.4 consumes only rebuilt effective lines and the two allowed form fields. | G3.6 `test_checkout_ignores_browser_submitted_order_data`. |
| 11 | G3.4 rolls back through the controlled item-insert seam; G3.5 clears only after successful commit and returns understandable 500 on failure. | G3.6 `test_item_insert_failure_rolls_back_and_preserves_complete_cart` and `test_success_removes_entire_cart_key_only_after_commit`. |
| 12 | G3.5 redirects to the saved ID; G4.1/G4.2 render every saved value through the currency filter. | G3.6 `test_valid_checkout_redirects_to_confirmation`; G4.3 `test_confirmation_displays_saved_order_with_two_decimal_money`. |
| 13 | G4.1 reads snapshot columns without joining current products. | G4.3 `test_confirmation_uses_snapshots_after_product_change_or_deletion`. |
| 14 | G4.1 returns 404 for unknown IDs; confirmation GET performs no writes or cart changes. | G4.3 `test_confirmation_refresh_is_idempotent` and `test_unknown_order_returns_understandable_404`. |
| 15 | G1.1/G1.2 keep schema initialization additive and idempotent. | G1.4 `test_init_db_preserves_existing_order_items_and_seed_products`. |
| 16 | G1.5, G2.4, G3.6, and G4.3 add isolated coverage while preserving every base test. | G4.5 runs the complete suite; all extension tests use existing temporary-database fixtures and independent clients. |
| 17 | G4.4 documents clean setup and both user flows; G4.5 performs them on a new local database. | G4.5 runs the exact clean-checkout commands and manual smoke flow below. |

## Exact clean-checkout verification commands

Run from the repository root in PowerShell. The two initialization calls are
intentional and must preserve both catalog and saved-order data.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app campus_shop init-db
.\.venv\Scripts\python.exe -m flask --app campus_shop init-db
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m flask --app campus_shop run --debug
```

At `http://127.0.0.1:5000/`, search with mixed case, combine a name search and
category, clear both controls, and confirm a no-results query has a reset link.
Add two products with different quantities, compare cart and checkout totals,
submit blank fields and confirm both errors without losing the cart, then place
one simulated order. Confirm all saved fields/totals, refresh without creating a
duplicate, return to products, and verify the cart is empty. Repeat the visual
flow at a common mobile width with JavaScript disabled. Stop the server with
`Ctrl+C`.

## Definition of Done

- [ ] Groups 1–4 are complete, and all 17 acceptance criteria have the mapped
  implementation and automated evidence above.
- [ ] Existing base catalog/detail/cart routes and all base pytest tests still
  pass without changed valid behavior.
- [ ] Search treats `%`, `_`, and the escape character literally; exact category
  filtering is case-sensitive; combined results and normalized controls are
  deterministic; no-result recovery is visible.
- [ ] Cart and checkout summaries safely ignore ineffective entries without
  mutating the session and use current SQLite product data with integer-cent
  arithmetic.
- [ ] Field validation is server-side, complete in one response, uses the exact
  messages, preserves normalized values and the cart, and creates no rows on
  failure.
- [ ] One valid checkout atomically saves authoritative immutable snapshots;
  fake browser order data is ignored; rollback leaves no partial rows; the full
  cart key is cleared only after commit.
- [ ] Confirmation reads only saved order/item data, formats every monetary
  value to two decimals, survives current-product changes/deletion, is safe to
  refresh, and returns an understandable 404 for an unknown ID.
- [ ] Fresh and repeated `init-db` runs preserve products and existing orders;
  foreign-key behavior is enabled and tested.
- [ ] `README.md` reproduces setup, initialization, testing, search/filter, and
  simulated-checkout flows and clearly states the local teaching limitations.
- [ ] The full suite passes with isolated temporary databases, no network or
  test-order dependency, and the browser flow works without JavaScript at
  desktop and mobile widths with escaped output, associated labels, and textual
  feedback.
- [ ] No excluded feature, real credential, real personal data, generated
  database, virtual environment, cache, or machine-specific artifact is added.

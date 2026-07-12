# Campus Mini Shop Base Implementation Plan

## Planning status and iteration note

Iteration 1 created this plan after reviewing `docs/base-specification.md`,
`docs/base-review.md`, the planning-loop artifacts, and the repository contents.
Iteration 2 re-read those artifacts and critically checked the complete plan
against all 15 acceptance criteria and the current repository, which still has
no application code. This iteration clarified deterministic validation order,
safe handling of an update for a missing cart line, and exclusion of generated
local artifacts; no extension work was introduced. The plan incorporates every
approved correction from the review: deterministic cart redirects, HTTP 400
responses that preserve cart state, explicit unknown/absent-product behavior,
and repeatable database initialization. All implementation checkboxes remain
intentionally unchecked for the build stage.

## Scope boundary

Implement only the reviewed base flow: browse seeded products, view a product,
add it to a session cart, view the cart, update quantities, remove lines, and
display authoritative totals. Do not add accounts, checkout, payment, orders,
search, filtering, sorting, administration, inventory handling, coupons, tax,
shipping, reviews, recommendations, notifications, analytics, external APIs,
deployment, containers, or other extension work.

## Target project structure

```text
campus-mini-shop/
├── campus_shop/
│   ├── __init__.py          # create_app and local/test configuration
│   ├── db.py                # SQLite connection, teardown, init-db command
│   ├── schema.sql           # products table and idempotent seed statements
│   ├── shop.py              # catalog/cart routes and shared cart helpers
│   ├── templates/
│   │   ├── base.html
│   │   ├── products.html
│   │   ├── product_detail.html
│   │   ├── cart.html
│   │   └── error.html
│   └── static/
│       └── style.css
├── tests/
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_products.py
│   └── test_cart.py
├── .gitignore
├── requirements.txt
└── README.md
```

Keep application logic in this single small package. A separate model layer,
ORM, JavaScript bundle, database migration framework, and API are unnecessary
for the base scope.

## Fixed implementation decisions

### Application and database

- `create_app(test_config=None)` creates the Flask application, sets an
  instance-local default database path such as `instance/campus_shop.sqlite`,
  and reads a development secret from an environment variable with a clearly
  non-production local fallback. Tests pass an isolated `TESTING`, `DATABASE`,
  and `SECRET_KEY` configuration.
- `db.py` opens one `sqlite3` connection per request through `flask.g`, uses
  `sqlite3.Row`, closes it at teardown, and registers `flask init-db`.
- `schema.sql` uses `CREATE TABLE IF NOT EXISTS product` with `id INTEGER
  PRIMARY KEY`, required name/description/category, positive integer
  `price_cents`, and nullable image. Seed at least six distinct campus products
  in at least two categories with stable IDs and `INSERT OR IGNORE` (or an
  equivalent unique-key upsert) so rerunning initialization never duplicates
  them or destroys existing data.
- Store and calculate all prices and totals as integer cents. A shared Jinja
  filter/helper formats cents as `$0.00`; routes never accept browser-provided
  prices or totals.

### Session cart and shared behavior

- Store the cart under `session["cart"]` as a JSON-serializable mapping of
  string product IDs to positive integers, for example `{"1": 2, "4": 1}`.
  Reassign the mapping to the session after each mutation so Flask persists it.
- A shared quantity parser accepts only base-10 whole-number text greater than
  zero. For add only, a missing form field or a value empty after trimming
  defaults to `1`. For update, missing or empty is invalid. Non-numeric,
  fractional, signed, zero, and negative values are invalid.
- Validate the database product and the submitted quantity before copying and
  mutating the cart. On add, check product existence first so an unknown ID
  deterministically produces 404 even if its submitted quantity is also bad;
  otherwise invalid quantities produce 400 without partial session changes.
  Invalid update input likewise leaves the old quantity unchanged. An update
  for a product ID that has no current cart line returns an understandable 404
  without changing the cart.
- A shared cart-loading helper fetches current product rows for the IDs in the
  session, combines them with session quantities, and computes each line total
  and the subtotal in cents. Product names, categories, descriptions, prices,
  and totals never come from form input or copied session metadata.
- Render an understandable `error.html` response for 400 and 404 cases, with
  main navigation intact. Jinja autoescaping remains enabled; do not mark user
  input as safe.

### Routes and observable responses

| Method and path | Endpoint behavior |
|---|---|
| `GET /` | Query all products in stable ID order and render `products.html`. |
| `GET /products/<int:product_id>` | Render all required product fields and the labeled add form; return understandable 404 if absent. |
| `GET /cart` | Render database-backed cart lines, line totals, subtotal, mutation forms, or a clear empty state plus `$0.00`. |
| `POST /cart/add/<int:product_id>` | Validate product and add quantity, accumulate an existing line, flash confirmation, and redirect to `GET /cart`. |
| `POST /cart/update/<int:product_id>` | Require an existing cart line and valid quantity, replace it, flash confirmation, and redirect to `GET /cart`; malformed input returns 400 unchanged, while a missing cart line returns 404 unchanged. |
| `POST /cart/remove/<int:product_id>` | Remove only that key if present. Always redirect to `GET /cart`; flash confirmation only when a line was actually removed, and handle an absent line without error. |

All state changes are POST-only. Flask's default method handling should reject
GET requests to mutation URLs. `base.html` supplies links to Products and Cart,
renders flashed feedback as text (not color alone), and provides the page shell.
Forms have associated labels. CSS should provide a simple responsive layout
that remains usable on mobile and desktop without JavaScript. The image field
is presented as a local reference when supplied and as a clearly labeled local
placeholder when absent; no remote image service is introduced.

## Ordered implementation groups

Each group is a coherent handoff unit. Complete and verify a group before a
fresh agent starts the next one.

### Group 1 — Reproducible skeleton and product database

- [ ] **G1.1** Add explicit compatible Flask and pytest version constraints to
  `requirements.txt`, plus concise clean-checkout setup, initialization, run,
  and test instructions in `README.md`; add `.gitignore` entries for `.venv`,
  Flask instance data, SQLite files, Python caches, and pytest caches.
- [ ] **G1.2** Create the application factory and configuration described above,
  including automatic creation of the instance directory and test overrides.
- [ ] **G1.3** Implement the request-scoped SQLite helpers, teardown hook, schema,
  stable seed data (six or more products and two or more categories), and the
  idempotent `init-db` CLI command.
- [ ] **G1.4** Add `tests/conftest.py` fixtures that build a fresh temporary
  SQLite database for each test, initialize it through application code, and
  expose an isolated Flask test client/database connection without network or
  test-order dependencies.
- [ ] **G1.5** Add database tests proving required columns/data constraints,
  positive seed prices, seed counts/categories, and unchanged product count and
  IDs after invoking initialization twice.

### Group 2 — Catalog pages, navigation, and presentation

- [ ] **G2.1** Implement `GET /` and `GET /products/<int:product_id>` using
  parameterized SQLite queries and stable product ordering.
- [ ] **G2.2** Add the shared base, product-list, product-detail, and error
  templates with escaped output, required fields, exact two-decimal currency,
  labeled controls, Products/Cart navigation, and local image placeholder
  behavior.
- [ ] **G2.3** Add minimal responsive CSS and confirm the catalog/detail flow
  remains complete with JavaScript disabled and does not rely on color alone.
- [ ] **G2.4** Add product tests for all seeded listings and fields, correct
  detail data and price formatting, valid detail links/navigation, and an
  understandable HTTP 404 response for an unknown product; assert Products and
  Cart navigation is present on list, detail, and error responses.

### Group 3 — Cart read/add flow and authoritative totals

- [ ] **G3.1** Implement the centralized quantity parser, session-cart access,
  current-product lookup, cart-line construction, integer-cent total
  calculation, and currency formatting helpers.
- [ ] **G3.2** Implement `GET /cart`, including current database unit prices,
  quantities, line totals, subtotal, and the explicit empty state with `$0.00`.
- [ ] **G3.3** Implement the detail-page add form and
  `POST /cart/add/<int:product_id>` with empty-as-one behavior, accumulation,
  POST/redirect/GET, and flashed success feedback.
- [ ] **G3.4** Implement add validation so non-numeric, fractional, signed, zero,
  and negative quantities return an understandable HTTP 400 and do not mutate
  the cart; check existence first so an unknown product returns 404 and also
  leaves it unchanged even when the submitted quantity is invalid.
- [ ] **G3.5** Add cart tests for empty state, default/explicit quantity adds,
  duplicate accumulation without duplicate HTML lines, two distinct products,
  correct integer-cent line/subtotal rendering, current database price
  authority, redirect/flash behavior, invalid add cases, unknown add, POST-only
  mutation, cart-page navigation, and persistence across requests with one
  client session. Every invalid/unknown case must assert response status,
  understandable message, and unchanged session state.

### Group 4 — Update/remove flow and regression completion

- [ ] **G4.1** Add labeled update and remove forms to each cart line and implement
  `POST /cart/update/<int:product_id>` so a valid positive whole number replaces
  the existing quantity and redirects with confirmation; an ID with no current
  cart line returns an understandable 404 without changing the cart.
- [ ] **G4.2** Reject missing, empty, non-numeric, fractional, signed, zero, and
  negative update quantities with an understandable HTTP 400 while preserving
  the prior session quantity.
- [ ] **G4.3** Implement `POST /cart/remove/<int:product_id>` so only the selected
  line is removed, totals recalculate, successful removal redirects with
  confirmation, and removal of an absent key redirects without error or changes.
- [ ] **G4.4** Add update/remove tests covering valid recalculation, every invalid
  update class and state preservation, a missing update line returning 404
  unchanged, removal isolation, absent removal, confirmation feedback, redirect
  destinations, and POST-only methods; 400 and 404 cases must assert an
  understandable message as well as status and unchanged state.
- [ ] **G4.5** Run the full suite from a newly initialized local database, perform
  the documented browser smoke flow, and correct only base-scope defects found.

## Acceptance-criterion traceability

Every numbered criterion in the reviewed specification maps to implementation
and pytest work below. Test names are targets; minor naming changes are allowed
only if equivalent coverage remains obvious.

| AC | Concrete implementation task(s) | Concrete pytest task(s) |
|---:|---|---|
| 1 | G1.3 seeds six or more products in two or more categories; G2.1/G2.2 list every database product. | G1.5 `test_seed_data_is_complete` and G2.4 `test_product_list_shows_all_seeded_products`. |
| 2 | G2.1/G2.2 render the selected product's name, description, category, and formatted price. | G2.4 `test_product_detail_shows_correct_fields_and_price`. |
| 3 | G2.1/G2.2 return an understandable 404 for an unknown detail ID. | G2.4 `test_unknown_product_detail_returns_404`. |
| 4 | G3.2/G3.3 create one session line, default add quantity to one, and calculate its line total. | G3.5 `test_add_defaults_to_one_and_shows_correct_total`. |
| 5 | G3.3 increments the existing session-map entry rather than appending a line. | G3.5 `test_repeated_add_accumulates_single_line`. |
| 6 | G3.3 preserves other keys when adding a new product. | G3.5 `test_add_second_product_preserves_first`. |
| 7 | G4.1 replaces quantity; G3.1/G3.2 recalculate line and subtotal from cents. | G4.4 `test_update_quantity_recalculates_line_and_subtotal`. |
| 8 | G3.4 and G4.2 validate before mutation and return 400 with a message. | G3.5 parametrized `test_invalid_add_keeps_cart`; G4.4 parametrized `test_invalid_update_keeps_quantity`, including missing, empty, text, fraction, signed, zero, and negative inputs as applicable. |
| 9 | G4.3 removes only the requested key and reuses authoritative total calculation. | G4.4 `test_remove_one_item_preserves_other_and_recalculates`. |
| 10 | G3.2 renders a clear empty message and `$0.00`. | G3.5 `test_empty_cart_message_and_zero_subtotal`. |
| 11 | G3.1 stores only the cart mapping in Flask session and reuses it across requests. | G3.5 `test_cart_persists_across_navigation_and_refresh`. |
| 12 | G3.3, G4.1, and G4.3 use redirects to `/cart` and flash success messages. | G3.5 `test_successful_add_redirects_and_flashes`; G4.4 `test_successful_update_redirects_and_flashes` and `test_successful_remove_redirects_and_flashes`. |
| 13 | G3.4 returns 404 before mutation for unknown add; G4.3 makes absent removal a safe no-op redirect. | G3.5 `test_unknown_add_returns_404_and_keeps_cart`; G4.4 `test_remove_absent_item_redirects_and_keeps_cart`. |
| 14 | G1.4 plus G1.5, G2.4, G3.5, and G4.4 provide isolated database, product, cart, validation, subtotal, feedback, and 404 coverage. | G4.5 runs the full pytest suite; test files must collectively exercise every behavior listed in AC 1–13. |
| 15 | G1.1 documents and G1.2/G1.3 implement clean setup and idempotent initialization. | G1.5 tests repeat initialization; G4.5 executes the exact clean-checkout commands and smoke check below. |

## Exact local verification commands

Run these commands from the repository root in PowerShell. The database
initialization command is deliberately safe to run more than once.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app campus_shop init-db
.\.venv\Scripts\python.exe -m flask --app campus_shop init-db
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m flask --app campus_shop run --debug
```

After the final command, use `http://127.0.0.1:5000/` for a manual smoke test:
browse at least two products; open a detail; add with blank and explicit
quantities; confirm accumulation and session persistence; add a second item;
try invalid add/update values and confirm existing state remains; update a
valid quantity; remove one line; remove all lines; and confirm the final empty
message and `$0.00` subtotal. Stop the development server with `Ctrl+C`.

## Definition of Done

- [ ] Only the reviewed base scope is implemented; no excluded extension is
  present.
- [ ] Groups 1–4 are complete and all acceptance criteria 1–15 have both the
  mapped implementation and automated coverage shown above.
- [ ] A fresh checkout can install dependencies, initialize a database, and
  start the application using the documented commands.
- [ ] Running `init-db` twice succeeds and does not duplicate or erase seeded
  products.
- [ ] `.\.venv\Scripts\python.exe -m pytest -q` passes with an isolated
  temporary database, no
  network access, no ordering dependency, and coverage of happy and failure
  paths.
- [ ] The manual browser flow works without JavaScript at desktop and mobile
  widths, with clear navigation, labels, feedback, error messages, and escaped
  content.
- [ ] All cart mutations use POST; successful mutations redirect to the cart;
  invalid quantities preserve state and return 400; required unknown IDs return
  404; absent removal is a safe redirect.
- [ ] Cart line totals and subtotal are calculated from current SQLite prices
  and positive session quantities in integer cents and display with exactly two
  decimal places.
- [ ] No real credential, personal information, generated local database,
  virtual environment, cache, or other machine-specific artifact is committed.

# Campus Mini Shop: Extension Specification

## 1. Purpose

This extension adds two small, visible capabilities to the completed Campus
Mini Shop base system. First, a visitor can narrow the catalog by product name
and category. Second, a visitor with a non-empty cart can complete a simulated
checkout that saves an order and displays an order confirmation.

The extension remains a local teaching application. It demonstrates query
handling, server-side form validation, a transactional parent/child database
write, and immutable order-time price snapshots without introducing accounts,
real payments, inventory, or production e-commerce infrastructure.

## 2. Extension User Flow

### 2.1 Search and filtering

1. The visitor opens the existing product-list page.
2. The visitor may enter all or part of a product name, select one exact
   category, or use both controls together.
3. The visitor submits the controls with a GET request.
4. The page displays only products that satisfy every active condition, while
   preserving the submitted controls.
5. If nothing matches, the page shows a clear no-results message and a way to
   return to the complete catalog.

### 2.2 Simulated checkout

1. The visitor adds at least one product to the existing session cart.
2. From the cart page, the visitor opens checkout.
3. The checkout page summarizes the authoritative current cart and asks for a
   customer name and delivery address.
4. The visitor submits the form. The server validates both fields and rebuilds
   the cart from SQLite rather than trusting browser-submitted products, prices,
   quantities, or totals.
5. After a valid submission, the server saves one order and its order items in
   one database transaction, using integer-cent price snapshots.
6. Only after that transaction commits successfully, the server clears the
   session cart and redirects to the saved order's confirmation page.
7. The confirmation page displays the order number, customer and delivery
   details, item snapshots, quantities, line totals, and order total.

## 3. Functional Requirements

### FR-E1: Search products by name

- The product-list page must provide a labeled product-name search field.
- Search must use the `q` query-string parameter and a GET request so the result
  can be refreshed or bookmarked without changing server state.
- The server must trim leading and trailing whitespace from `q`.
- A non-blank search must match when it occurs anywhere in a product name,
  without regard to letter case. Product description and category text must not
  influence name-search matches.
- A missing, empty, or whitespace-only `q` must apply no name restriction.
- Results must retain the base system's stable product-ID ordering.

### FR-E2: Filter products by exact category

- The product-list page must provide a labeled category control whose choices
  are the distinct categories currently present in SQLite, plus an `All
  categories` choice.
- Category filtering must use the `category` query-string parameter and a GET
  request.
- The server must trim leading and trailing whitespace from `category`.
- A non-blank category value must match the stored category value exactly; it
  must not use substring matching or silently map one category to another.
- A missing, empty, or whitespace-only category value must apply no category
  restriction.
- A non-blank category not present in the database is valid query input but
  produces zero products rather than an HTTP error.

### FR-E3: Combine and present catalog controls

- When both name and category conditions are active, a product must satisfy
  both conditions to appear.
- The submitted normalized search text and category must remain visible in the
  controls after submission, including when there are no matches.
- When no product matches, the page must display the explicit message `No
  products match your search and filter.` rather than a blank product grid.
- The no-results state must include a link that removes both query parameters
  and returns to the full product list.
- Existing product-detail links and base catalog behavior must continue to work
  for every displayed result.

### FR-E4: Open checkout only for an effective non-empty cart

- A populated cart page must provide a clear link or button to `GET /checkout`.
- An effective checkout cart means at least one session-cart entry resolves to
  a current SQLite product and has a positive whole-number quantity.
- `GET /checkout` with no effective cart lines must not display a checkout form;
  it must redirect to `/cart` and show `Add at least one product before
  checkout.`
- The checkout page must show each current product name, authoritative current
  unit price, quantity, line total, and subtotal, all calculated on the server
  using integer cents.
- The checkout form must contain labeled `customer_name` and
  `delivery_address` fields and submit to `POST /checkout`.

### FR-E5: Validate checkout deterministically on the server

- The server must read both fields as text and trim leading and trailing
  whitespace before validation and persistence.
- `customer_name` is valid only when its trimmed length is between 1 and 100
  characters inclusive.
- `delivery_address` is valid only when its trimmed length is between 1 and 300
  characters inclusive.
- Missing fields, whitespace-only values, and values over their maximum lengths
  are invalid. Internal spaces and line breaks are otherwise preserved; the
  application does not attempt to verify whether a person or address is real.
- Validation must check the effective cart before form fields. A direct
  `POST /checkout` with no effective cart must return HTTP 400 with `Your cart
  is empty; an order was not created.`
- With a non-empty effective cart, all submitted fields must be validated in one
  pass. An invalid submission must return HTTP 400, re-render checkout with the
  authoritative cart summary, preserve the submitted field values, and show a
  specific message beside every invalid field.
- The required-field messages must be `Enter your name.` and `Enter a delivery
  address.` The over-length messages must be `Name must be 100 characters or
  fewer.` and `Delivery address must be 300 characters or fewer.`
- Any validation failure must create no order or order-item rows and must leave
  the session cart unchanged.
- Browser-side `required` or length attributes may improve usability but must
  not replace these server-side rules.

### FR-E6: Persist an order and immutable item snapshots

- A valid checkout must create exactly one `orders` row and one `order_item`
  row for every effective cart line.
- The server must calculate the order from current database products and session
  quantities. It must ignore any browser-submitted product ID, product name,
  price, quantity, line total, or order total.
- Each order item must snapshot the product name and current unit price in
  integer cents at checkout time. Later changes to the product table must not
  change a saved confirmation.
- Each saved line total must equal snapshot unit price times quantity, and the
  saved order total must equal the sum of its saved line totals.
- The order row and all associated item rows must be inserted in one SQLite
  transaction. If any insert or commit fails, the transaction must roll back,
  the cart must remain unchanged, and no partial order may remain.
- After a successful commit, and not before, the application must remove only
  the `cart` key from the current session and redirect to the new order's
  confirmation page.

### FR-E7: Display an order confirmation

- `GET /orders/<int:order_id>` must load the saved order and saved item
  snapshots, not rebuild the page from the current cart or current product
  prices.
- The page must display a clear confirmation heading, numeric order ID,
  customer name, delivery address, creation timestamp, each item name, snapshot
  unit price, quantity, line total, and the saved order total.
- Every monetary value must be formatted with exactly two decimal places.
- Requesting an unknown order ID must return an understandable HTTP 404.
- Refreshing a confirmation page must not create another order or alter the
  now-empty session cart.
- The confirmation page must provide navigation back to the product list.

## 4. Data and Schema Additions

The existing `product` table and session-cart representation remain unchanged.
The extension adds the following SQLite tables.

### 4.1 `orders`

| Field | Requirement |
|---|---|
| `id` | Unique integer primary key generated by SQLite |
| `customer_name` | Required trimmed text, 1-100 characters |
| `delivery_address` | Required trimmed text, 1-300 characters |
| `total_cents` | Required non-negative integer equal to the saved item-total sum |
| `created_at` | Required creation timestamp with a deterministic SQLite default |

### 4.2 `order_item`

| Field | Requirement |
|---|---|
| `id` | Unique integer primary key generated by SQLite |
| `order_id` | Required reference to `orders.id`, with cascade deletion allowed |
| `product_id` | Required identifier of the source product at checkout time |
| `product_name` | Required non-empty snapshot of the product name |
| `unit_price_cents` | Required positive integer snapshot of the unit price |
| `quantity` | Required positive integer snapshot of the purchased quantity |
| `line_total_cents` | Required positive integer equal to unit price times quantity |

- SQLite foreign-key enforcement must be enabled for application database
  connections.
- Order confirmation must use `product_name`, `unit_price_cents`, quantity, and
  line total from `order_item`; `product_id` is provenance and must not be used
  to replace the snapshots with current catalog data.
- The project continues to use integer cents for all storage and arithmetic.

## 5. Migration and Idempotency Expectations

- The existing documented `flask --app campus_shop init-db` command must create
  the new tables for a fresh database and add them to an existing base-system
  database without deleting or rewriting products.
- Schema creation must use `CREATE TABLE IF NOT EXISTS` or equivalent
  idempotent behavior.
- Running initialization repeatedly must preserve all existing orders and order
  items and must not duplicate seed products.
- Tests must cover both a fresh initialization and repeated initialization after
  an order exists.
- No external migration framework is required for this two-step teaching
  project; the idempotent schema script is the required migration mechanism.

## 6. Acceptance Criteria

The extension is accepted when all of the following observable checks pass:

1. A mixed-case partial `q` value returns every product whose name contains it
   case-insensitively and excludes products matched only by description or
   category.
2. Blank or whitespace-only `q` displays the complete catalog, and the search
   form uses GET with a labeled input.
3. Selecting one category displays only products whose stored category equals
   it exactly; blank category displays all categories, and an unknown non-blank
   category displays the no-results state without an error.
4. Using search and category together returns only the intersection of both
   conditions and preserves both normalized values in the controls.
5. A query with no matches displays `No products match your search and filter.`
   and a link that restores the unfiltered catalog.
6. A non-empty cart can open checkout and sees the same authoritative names,
   quantities, current prices, line totals, and subtotal as the cart page.
7. `GET /checkout` with an empty effective cart redirects to `/cart` with the
   required feedback; direct empty-cart `POST /checkout` returns HTTP 400 and
   creates no database rows.
8. Missing, blank, and over-length customer-name and delivery-address values
   produce the specified field messages in one HTTP 400 checkout response,
   preserve submitted values, create no rows, and leave the cart unchanged.
9. One valid submission creates exactly one order and one item per effective
   cart line with the correct customer data, quantities, snapshot names,
   integer-cent prices, line totals, timestamp, and summed order total.
10. Browser-submitted fake prices, quantities, product names, or totals cannot
    affect the persisted order; authoritative database and session values win.
11. The session cart is cleared only after the complete order transaction
    commits; a simulated database failure leaves the cart unchanged and no
    partial order or item rows.
12. Successful checkout redirects to one confirmation page that displays all
    required saved values with two-decimal currency formatting.
13. Changing a product name or price after checkout does not change the saved
    order confirmation, proving that item snapshots are authoritative.
14. Refreshing confirmation does not create duplicate orders, and an unknown
    order ID returns an understandable HTTP 404.
15. Running database initialization repeatedly after an order exists preserves
    that order and its items and does not duplicate products.
16. All existing base-system tests continue to pass, and new isolated pytest
    coverage verifies search, filtering, validation, persistence, transaction
    rollback, cart-clearing timing, snapshots, confirmation, 404, and
    initialization behavior without network access or test-order dependence.
17. The documented local initialization, run, test, catalog-search, and
    simulated-checkout flow works from a clean project checkout.

## 7. Nonfunctional Constraints

### 7.1 Required technology and structure

- Continue using Python, Flask, SQLite, server-rendered Jinja HTML, CSS, and
  pytest.
- Keep the extension within the existing small application package; do not add
  an ORM, JavaScript framework, separate API, database server, or external
  service.
- Core search, filter, checkout, and confirmation flows must work without
  JavaScript.

### 7.2 Reliability, security, and privacy

- Use parameterized SQL for all query values and persisted form values.
- Continue relying on Jinja autoescaping; user-submitted name and address text
  must never be rendered as trusted HTML.
- Checkout state changes must use POST followed by redirect on success.
- Customer name and delivery address are collected only for the local simulated
  order. The project must not transmit them to any external service or include
  real personal data in committed seed or test fixtures.
- No production security, authorization, or privacy guarantee is claimed. This
  limitation must remain clear in user-facing documentation.

### 7.3 Usability and accessibility

- Search, category, name, and address controls must have associated labels.
- Validation and no-results information must be conveyed in text, not color
  alone.
- Search results, checkout, and confirmation must remain usable at common
  desktop and mobile viewport widths.
- The checkout page must clearly identify the flow as simulated and must not
  request card or banking information.

### 7.4 Testability and reproducibility

- Extension tests must use isolated temporary databases and Flask test clients.
- Tests must not depend on network access, real personal information, existing
  local orders, test execution order, or wall-clock display formatting beyond
  proving that a timestamp is saved and shown.
- Existing base behavior and extension behavior must be verifiable with the
  same short local setup documented for the project.

## 8. Explicit Exclusions

The extension must not add:

- User registration, login, profiles, roles, or authentication.
- Real payment, payment-provider simulation, card fields, banking data, or
  refunds.
- Email, SMS, receipts sent outside the application, or other notifications.
- Inventory counts, stock reservation, stock decrement, back orders, or
  concurrency handling.
- Product or order administration, dashboards, or status management.
- Shipping rates, delivery tracking, tax, coupons, discounts, or multiple
  currencies.
- Product recommendations, reviews, ratings, wish lists, or analytics.
- External APIs, remote images, cloud databases, cloud deployment, containers,
  or production infrastructure.

## 9. Extension Stage-Completion Checklist

This specification stage is complete when:

- [x] The extension purpose and both user flows are documented.
- [x] Search, exact filtering, combined-query, and no-results behavior are
  deterministic and testable.
- [x] Checkout eligibility, field validation, error messages, persistence, and
  cart-clearing timing are deterministic and testable.
- [x] Order and order-item schema additions include integer-cent immutable
  snapshots and transaction expectations.
- [x] Acceptance criteria cover happy paths, invalid input, authoritative data,
  rollback, confirmation, 404, regression, and reproducibility behavior.
- [x] Nonfunctional constraints and explicit exclusions keep the extension
  small and locally reproducible.
- [x] Migration and repeated-initialization expectations preserve base data and
  saved orders.
- [ ] An independent requirements reviewer has checked this extension for
  ambiguity, missing cases, and unnecessary scope.
- [ ] Approved review corrections have been incorporated before extension
  implementation planning begins.

# Campus Mini Shop: Base System Specification

## 1. Purpose

Campus Mini Shop is a small, locally run shopping website for common campus supplies. The base system demonstrates a complete but intentionally limited shopping flow: a visitor can browse products, inspect one product, place products in a temporary cart, change cart quantities, remove products, and see the current subtotal.

The base system is designed for a teaching assignment. It must be easy for a teaching assistant to install, run, understand, and test on a local computer. It does not attempt to provide accounts, checkout, payment, order processing, or production e-commerce features.

## 2. Personas

### 2.1 Student shopper

A student who wants to browse inexpensive campus supplies and assemble a temporary shopping cart. The student does not need to create an account or provide personal information.

### 2.2 Teaching assistant

A reviewer who installs the project locally, starts the Flask application, follows the user flow, and runs automated tests to verify that the documented requirements are satisfied.

## 3. Base-System User Flow

1. The visitor opens the product-list page.
2. The visitor browses the seeded products.
3. The visitor opens a product-detail page.
4. The visitor adds one or more units of a product to the cart.
5. The visitor opens the cart and may update quantities or remove items.
6. The system recalculates and displays the cart subtotal.

The cart is temporary and belongs only to the visitor's current Flask session. The flow ends at the cart; there is no checkout in the base system.

## 4. Functional Requirements

### FR-1: Browse products

- The home page must display all seeded products that are available in the SQLite database.
- Each product listing must show at least its name, price, category, and a link to its detail page.
- Prices must be displayed as currency with exactly two decimal places.
- The product list must be useful without client-side JavaScript.

### FR-2: View product details

- A visitor must be able to open a detail page for any existing product.
- The detail page must show the product's name, description, category, price, and image reference or local placeholder presentation.
- Requesting a product ID that does not exist must return an HTTP 404 response with an understandable page or message.

### FR-3: Add a product to the cart

- A visitor must be able to add an existing product to the session cart from the product list or product-detail page.
- The add action must accept a positive whole-number quantity; the default quantity may be one.
- Adding a product that is already in the cart must increase that product's quantity rather than create a duplicate cart line.
- Invalid quantities and nonexistent product IDs must not corrupt or silently create cart data.
- After a successful add action, the visitor must be redirected to a useful page, such as the cart or the originating product page.

### FR-4: View the cart

- The cart page must display every product currently stored in the session cart.
- Each cart line must show the product name, unit price, quantity, and line total.
- An empty cart must display a clear empty-state message rather than an error or blank table.
- Cart data must persist across requests within the same browser session.

### FR-5: Update cart quantities

- A visitor must be able to replace a cart line's quantity with a positive whole number.
- After an update, the cart line total and subtotal must reflect the new quantity.
- Invalid values, including non-numeric, fractional, zero, and negative quantities, must be rejected or handled without leaving an invalid quantity in the cart.

### FR-6: Remove cart items

- A visitor must be able to remove an individual product from the cart.
- Removing one product must not change other cart lines.
- Attempting to remove a product that is not in the cart must be handled safely and must not produce a server error.

### FR-7: Calculate and display subtotal

- The cart page must display a subtotal equal to the sum of each unit price multiplied by its quantity.
- The subtotal and line totals must be displayed as currency with exactly two decimal places.
- The server must calculate authoritative totals from current database prices and session quantities; totals submitted by the browser must not be trusted.
- An empty cart must have a subtotal of `$0.00`.

### FR-8: Basic navigation and feedback

- Every main page must provide clear navigation to the product list and cart.
- State-changing form submissions must use POST requests.
- The application should provide clear success or validation feedback when a cart action completes or cannot be completed.

## 5. Data Requirements

### 5.1 Product data

Products must be stored in SQLite and seeded so that a fresh local installation has products to browse. Each product must contain:

| Field | Requirement |
|---|---|
| `id` | Unique integer identifier and primary key |
| `name` | Required, human-readable product name |
| `description` | Required short product description |
| `category` | Required category label |
| `price_cents` | Required positive integer price in cents |
| `image` | Optional local image path or placeholder identifier |

The seed data must contain at least six distinct campus-related products and at least two categories. Seed prices must be positive.

### 5.2 Cart data

- The cart must be stored in the Flask session, not in a database table.
- The session cart should map product identifiers to positive whole-number quantities.
- Product names and prices must be loaded from SQLite when rendering totals so that stale client data is not treated as authoritative.
- No personally identifying information may be collected for the base system.

### 5.3 Monetary calculations

- Monetary values must be stored and calculated as integer cents to avoid floating-point rounding errors.
- Currency formatting must occur only when values are presented to the user.

## 6. Acceptance Criteria

The base system is accepted when all of the following observable checks pass:

1. Starting with a fresh database shows at least six seeded products across at least two categories on the product-list page.
2. Selecting a product opens a detail page containing the correct name, description, category, and two-decimal price.
3. Requesting an unknown product detail returns HTTP 404 rather than HTTP 500.
4. Adding one unit of a product creates one cart line with quantity one and the correct line total.
5. Adding the same product again increases its existing quantity and does not create a duplicate line.
6. Adding a second product preserves the first product and shows two distinct cart lines.
7. Updating a quantity to a positive whole number updates both the line total and subtotal.
8. Invalid add or update quantities do not leave zero, negative, fractional, or non-numeric quantities in the cart.
9. Removing one cart item removes only that item and recalculates the subtotal.
10. An empty cart displays a clear message and a subtotal of `$0.00`.
11. Refreshing or navigating between pages within the same browser session preserves cart contents.
12. Automated pytest coverage verifies the main product, cart, validation, subtotal, and 404 behaviors.
13. The documented local setup and test commands work from a clean project checkout.

## 7. Nonfunctional Constraints

### 7.1 Required technology

- Python and Flask for the web application.
- SQLite for persistent product data.
- Server-rendered HTML templates and CSS for the interface.
- Minimal JavaScript only where it improves usability; core flows must work without it.
- pytest for automated tests.

### 7.2 Simplicity and maintainability

- The project must run locally without a separate database server or external service.
- Application structure, route names, templates, and tests must be understandable to a student familiar with introductory Python and web concepts.
- Configuration suitable for local development and testing must be separated where practical.
- Repeated business logic, especially cart validation and total calculation, should be centralized rather than copied between routes.

### 7.3 Usability and accessibility

- Pages must use clear headings, labels, buttons, and navigation.
- Forms must have associated labels and understandable validation messages.
- The layout must remain usable at common desktop and mobile viewport widths.
- Color must not be the only way important information is communicated.

### 7.4 Reliability and security boundaries

- User-supplied quantities and route identifiers must be validated on the server.
- Templates must use Flask/Jinja escaping rather than rendering untrusted HTML as safe.
- A development secret key may be configured locally, but no real credentials or secrets may be committed.
- The application must respond predictably to invalid product IDs and malformed cart input without an uncaught server error.

### 7.5 Testability and reproducibility

- Tests must use an isolated temporary database and test client/session where appropriate.
- Tests must not depend on network access, test order, or a user's existing local database.
- Setup, run, and test instructions must require only a small number of documented commands.

## 8. Explicit Exclusions from the Base System

The following features are outside the base-system scope and must not be implemented in this stage:

- User registration, login, profiles, or role-based access.
- Real or simulated payment.
- Checkout forms, shipping details, order placement, order confirmation, or order persistence.
- Product search, category filtering controls, or sorting controls.
- Administrative product, inventory, or order management.
- Inventory reservation, stock decrementing, or concurrent stock handling.
- Coupons, tax, shipping fees, recommendations, reviews, ratings, or wish lists.
- Email, SMS, notifications, analytics, or external APIs.
- Cloud hosting, deployment automation, containers, or production infrastructure.

Search, category filtering, simulated checkout, and order persistence may be considered only as a separately specified extension after the base system has been completed and verified.

## 9. Stage-Completion Checklist

The base specification stage is complete only when:

- [ ] Purpose and intended personas are documented.
- [ ] The end-to-end base user flow is documented.
- [ ] Each required base feature has a numbered functional requirement.
- [ ] Product, cart, and monetary data rules are unambiguous.
- [ ] Acceptance criteria are observable and testable.
- [ ] Technology, usability, reliability, and testing constraints are recorded.
- [ ] Excluded features clearly prevent extension work from entering the base stage.
- [ ] A separate reviewer has checked this specification for ambiguity, missing cases, and unnecessary complexity.
- [ ] Any approved review corrections have been incorporated before implementation planning begins.


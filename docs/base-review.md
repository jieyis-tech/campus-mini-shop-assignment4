# Base System Specification Review

## Review scope

This review checks `docs/base-specification.md` against the Assignment 4 instructions and the project goal of producing a small, locally reproducible interactive application. It covers only the base system. No extension design or implementation is approved by this review.

## Must Fix

### 1. Invalid-input behavior allowed multiple incompatible implementations

**Finding:** FR-3 and FR-5 previously said invalid quantities could be “rejected or handled,” without defining a response status or whether the existing cart should change. Different implementation iterations could therefore satisfy the wording while behaving differently, and tests would not have one expected result.

**Correction applied:** Invalid add and update quantities now return an understandable HTTP 400 response. An invalid add leaves the cart unchanged, and an invalid update preserves the existing quantity. The acceptance criteria now state these observable outcomes.

### 2. Successful-add destination was not deterministic

**Finding:** FR-3 allowed a redirect to the cart or to the originating page. This made the required user flow and test expectations ambiguous.

**Correction applied:** A successful add now redirects to the cart. Successful add, update, and remove operations must display brief confirmation feedback there.

### 3. Fresh-database setup was not sufficiently reproducible

**Finding:** The specification required seeded products and clean-checkout instructions but did not explicitly require a safe, repeatable database-initialization command. A TA could encounter missing data or duplicated seed rows when following setup instructions more than once.

**Correction applied:** The reproducibility constraints now require one documented, idempotent initialization command that creates and seeds SQLite without duplicating products.

## Should Fix

### 1. Product-list add behavior increased scope without an acceptance check

**Finding:** FR-3 allowed adding from the product list or detail page. The phrase did not clearly require one location or both, while the documented flow already sends the visitor through product details. Supporting list-page quantity forms would add interface and validation work without strengthening the base-system demonstration.

**Correction applied:** The required add form is now limited to the product-detail page. An implementation may later add another entry point only if it does not alter the specified behavior, but it is not part of base acceptance.

### 2. Missing and unknown cart actions needed explicit outcomes

**Finding:** The original text required safe handling but did not say what the user or tests should observe.

**Correction applied:** Adding an unknown product now returns HTTP 404 without changing the cart. Removing a product absent from the cart leaves the cart unchanged and redirects normally to the cart. These cases were added to acceptance criteria.

## Accepted

### Assignment structure

The base specification is appropriate for the first of the assignment's two required steps. It can be completed through separate specification, review, planning, and build stages, with a repository commit after each stage. Loop use belongs in a later planning or build stage and is not incorrectly claimed in this document.

### Nontrivial but controlled scope

The product database, server-rendered pages, session cart, server-side validation, and automated tests constitute a small interactive backend. The campus theme, original seed data, and project-specific implementation keep this from being an exact copy of a classroom example. Accounts, checkout, payment, search, filtering, and order persistence are correctly excluded from the base step.

### Technology and reproducibility

Flask, SQLite, server-rendered templates, and pytest are suitable for a TA to run locally without network services. Integer-cent price storage and an isolated test database reduce avoidable implementation and testing problems.

### Testability

The revised acceptance criteria cover the central happy paths and failure paths: seeded products, details, 404 handling, cart accumulation, session persistence, quantity validation, subtotal calculation, feedback, removal, and clean-checkout setup.

## Review decision

**Approved for planning.** All Must Fix findings and the narrowly scoped Should Fix findings have been incorporated into `docs/base-specification.md`. The base scope remains intentionally limited, and extension features must remain deferred until the base system has been implemented, tested, and committed as its own step.

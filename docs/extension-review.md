# Extension Specification Review

## Review scope

This review checks `docs/extension-specification.md` against the completed base
system and the Assignment 4 goal of a small, locally reproducible Step 2. It
covers requirements only. No extension implementation is claimed or approved
by this document.

## Must Fix

### 1. Literal substring search was underspecified

**Finding:** The specification required a name substring search but did not say
whether SQL `LIKE` metacharacters such as `%` and `_` were user-visible
wildcards. A direct `LIKE '%' || ? || '%'` implementation would make those
characters match products that do not literally contain them.

**Correction applied:** Search remains ASCII case-insensitive for the English
catalog, and SQL wildcard characters must be escaped and matched literally.
Acceptance coverage now calls out this boundary.

### 2. Unknown categories contradicted control-state preservation

**Finding:** The category control was limited to values currently stored in
SQLite, while an unknown query value was valid and all submitted values had to
remain visible in the controls. A select element cannot preserve an option it
does not contain.

**Correction applied:** Stored choices are sorted deterministically. An unknown
non-blank submitted value is rendered as a temporary selected option, produces
zero results, and is never inserted into the database. Exact matching is now
explicitly case-sensitive.

### 3. "Effective cart" did not define malformed session behavior

**Finding:** The completed base cart assumes its signed session map was produced
by valid routes. Extension tests and stale sessions can nevertheless contain a
deleted product ID or a malformed quantity. The prior wording did not say
whether these entries should crash, be removed, be purchased, or remain in the
session.

**Correction applied:** Only current products paired with positive integer
quantities are effective; booleans, strings, fractions, non-positive values,
malformed IDs, and deleted products are ignored safely. Summary reads do not
mutate the session. Success removes the entire cart key, while every failure
preserves it unchanged.

### 4. Failed-transaction response was not observable

**Finding:** Rollback and cart preservation were required, but the HTTP outcome
of an insert or commit failure was unspecified. Implementations could redirect,
leak a traceback, or return incompatible statuses while satisfying the data
rules.

**Correction applied:** A database failure must roll back and return an
understandable HTTP 500 without a confirmation redirect or raw traceback. The
acceptance check now includes the response as well as database and session
state.

### 5. Schema constraints contained avoidable ambiguity

**Finding:** A valid order is necessarily positive because checkout requires at
least one positive-price, positive-quantity line, yet `total_cents` allowed zero.
The timestamp default was called deterministic without naming its format, and
the order-item foreign-key language said cascade deletion was merely "allowed."
The intended relationship between `product_id` and mutable catalog rows was
also unclear.

**Correction applied:** The order total is positive; `created_at` uses SQLite
`CURRENT_TIMESTAMP` in its UTC text format; `order_id` requires `ON DELETE
CASCADE`; and snapshot provenance `product_id` deliberately has no product
foreign key so historical orders survive catalog deletion.

## Should Fix

### 1. Invalid-form value preservation needed one canonical form

**Finding:** Inputs were trimmed before validation and persistence, but an
invalid response had to preserve "submitted" values. That could mean either raw
whitespace or normalized values and would produce inconsistent tests.

**Correction applied:** The invalid form re-renders normalized, trimmed values.
Internal spaces and line breaks remain preserved as already specified.

### 2. Corrupt cart hardening slightly broadens the base helper

**Finding:** Checkout should reuse the base system's centralized cart-building
logic, but that helper currently assumes integer-convertible product keys and
integer quantities. Implementing the corrected effective-cart rule will require
a narrow hardening of that shared helper.

**Recommendation for planning:** Treat this as extension integration work, keep
valid base behavior unchanged, and add regression tests. Do not introduce a new
cart storage format or automatic session repair.

### 3. Transaction-failure testing should use a controlled test seam

**Finding:** The rollback requirement is important, but relying on a real disk
or lock failure would make tests fragile and platform-dependent.

**Recommendation for planning:** Keep order persistence in one small function or
otherwise patch a deterministic database operation in tests. The application
must remain simple; no repository layer, ORM, or migration framework is needed.

## Accepted

### Extension scope

Search, one exact category filter, simulated checkout, saved order snapshots,
and one confirmation page form a visible but controlled second step. Accounts,
payments, inventory, administration, tax, shipping calculations, external
services, and client-side frameworks remain correctly excluded.

### Integration with the base system

The extension builds on the existing product table, session cart, integer-cent
calculations, Flask routes, Jinja templates, SQLite connection, and pytest
fixtures. The base flow remains independently recognizable, and existing tests
are explicitly required to continue passing.

### Authoritative and immutable order data

Rebuilding the cart from SQLite and the signed session prevents browser form
fields from controlling prices or totals. Saving product names, prices,
quantities, line totals, and the order total provides a clear, testable snapshot
that confirmation pages can render without depending on the current catalog.

### Migration and reproducibility

Idempotent schema creation extends both fresh and existing base databases
without a heavyweight migration dependency. Repeated initialization preserving
products and orders is appropriate for a small teaching application and is
covered by an acceptance check.

### Validation and request semantics

The revised rules specify GET for read-only catalog and checkout pages, POST for
order creation, deterministic empty-cart and invalid-field responses, PRG after
success, and saved-data confirmation. These behaviors are suitable for isolated
Flask client tests without network access.

## Review decision

**Approved for extension planning.** All Must Fix findings and the necessary
wording correction have been incorporated into
`docs/extension-specification.md`. The Should Fix implementation notes should be
carried into the plan without expanding the product scope.

# Campus Mini Shop

Campus Mini Shop is a small two-step Flask teaching application. The base
system lets visitors browse campus supplies and manage a temporary session
cart. The extension adds product-name search, an exact category filter, and a
simulated checkout that saves immutable order snapshots in local SQLite.

## Local setup

From the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app campus_shop init-db
.\.venv\Scripts\python.exe -m flask --app campus_shop run --debug
```

Open `http://127.0.0.1:5000/` after the server starts. The `init-db` command is
safe to run again. It creates missing catalog and order tables without
duplicating products or deleting existing products or orders, so the same
command upgrades a base-system database to the extension schema.

## Try the completed flows

On the product page, enter part of a product name, choose a category, or use
both controls together. Search and filter use a normal GET request, so clearing
both controls returns to the complete catalog.

Add one or more products to the cart and select **Continue to simulated
checkout**. Enter a made-up classroom name and address, submit the form, and
review the saved confirmation. This is only a local simulation: there is no
real payment, account system, inventory management, or external message.

Do not enter real personal, card, or banking information. This teaching project
does not provide production privacy, security, payment, or availability
guarantees, and it does not send submitted data to an external service.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use a fresh temporary SQLite database and do not modify the local
development database in `instance/`.

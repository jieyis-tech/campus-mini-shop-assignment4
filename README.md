# Campus Mini Shop

Campus Mini Shop is a small Flask application for browsing campus supplies and
building a temporary session cart. The base system runs entirely on a local
computer with SQLite; it does not include accounts, checkout, orders, or
payment.

## Local setup

From the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app campus_shop init-db
.\.venv\Scripts\python.exe -m flask --app campus_shop run --debug
```

Open `http://127.0.0.1:5000/` after the server starts. The `init-db` command is
safe to run again: it creates any missing schema and seed rows without
duplicating or deleting existing products.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use a fresh temporary SQLite database and do not modify the local
development database in `instance/`.

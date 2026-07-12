# Running Campus Mini Shop

These instructions reproduce the application locally from a clean checkout.
The project requires Python 3.10 or newer and does not require a separate
database server, JavaScript toolchain, or external API.

## 1. Clone and enter the repository

```powershell
git clone https://github.com/jieyis-tech/campus-mini-shop-assignment4.git
cd campus-mini-shop-assignment4
```

## 2. Create the virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On macOS or Linux, replace the second command with:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

## 3. Initialize SQLite

```powershell
.\.venv\Scripts\python.exe -m flask --app campus_shop init-db
```

This creates `instance/campus_shop.sqlite` and seeds six campus products. The
command is safe to run repeatedly: it does not duplicate products or delete
saved simulated orders.

## 4. Start the website

```powershell
.\.venv\Scripts\python.exe -m flask --app campus_shop run
```

Open <http://127.0.0.1:5000/>. Stop the server with `Ctrl+C`.

## 5. Reproduce the main flow

1. Browse the six products and open a product detail page.
2. Search for part of a product name and optionally select a category.
3. Add a product to the cart, update its quantity, and verify the subtotal.
4. Select **Continue to simulated checkout**.
5. Enter invented classroom test data, not real personal information.
6. Place the simulated order and verify the saved confirmation page.
7. Open the cart and confirm that it is empty after the successful order.

This is a local classroom simulation. It has no accounts, real payment,
inventory processing, email, or production privacy/security guarantees.

## 6. Run the automated verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The expected result is `73 passed`. Tests create isolated temporary databases
and do not modify the local database in `instance/`.


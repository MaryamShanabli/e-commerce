# FastAPI E-Commerce Backend

A RESTful e-commerce API built with FastAPI and SQLAlchemy (synchronous). It provides JWT-authenticated user accounts, product and category management (admin-only for writes), a per-user shopping cart, and order processing with an atomic, stock-safe checkout.

The API surface: `POST /api/auth/sign-up` and `/api/auth/login`, product/category CRUD, cart endpoints (`GET /api/cart/{user_id}`, `POST /api/cart/add?userID={id}`, `PUT /api/cart/quantity`, `POST /api/cart/checkout`), and order history (`GET /api/order`, `GET /api/order/{id}`).

## Prerequisites

- **Python 3.10+** (developed and tested on 3.12)
- PostgreSQL is optional and available for production-parity testing. SQLite is the default for local development, already set in .env.example, no extra configuration needed.

## Setup

Run these from the repository root.

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure the environment
cp .env.example .env
```

Now edit `.env`. The example defaults to SQLite, so no server setup is needed for local dev. For PostgreSQL instead (production-parity testing), uncomment the Postgres line in `.env.example`:

Replace `JWT_SECRET_KEY` with a long random value, and set `ADMIN_EMAIL` / `ADMIN_PASSWORD` to what you want for the first administrator.

Generate one with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

```bash
# 4. Create the database tables
alembic upgrade head
```

This step runs the migration that creates all seven tables (`users`, `categories`, `products`, `carts`, `cart_items`, `orders`, `order_items`).

## Creating the first admin user

Admin-only routes (creating/updating/deleting products and categories) require a user with admin privileges. There is no public endpoint for this. The admin is created by a script that reads `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `.env`:

```bash
python -m scripts.create_admin
```

The script is idempotent: if the email already exists it promotes that user to admin, otherwise it creates the user. Run it again any time you want to re-assert admin on that account.

## Running the app

```bash
uvicorn app.main:app --reload
```

The API is then available at **http://127.0.0.1:8000**.

## Interactive API exploration

Open **http://127.0.0.1:8000/docs** for the Swagger UI. Every endpoint is listed there with its request/response schemas. You can sign up, log in, and paste the returned access token into the Authorize button (`Authorization: Bearer {token}`) to exercise the authenticated routes.

## Running the test suite

```bash
pytest
```

The full suite is 64 tests covering auth, admin permissions, ownership enforcement, validation, pagination, cart behavior, checkout atomicity/rollback, order history, and the error contract. All 64 should pass.

## Quick manual test

With the app running (see above), confirm it works end to end. Run these in order, in the same terminal session.

```bash
# 1. Sign up a regular user and capture her user id
MARYAM_ID=$(curl -s -X POST http://127.0.0.1:8000/api/auth/sign-up \
  -H "Content-Type: application/json" \
  -d '{"name": "Maryam", "email": "maryam@example.com", "password": "Maryam123"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

# 2. Log in as Maryam and capture her token automatically
MARYAM_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "maryam@example.com", "password": "Maryam123"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# 3. Log in as admin (email/password from your .env) and capture the token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "Admin123"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# 4. Create a category as admin
curl -s -X POST http://127.0.0.1:8000/api/category \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"name": "Snacks"}'

# 5. Create a product as admin
curl -s -X POST http://127.0.0.1:8000/api/product \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"name": "Chips", "price": 2.99, "description": "Pack of 6", "quantity": 200, "category_id": 1}'

# 6. Duplicate category name, expect 409
curl -s -X POST http://127.0.0.1:8000/api/category \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"name": "Snacks"}'

# 7. Non-admin blocked from admin action, expect 403
curl -s -X POST http://127.0.0.1:8000/api/category \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MARYAM_TOKEN" \
  -d '{"name": "Beverages"}'

# 8. Add the product to Maryam's cart
curl -s -X POST "http://127.0.0.1:8000/api/cart/add?userID=$MARYAM_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MARYAM_TOKEN" \
  -d '{"product_id": 1, "quantity": 2}'

# 9. Checkout Maryam's cart
curl -s -X POST http://127.0.0.1:8000/api/cart/checkout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MARYAM_TOKEN" \
  -d "{\"user_id\": $MARYAM_ID, \"payment_method\": \"Credit Card\", \"shipping_address\": \"123 Main St\"}"

# 10. Confirm public read access needs no token at all
curl -s http://127.0.0.1:8000/api/product
```

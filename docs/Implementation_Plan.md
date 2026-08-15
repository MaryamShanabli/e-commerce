# FastAPI E-Commerce Backend — Implementation Plan

**Read this together with:** `Maryam_Task.pdf` (the assessment spec) and `FastAPI_Ecommerce_Architecture_Review.md` (the architecture decisions and their reasoning). This plan is the executable translation of that review — every choice here traces back to a numbered item in the review file. If anything here seems to contradict the review file, the review file's reasoning wins and this plan has a bug; flag it rather than silently picking one.

This plan has been cross-checked field-by-field against the task PDF as a final pass before handoff. Section 0 lists the exact literal strings pulled from the PDF (routes, field names, defaults) so nothing gets paraphrased into a slightly different shape during implementation.

---

## 0. Literal contract extracted from the PDF (do not alter these strings/values)

**Routes (exact paths, exact casing, exact methods):**
```
POST   /api/auth/sign-up
POST   /api/auth/login
GET    /api/product
GET    /api/product/{id}
POST   /api/product
PUT    /api/product/{id}
DELETE /api/product/{id}
GET    /api/category
GET    /api/category/{id}
POST   /api/category
PUT    /api/category            <-- NO path id, see section 8 (Category module)
DELETE /api/category/{id}
GET    /api/cart/{user_id}
POST   /api/cart/add?userID={id}   <-- query param is literally "userID" (capital ID), not "user_id"
PUT    /api/cart/quantity
POST   /api/cart/checkout
GET    /api/order
GET    /api/order/{id}
```

**Defaults / limits (exact numbers):**
- Pagination: `page=1`, `size=10` default; `size` max `100`.
- JWT: algorithm `HS256`; default expiry `1440` minutes (= 24h) — matches the PDF's example `"expires_in": 1440`.
- `token_type` in login response is literally `"bearer"` (lowercase).
- Password minimum length: `6`.
- `price` must be `> 0`. `quantity` must be `>= 0`.

**Error response shape (exact 4 keys, exact names):**
```json
{ "message": "...", "status_code": 404, "error_type": "NotFoundException", "timestamp": "2024-01-15T10:30:00Z" }
```
Plus one additive `ForbiddenException → 403` (see Architecture Review item 24) for ownership/admin authorization failures specifically — not used for missing/invalid tokens, which stay 401.

**Order statuses (exact strings, exact casing):** `Pending`, `Processing`, `Shipped`, `Delivered`, `Cancelled`. New orders start `Pending`.

---

## 1. Tech stack and dependencies

```
fastapi
uvicorn[standard]
sqlalchemy>=2.0
alembic
pydantic>=2
pydantic-settings
python-jose[cryptography]
passlib[bcrypt]
psycopg2-binary        # Postgres driver (prod / CI)
python-dotenv
pytest
httpx                  # used internally by FastAPI's TestClient
```

Do not add `asyncpg`, `pytest-asyncio`, or any async DB driver — this project is synchronous end to end (Architecture Review item 1 and item 29).

---

## 2. Project structure (create exactly this layout)

```
app/
  core/
    __init__.py
    config.py            # Settings (pydantic-settings), reads .env
    db.py                 # engine, SessionLocal, Base, get_db dependency
    security.py           # password hashing, JWT encode/decode, get_current_user, require_admin
    exceptions.py          # custom exception classes + global handlers
    pagination.py          # shared pagination helper
  auth/
    __init__.py
    router.py
    schemas.py
    service.py
    models.py               # User model lives here
  categories/
    __init__.py
    router.py
    schemas.py
    service.py
    models.py               # Category model
  products/
    __init__.py
    router.py
    schemas.py
    service.py
    models.py               # Product model
  cart/
    __init__.py
    router.py
    schemas.py
    service.py
    models.py               # Cart, CartItem models
  orders/
    __init__.py
    router.py
    schemas.py
    service.py
    models.py               # Order, OrderItem models
  main.py                    # creates FastAPI app, includes routers, registers exception handlers, CORS
alembic/
  env.py
  versions/
alembic.ini
scripts/
  create_admin.py            # bootstrap script, see section 4
tests/
  conftest.py                 # DB fixture (SQLite, transaction rollback per test)
  test_auth.py
  test_categories.py
  test_products.py
  test_cart.py
  test_orders.py
  test_errors.py
.env.example
requirements.txt
```

Rationale: feature-first structure, per Architecture Review items 27–28.

---

## 3. Environment variables (`.env.example`)

```
DATABASE_URL=postgresql://user:password@localhost:5432/ecommerce
# For local dev without Postgres running: sqlite:///./dev.db
JWT_SECRET_KEY=change-me-to-a-long-random-value
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:3000
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeThisPassword123!
```

`app/core/config.py` must fail fast (raise at startup) if `JWT_SECRET_KEY` is missing or empty in a non-dev environment — do not fall back to a hardcoded default in code.

---

## 4. Database models — exact columns

For every table below, columns marked **(ADD)** are additions beyond the PDF's literal table list. Each one is justified in the Architecture Review (item numbers noted) — implement them exactly as specified, do not omit them and do not invent additional ones beyond what's listed here.

### `users`
| Column | Type | Notes |
|---|---|---|
| id | Integer, PK, autoincrement | |
| name | String, not null | |
| email | String, unique, not null, indexed | |
| password_hash | String, not null | bcrypt hash, never serialized in any response |
| created_at | DateTime, not null, default=now (UTC) | |
| is_admin | Boolean, not null, default=False | **(ADD — Review item 4)** |

### `categories`
| Column | Type | Notes |
|---|---|---|
| id | Integer, PK, autoincrement | |
| name | String, unique, not null | Validate non-empty at schema level too |

### `products`
| Column | Type | Notes |
|---|---|---|
| id | Integer, PK, autoincrement | |
| name | String, not null | |
| price | Numeric(10,2), not null | **(Review item 18 — Decimal, not float)** |
| description | Text, nullable | |
| quantity | Integer, not null | |
| category_id | Integer, FK → categories.id, not null, indexed | |
| created_at | DateTime, not null, default=now (UTC) | |
| is_active | Boolean, not null, default=True | **(ADD — Review item 20, soft delete)** |

### `carts`
| Column | Type | Notes |
|---|---|---|
| id | Integer, PK, autoincrement | |
| user_id | Integer, FK → users.id, not null, **unique**, indexed | Unique enforces the fixed 1:1 User↔Cart relationship (Review item 12) |
| created_at | DateTime, not null, default=now (UTC) | |

### `cart_items`
| Column | Type | Notes |
|---|---|---|
| id | Integer, PK, autoincrement | |
| cart_id | Integer, FK → carts.id, not null, indexed | |
| product_id | Integer, FK → products.id, not null, indexed | |
| quantity | Integer, not null | |

Add a unique constraint on `(cart_id, product_id)` — this is what makes "increment instead of duplicate" (Review item 10) enforceable at the DB level, not just in application logic.

### `orders`
| Column | Type | Notes |
|---|---|---|
| id | Integer, PK, autoincrement | |
| user_id | Integer, FK → users.id, not null, indexed | |
| order_date | DateTime, not null, default=now (UTC) | |
| status | String, not null, default=`"Pending"` | Validated against the 5 allowed values at the Pydantic/service layer, not a native DB enum (Review item 16) |
| price | Numeric(10,2), not null | Total order price |
| shipping_address | String, not null | |
| payment_method | String, not null | |

### `order_items`
| Column | Type | Notes |
|---|---|---|
| id | Integer, PK, autoincrement | |
| order_id | Integer, FK → orders.id, not null, indexed | |
| product_id | Integer, FK → products.id, not null, indexed | |
| product_name | String, not null | **(ADD — Review item 15, snapshot)** |
| quantity | Integer, not null | |
| unit_price | Numeric(10,2), not null | Snapshot, not a live join (Review item 15) |

`subtotal` is **not** a stored column anywhere — compute it in the response layer as `quantity * unit_price` for both cart items and order items.

---

## 5. Alembic

- Initialize Alembic against the sync engine (`alembic init alembic`, point `sqlalchemy.url` at `DATABASE_URL` from settings in `env.py`, do not hardcode a URL in `alembic.ini`).
- One initial migration creating all 7 tables above, with all FKs, the two unique constraints noted (`carts.user_id`, `cart_items(cart_id, product_id)`), and indexes on every FK column plus `users.email` and `categories.name`.
- Do not use a native Postgres `ENUM` type for `orders.status` — plain `String`/`VARCHAR` (Review item 16), so the same migration works unmodified against SQLite in dev/tests.

---

## 6. Core utilities

### `app/core/security.py`
- `hash_password(plain: str) -> str` / `verify_password(plain: str, hashed: str) -> bool` using `passlib.context.CryptContext(schemes=["bcrypt"])`.
- `create_access_token(user_id: int, email: str, is_admin: bool, expires_minutes: int) -> str` — JWT payload: `sub` (user id, as string), `email`, `is_admin`, `exp`, `iat`. Algorithm from settings (`HS256`).
- `decode_access_token(token: str) -> dict` — raises `UnauthorizedException` (401) on invalid signature, malformed token, or expiry.
- `get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User` dependency — decodes token, loads the user by id, raises 401 if the user no longer exists (e.g., deleted between token issue and use). This is the dependency injected into every protected route.
- `require_admin(current_user: User = Depends(get_current_user)) -> User` — raises `ForbiddenException` (403) if `not current_user.is_admin`. Used on every "(Admin only)" route.
- `require_owner_or_admin(resource_user_id: int, current_user: User = Depends(get_current_user))` — raises `ForbiddenException` (403) if `current_user.id != resource_user_id and not current_user.is_admin`. Used on cart/order routes per Review item 7 and item 8.

### `app/core/exceptions.py`
Define these exception classes (all subclassing a common `AppException(message: str)`):
```
NotFoundException      -> 404, error_type "NotFoundException"
BadRequestException    -> 400, error_type "BadRequestException"
ConflictException      -> 409, error_type "ConflictException"
UnauthorizedException  -> 401, error_type "UnauthorizedException"
ForbiddenException     -> 403, error_type "ForbiddenException"   # additive, Review item 24
ValidationException    -> 400, error_type "ValidationError"
```
Register FastAPI exception handlers for:
1. Each custom exception class above → the exact 4-field JSON shape from Section 0, using `datetime.utcnow().isoformat() + "Z"` for `timestamp`.
2. `RequestValidationError` (FastAPI/Pydantic's default) → **remap to 400**, `error_type: "ValidationError"`, with `message` built by concatenating `"{field}: {error message}"` for each failing field, joined with `"; "`. Do **not** let this fall through to FastAPI's default 422 (Review item 22).
3. A catch-all `Exception` handler → 500, `error_type: "InternalServerError"`, generic message (do not leak stack traces in the response body; log server-side).

### `app/core/pagination.py`
```
def paginate(query, page: int, size: int):
    page = max(page, 1)
    size = min(max(size, 1), 100)          # clamp: PDF max size = 100
    total_count = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    total_pages = ceil(total_count / size) if total_count else 0
    return {
        "items": items,
        "total_count": total_count,
        "page_number": page,
        "page_size": size,
        "total_pages": total_pages,
        "has_previous_page": page > 1,
        "has_next_page": page < total_pages,
    }
```
Used by `GET /api/product` (only paginated list in the PDF).

---

## 7. Module: Auth

### Schemas (`app/auth/schemas.py`)
- `RegisterRequest`: `name: str`, `email: EmailStr`, `password: str` (min_length=6).
- `LoginRequest`: `email: EmailStr`, `password: str`.
- `UserResponse`: `id: int`, `name: str`, `email: str`. (Never include `password_hash` or `is_admin`.)
- `LoginResponse`: `access_token: str`, `token_type: str = "bearer"`, `expires_in: int`, `email: str`.

### Endpoints (`app/auth/router.py`)
- `POST /api/auth/sign-up`
  - Validate email format + password length (Pydantic handles this; failures go through the 400 remap).
  - If email already exists → `ConflictException("Email already registered")` (409).
  - Hash password, create `User(is_admin=False)`, also create an empty `Cart` row for that user immediately (keeps the fixed 1:1 relationship always satisfied from the moment of signup — simplifies cart lookups later, no lazy-create branch needed).
  - Return `UserResponse` (201).
- `POST /api/auth/login`
  - Look up user by email; if not found or password mismatch → `UnauthorizedException("Invalid email or password")` (401). Use the same generic message for both cases (don't reveal whether the email exists).
  - Issue JWT via `create_access_token`.
  - Return `LoginResponse` with `expires_in` = configured minutes (default 1440).

---

## 8. Module: Categories

### Schemas (`app/categories/schemas.py`)
- `CategoryResponse`: `id: int`, `name: str`.
- `CreateCategoryRequest`: `name: str` (min_length=1, stripped — enforces "cannot be empty").
- `UpdateCategoryRequest`: `id: int`, `name: str` (min_length=1). **(ADD — Review item 33: no path id exists on `PUT /api/category`, so id travels in the body.)**

### Endpoints (`app/categories/router.py`)
- `GET /api/category` — public, no auth required, returns `list[CategoryResponse]`.
- `GET /api/category/{id}` — public. Not found → 404.
- `POST /api/category` — `require_admin`. Duplicate name → `ConflictException` (409). Empty name → 400 (schema validation).
- `PUT /api/category` — `require_admin`. Body is `UpdateCategoryRequest`. Look up category by `body.id`; not found → 404. If renaming to a name that already exists on a *different* category → 409.
- `DELETE /api/category/{id}` — `require_admin`. If any `products.category_id == id` exists (regardless of `is_active`) → `ConflictException("Category has associated products")` (409), per Review item 20. Otherwise hard delete.

---

## 9. Module: Products

### Schemas (`app/products/schemas.py`)
- `ProductResponse`: `id: int`, `name: str`, `price: Decimal`, `quantity: int`, `category_id: int`, `category_name: str`, `description: str | None`. **(`description` added — Review item 32.)**
- `CreateProductRequest`: `name: str`, `price: Decimal` (gt=0), `description: str | None = None`, `quantity: int` (ge=0), `category_id: int`.
- `UpdateProductRequest`: same fields as `CreateProductRequest`.

### Endpoints (`app/products/router.py`)
- `GET /api/product?page=&size=` — public. Filter `WHERE is_active = true` (Review item 21). Join `categories` for `category_name`. Return `PaginatedResponse[ProductResponse]` via `paginate()`.
- `GET /api/product/{id}` — public. If not found **or** `is_active = false` → 404 (Review item 21 — inactive product looks identical to deleted from the outside).
- `POST /api/product` — `require_admin`. Validate `category_id` exists → 400/404 if not (`NotFoundException("Category not found")`). Create with `is_active=True`.
- `PUT /api/product/{id}` — `require_admin`. 404 if missing/inactive. Validate `category_id` exists if changed.
- `DELETE /api/product/{id}` — `require_admin`. Soft delete: set `is_active = False`. 404 if already inactive or missing. Return 204.

---

## 10. Module: Cart

### Schemas (`app/cart/schemas.py`)
- `CartItemResponse`: `id: int`, `product_id: int`, `product_name: str`, `product_price: Decimal`, `quantity: int`, `subtotal: Decimal` (computed).
- `CartResponse`: `id: int`, `user_id: int`, `total_price: Decimal` (computed = sum of item subtotals), `items: list[CartItemResponse]`.
- `AddToCartRequest`: `product_id: int`, `quantity: int` (gt=0).
- `UpdateQuantityRequest`: `cart_item_id: int`, `quantity_required: int` (ge=0 — 0 is meaningful, see below).

### Endpoints (`app/cart/router.py`)
All routes: `Depends(get_current_user)` + `require_owner_or_admin(user_id, current_user)` where `user_id` is the path/query value (never trust it alone — Review items 7, 8).

- `GET /api/cart/{user_id}` — ownership check as above. Load (or the cart already exists, since it's created at signup — section 7) the user's cart with items joined to products for `product_name`/`product_price`. Compute `subtotal` per item and `total_price`.
- `POST /api/cart/add?userID={id}` — **query param name is literally `userID`** (Section 0). Ownership check against `id`. Load product; 404 if missing or inactive. If `(cart_id, product_id)` row exists, increment `quantity` (Review item 10); else insert new row. At every point, new total quantity must not exceed `product.quantity` → else `ConflictException("Insufficient stock")` (409).
- `PUT /api/cart/quantity` — body has no user id, so resolve the target `CartItem` by `cart_item_id`, then ownership-check via that item's `cart.user_id` against the current user. 404 if the cart item doesn't exist. If `quantity_required == 0` → delete the row (Review item 11). Else validate against `product.quantity` → 409 if exceeded, otherwise update.
- `POST /api/cart/checkout` — body is `CheckoutRequest` (defined in Orders module, section 11, since it produces an order). Implemented here or delegated to `orders/service.py` — either is fine structurally as long as the transaction described in section 11 is atomic.

---

## 11. Module: Orders

### Schemas (`app/orders/schemas.py`)
- `OrderItemResponse`: `product_id: int`, `product_name: str`, `quantity: int`, `unit_price: Decimal`, `subtotal: Decimal` (computed).
- `OrderResponse`: `id: int`, `user_id: int`, `order_date: datetime`, `status: str`, `price: Decimal`, `items: list[OrderItemResponse]`, `shipping_address: str`, `payment_method: str`. **(`shipping_address`, `payment_method` added — Review item 31.)**
- `CheckoutRequest`: `user_id: int`, `payment_method: str`, `shipping_address: str`. `user_id` is retained in the schema for fidelity to the PDF, but its value is **never trusted** — see logic below (Review item 17).

### Checkout logic (`app/orders/service.py`, called from `POST /api/cart/checkout`)
Single DB transaction, in this exact order (Review item 14):
1. Resolve the authoritative user from the JWT (`get_current_user`), **not** from `CheckoutRequest.user_id`. If `CheckoutRequest.user_id != current_user.id` and the caller is not admin → `ForbiddenException` (403).
2. Load the user's cart with items. If no items → `BadRequestException("Cart is empty")` (400). Do this check **before** starting any write.
3. For each cart item, run the atomic conditional stock update (Review item 19):
   `UPDATE products SET quantity = quantity - :qty WHERE id = :id AND quantity >= :qty AND is_active = true`
   — check rowcount == 1; if 0, raise `ConflictException("Insufficient stock for {product_name}")` (409) and let the transaction roll back everything done in this checkout so far (including any earlier successful decrements in this same loop — the whole operation is one transaction, nothing partial commits).
4. Compute `total_price` = sum of `quantity * unit_price` across items, using each product's **current** price at the moment of checkout (this is the price being charged now, not a stale cached one — separate from item 15's concern, which is about what's *stored on the order afterward*, not what's charged).
5. Create the `Order` row: `status="Pending"`, `price=total_price`, `shipping_address`, `payment_method` from the request.
6. Create `OrderItem` rows, one per cart item, snapshotting `product_name` and `unit_price` at this moment (Review item 15).
7. Delete all `cart_items` rows for this cart (Review item 13 — clear, don't delete the cart itself).
8. Commit. Return the created `OrderResponse`.
Any exception anywhere in steps 2–7 → rollback the entire transaction, re-raise the specific exception so the global handler returns the right status code.

### Endpoints (`app/orders/router.py`)
- `GET /api/order` — `Depends(get_current_user)`. Returns only the current user's orders (`WHERE user_id = current_user.id`), most recent first. No pagination specified for this endpoint in the PDF — return a plain list.
- `GET /api/order/{id}` — `Depends(get_current_user)`. Load order; 404 if missing. Ownership check: `order.user_id == current_user.id` or admin → else `ForbiddenException` (403).

---

## 12. `app/main.py` wiring

1. Create the `FastAPI()` app.
2. Register CORS middleware: `allow_origins` = `settings.CORS_ORIGINS.split(",")`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]` (Review item 25).
3. Register all exception handlers from `core/exceptions.py` (including the `RequestValidationError` → 400 remap — this must be registered or the 422 default leaks through, breaking Review item 22).
4. Include all 5 routers with their `/api/...` prefixes.
5. No need for a root `/` route beyond FastAPI's default docs at `/docs`.

---

## 13. Admin bootstrap script (`scripts/create_admin.py`)

- Reads `ADMIN_EMAIL` / `ADMIN_PASSWORD` from settings/env.
- If a user with that email already exists: set `is_admin = True` on it (idempotent — safe to re-run).
- If not: create a new user with that email/password and `is_admin = True`.
- Never exposed via any HTTP route (Review item 5). Run manually: `python -m scripts.create_admin`.

---

## 14. Tests (`tests/`)

`conftest.py`: SQLite file or in-memory DB fixture, fresh schema per test session (`Base.metadata.create_all`), each test wrapped in a transaction that's rolled back afterward so tests don't leak state into each other. A `client` fixture wrapping FastAPI's `TestClient`. Helper fixtures: `create_user(is_admin=False)`, `auth_headers(user)` returning `{"Authorization": f"Bearer {token}"}`.

Implement at minimum, one test function per line below (Review item 30, plus 3 new cases for items 31–33):

**Auth**
- Sign-up succeeds, returns `UserResponse` shape (no password field).
- Sign-up with duplicate email → 409.
- Login with correct credentials → 200 + token; wrong password → 401; nonexistent email → 401 (same message either way).
- Protected route with no `Authorization` header → 401.
- Protected route with an expired/garbage token → 401.

**Admin permission**
- Non-admin `POST /api/product` → 403. Admin `POST /api/product` → 201.
- Non-admin `DELETE /api/category/{id}` → 403.

**Ownership**
- User A `GET /api/cart/{user_B_id}` → 403.
- User A `GET /api/order/{order_belonging_to_B}` → 403.
- Admin can access any user's cart/order.

**Validation**
- Sign-up missing `email` field → 400 (not 422!) with the 4-field error shape.
- `price = 0` on product create → 400.
- `quantity = -1` on product create → 400.
- Empty-string category name → 400.
- Duplicate category name → 409.

**Pagination**
- `GET /api/product` with no query params → `page_number=1, page_size=10`.
- `size=500` requested → clamped to 100.
- Verify `has_previous_page`/`has_next_page`/`total_pages` on first, middle, and last page of a seeded 25-product set.

**Cart behavior**
- Adding the same product twice increments quantity, doesn't duplicate the row.
- Adding more than available stock → 409.
- `PUT /api/cart/quantity` with `quantity_required=0` removes the item.

**Inventory safety / checkout**
- Two sequential checkouts racing for the last unit of stock: simulate by decrementing stock via two service calls sharing the same starting state; exactly one should succeed, the other 409, and final stock is never negative.
- Checkout with an empty cart → 400.
- Checkout where one of two items is out of stock → whole transaction rolls back: assert no `Order` row was created and the *other* item's stock was **not** decremented either.
- Successful checkout: stock decremented correctly, cart is emptied (not deleted — verify the `carts` row for that user still exists afterward), `OrderItem.product_name`/`unit_price` match what was in the cart at the time, order `status == "Pending"`.

**Order history**
- User only sees their own orders from `GET /api/order`.
- `GET /api/order/{id}` for another user's order → 403.

**Error contract**
- For a 404, 400, 409, 401, and 403 case each: assert the JSON body has exactly the 4 keys `message, status_code, error_type, timestamp` with correct types (403 case naturally has the same 4 keys, `error_type: "ForbiddenException"`).

**New: response-shape regression tests (Review items 31–33)**
- `GET /api/order/{id}` response includes `shipping_address` and `payment_method` matching what was submitted at checkout.
- `GET /api/product/{id}` response includes `description` matching what was set on create.
- `PUT /api/category` with a body `{id, name}` successfully renames the category (path has no id — confirm the route as literally specified still works).

---

## 15. Build order (do the phases in this sequence — don't skip ahead)

1. Scaffold project structure + dependencies + `.env.example` (sections 1–3).
2. `core/config.py`, `core/db.py` — confirm the app boots and can connect to SQLite locally.
3. `core/security.py`, `core/exceptions.py`, `core/pagination.py`.
4. All models (section 4) + Alembic init + initial migration (section 5). Run the migration against local SQLite, confirm tables exist.
5. Auth module end to end (sign-up, login) — confirm you can obtain a token via `curl`/`TestClient` before building anything that depends on auth.
6. Categories module.
7. Products module (depends on categories existing).
8. Cart module (depends on auth + products).
9. Orders module + checkout transaction (depends on cart + products).
10. Wire `main.py` (routers, CORS, exception handlers) — do this only once all modules exist, then smoke-test every route manually.
11. Admin bootstrap script — run it once, confirm the created user can hit an admin-only route.
12. Write and run the full test suite (section 14). All tests must pass before considering this done.
13. Final self-check: walk through Section 0's literal route list one by one and confirm each exists with the exact path/method/param names written there.

---

## 16. Final acceptance checklist (verify before declaring the task complete)

- [ ] All 18 routes in Section 0 exist with exact paths, methods, and parameter names (`userID` not `user_id` on the add-to-cart query param; no path id on `PUT /api/category`).
- [ ] All 7 tables exist with their required columns plus exactly the additions listed in Section 4 (`is_admin`, `is_active`, `product_name` on order_items) — no other undocumented columns.
- [ ] Passwords are bcrypt-hashed and never appear in any response.
- [ ] JWT uses HS256, default 1440-minute expiry, `Bearer` header auth.
- [ ] Pagination defaults/max match Section 0 exactly, and all 6 `PaginatedResponse` fields are present and correctly computed.
- [ ] Every error response has exactly the 4 documented fields (`message, status_code, error_type, timestamp`); validation errors return 400, not FastAPI's default 422.
- [ ] `ProductResponse` includes `description`; `OrderResponse` includes `shipping_address` and `payment_method` (Review items 31–32).
- [ ] Checkout is atomic: empty-cart rejection, stock-safe under concurrency, full rollback on partial failure, cart cleared (not deleted) on success, order items snapshot name/price.
- [ ] Ownership enforcement is present on every cart/order route, admin enforcement on every "(Admin only)" route.
- [ ] CORS configured with credentials + explicit origin list.
- [ ] Full test suite from Section 14 passes.

---

# Prompt for the implementing agent

Copy everything between the lines below and paste it as the first message to the agent, along with the three attached files (`Maryam_Task.pdf`, `FastAPI_Ecommerce_Architecture_Review.md`, `Implementation_Plan.md`).

---

You are implementing a FastAPI e-commerce backend. I'm giving you three documents — read all three fully before writing any code:

1. **`Maryam_Task.pdf`** — the original assessment spec. This is the ultimate source of truth for *what* is required.
2. **`FastAPI_Ecommerce_Architecture_Review.md`** — an architecture review that was done against that spec before any code was written. It documents every non-obvious design decision (sync vs async, database choice, auth model, transaction strategy, deletion policy, and several places where the PDF is internally ambiguous or inconsistent with itself), along with the reasoning for each and what alternatives were rejected and why.
3. **`Implementation_Plan.md`** — the concrete build plan that translates that architecture review into an exact file structure, database schema, endpoint-by-endpoint logic, and test list. This is your primary implementation reference.

**Your instructions:**

- Follow `Implementation_Plan.md` exactly — exact file structure, exact model columns, exact endpoint behavior, in the build order given in its Section 15. Do not deviate from it without a clear technical reason, and if you do deviate, say so explicitly and explain why, the same way the architecture review does.
- Section 0 of the plan lists literal strings pulled directly from the PDF (exact routes, exact defaults, exact field/parameter names, including a couple of easy-to-miss details like the `userID` query parameter casing and `PUT /api/category` having no path id). Treat these as non-negotiable — don't "clean them up" to look more conventional.
- Several places in the plan add a column, field, or piece of logic beyond what the PDF's tables/DTOs literally list (e.g., `is_admin`, `is_active`, `product_name` on `order_items`, `description` on `ProductResponse`, `shipping_address`/`payment_method` on `OrderResponse`). Each of these is explained in the architecture review and cross-referenced by item number in the plan — implement them as specified, they are not optional extras.
- Implement the full test suite described in Section 14 of the plan, and don't consider the task done until every test passes and the Section 16 acceptance checklist is fully checked off.
- If you find a place where the PDF, the architecture review, and the implementation plan genuinely disagree with each other (rather than just extending or clarifying it), stop and flag it — don't silently resolve it by picking one.
- Do not add scope beyond what's in these three documents (no extra endpoints, no extra tables, no framework substitutions) unless something is genuinely required to make a documented requirement work, the same restraint the architecture review used throughout.

Start by scaffolding the project structure from Section 2 of the implementation plan, then proceed through the build order in Section 15.

---

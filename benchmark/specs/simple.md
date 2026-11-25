# Warehouse stock API

Build a REST API that tracks stock of items in one warehouse. Python, FastAPI, SQLite.

## Runtime contract (the acceptance tests depend on it)

- The ASGI app is `app.main:app`, in a package `app/` at the project root.
- The server is started from the project root with `python -m uvicorn app.main:app --host 127.0.0.1 --port <PORT> --workers 2`. Two worker processes share one database, so correctness must not depend on in-process state.
- The SQLite file path comes from the environment variable `DB_PATH`. If the file or its tables do not exist, the app creates them at startup. Data must survive a restart.
- Dependencies are listed in `requirements.txt` at the root. Python 3.12 with `fastapi`, `uvicorn`, `pydantic` and `httpx` is already installed; anything else you need must be in `requirements.txt`.
- All request and response bodies are JSON. Validation failures return HTTP 422.

## Resources

### Item

Fields: `id` (integer, assigned by the server), `sku` (string, 1 to 32 characters, unique, case-sensitive, immutable), `name` (string, 1 to 100 characters), `min_stock` (integer, 0 or more, default 0), `quantity` (integer, current balance, starts at 0, never negative).

### Movement

Fields: `id`, `item_id`, `type` (`"in"` or `"out"`), `quantity` (integer greater than 0), `note` (optional string up to 200 characters, default `null`), `balance_after` (the item's quantity after this movement), `created_at` (ISO 8601 UTC string).

## Endpoints

1. `GET /health` returns 200 `{"status": "ok"}`.
2. `POST /items` with `sku`, `name` and optional `min_stock`. Returns 201 with the item. A repeated `sku` returns 409. A client cannot set `quantity` or `id`: those fields in the body are ignored.
3. `GET /items` returns 200 with a list of all items ordered by `id`. The optional query `q` keeps only items whose `sku` or `name` contains `q`, ignoring case.
4. `GET /items/{id}` returns 200 with the item, or 404.
5. `PUT /items/{id}` with `name` and `min_stock` (both required). Returns 200 with the updated item. A `sku` in the body is ignored. 404 if the item does not exist.
6. `DELETE /items/{id}` returns 204 and removes the item with its movements. It returns 409 if the item's quantity is greater than 0. It returns 404 if the item does not exist.
7. `POST /items/{id}/movements` with `type`, `quantity` and optional `note`. Returns 201 with the movement. An `"in"` adds to the balance and an `"out"` subtracts. An `"out"` larger than the balance returns 409 and changes nothing, including under concurrent requests: with a balance of N, any number of simultaneous outs of 1 must succeed exactly N times. 404 if the item does not exist.
8. `GET /items/{id}/movements` returns 200 with the item's movements, oldest first. 404 if the item does not exist.
9. `GET /reports/low-stock` returns 200 with the items whose `quantity` is strictly below `min_stock`. Each entry is the item plus `shortfall` (`min_stock - quantity`). Order: largest `shortfall` first, ties by `sku` ascending. An item with `min_stock` 0 never appears.

Error responses are JSON with a `detail` field.

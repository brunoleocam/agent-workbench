# Event registration API (version 3)

Build a REST API for registering people to events with limited seats, a waiting list, and check-in at the door. Python, FastAPI, SQLite.

## Changes in version 2

Version 2 of this API is already implemented in the current directory. Version 3 keeps everything below that is not listed here:

- New: `GET /admin/outbox` lists notifications that the system must record for every registration change (endpoint 13).
- Changed: an administrator may now cancel a `checked_in` registration (see Behaviour and endpoint 8). This replaces the earlier rule that a `checked_in` registration cannot be cancelled.

## Runtime contract (the acceptance tests depend on it)

- The ASGI app is `app.main:app`, in a package `app/` at the project root.
- The server is started from the project root with `python -m uvicorn app.main:app --host 127.0.0.1 --port <PORT> --workers 2`. Two worker processes share one database, so correctness, and above all the seat limit, must not depend on in-process state or locks.
- The SQLite file path comes from the environment variable `DB_PATH`. If the file or its tables do not exist, the app creates them at startup. Data must survive a restart.
- The administrator credentials come from the environment variables `ADMIN_USER` and `ADMIN_PASSWORD`. There is no default: if either is missing, `POST /admin/login` always returns 401.
- Dependencies are listed in `requirements.txt` at the root. Python 3.12 with `fastapi`, `uvicorn`, `pydantic` and `httpx` is already installed; anything else you need must be in `requirements.txt`.
- All request and response bodies are JSON. Validation failures return HTTP 422. Error responses are JSON with a `detail` field.

## Authentication

`POST /admin/login` with `username` and `password` returns 200 `{"token": "<opaque string>"}` for the configured credentials, otherwise 401. Endpoints marked **admin** need the header `Authorization: Bearer <token>`. A missing, malformed, or unknown token returns 401. A token is valid for 1 hour and must be accepted by both workers and after a restart (store tokens in the database or sign them). Passwords must be compared in constant time. Public endpoints need no token.

## Resources

### Event

`id`, `name` (1 to 100 characters), `capacity` (integer, 1 or more), `confirmed_count`, `waitlist_count`, `checked_in_count`.

### Registration

`id`, `event_id`, `name` (1 to 100 characters), `email` (a syntactically valid address, stored and compared in lowercase), `status`, `position`, `checkin_code`.

`status` is one of `confirmed`, `waitlisted`, `cancelled`, `checked_in`. `position` is the 1-based place in the waiting list while `waitlisted`, otherwise `null`. `checkin_code` is a string of exactly 8 characters from `A-Z` and `0-9`, unique across all registrations, generated with a cryptographically secure source. It is present while the registration is `confirmed` or `checked_in` and `null` otherwise.

## Behaviour

- A registration takes a seat while its status is `confirmed` or `checked_in`. Number of seats taken never exceeds `capacity`, even with many simultaneous registrations or cancellations.
- A new registration for an event with a free seat is `confirmed`. When the event is full it is `waitlisted`, at the end of the waiting list.
- One person (same email, compared case-insensitively) can hold only one active registration (`confirmed`, `waitlisted`, or `checked_in`) per event. A second attempt returns 409. After cancelling, the same person may register again as a new registration.
- Cancelling a `confirmed` registration frees its seat, and if the waiting list is not empty the person at the front is promoted to `confirmed` at once (and receives a `checkin_code`), in the same operation. Cancelling a `waitlisted` registration moves everyone behind it up by one. Positions are always contiguous from 1.
- A cancelled registration's code stops working.
- A `cancelled` registration cannot be cancelled again (409). A `checked_in` registration can be cancelled only by an administrator: `DELETE /registrations/{id}` with a valid admin token returns 200, the registration becomes `cancelled`, its seat is freed, its code stops working, and the front of the waiting list is promoted as for any other cancellation. Without an `Authorization` header the same request returns 409. With an `Authorization` header that is malformed, unknown, or expired, `DELETE /registrations/{id}` returns 401 for every registration.
- Check-in uses the code, per event: a code that does not exist, belongs to another event, or belongs to a cancelled registration returns 404. A code already used returns 409.

## Endpoints

1. `GET /health` returns 200 `{"status": "ok"}`.
2. `POST /admin/login` as above.
3. `POST /events` (**admin**) with `name` and `capacity`. Returns 201 with the event. Counts start at 0.
4. `GET /events` returns 200 with all events ordered by `id`. Public.
5. `GET /events/{id}` returns 200 with the event, or 404. Public.
6. `POST /events/{id}/registrations` with `name` and `email`. Public. Returns 201 with the registration. 404 if the event does not exist, 409 for a duplicate active registration.
7. `GET /registrations/{id}` returns 200 with the registration, or 404. Public.
8. `DELETE /registrations/{id}` returns 200 with the registration after cancelling (status `cancelled`), or 404 or 409 as above. Public, except for the rules for `checked_in` registrations and for an invalid `Authorization` header (see Behaviour).
9. `GET /events/{id}/registrations` (**admin**) returns 200 with all registrations of the event, ordered by `id`, optionally filtered by the query `status`. 404 if the event does not exist.
10. `POST /events/{id}/checkin` (**admin**) with `code`. Returns 200 with the registration, now `checked_in`. Errors as above.

When both authentication and another error apply, authentication is checked first (401 before 404 or 422).
11. `PATCH /events/{id}` (**admin**) with a JSON body that has `name` (1 to 100 characters), `capacity` (integer, 1 or more), or both. At least one of the two is required, otherwise 422. Returns 200 with the event, or 404 if it does not exist. Rules: if the new capacity is lower than the number of seats taken (`confirmed` plus `checked_in`), the request fails with 409 and nothing changes, not even the name. If the new capacity is higher, the people at the front of the waiting list are promoted to `confirmed` at once, in waiting-list order, until the free seats are used or the list is empty; they receive their `checkin_code`, and positions stay contiguous from 1. The change and the promotions happen in one operation, and the seat limit holds under concurrent registrations, cancellations, and changes.
12. `GET /events/{id}/waitlist` (**admin**) returns 200 with the `waitlisted` registrations of the event ordered by `position`, or 404 if the event does not exist.
13. `GET /admin/outbox` (**admin**) returns 200 with the notifications ordered by `id`, each `{"id": int, "event_id": int, "registration_id": int, "kind": "confirmed" | "waitlisted" | "promoted" | "cancelled"}`. The optional queries `event_id` and `registration_id` (integers, otherwise 422) filter the list. Rules: exactly one notification is recorded for every status transition, in the same operation as the change, so it is never missing and never duplicated, including under concurrent requests. A new registration records `confirmed` or `waitlisted`. A promotion from the waiting list records `promoted`, whichever operation caused it (a cancellation or a capacity increase). A cancellation records `cancelled`; when it also promotes someone, the `cancelled` notification comes first. A rejected request (409, 404, 422) records nothing. Check-in records nothing.

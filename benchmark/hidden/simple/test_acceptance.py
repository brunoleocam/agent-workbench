"""Hidden black-box acceptance tests: warehouse stock API. Never copied into a run workspace."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Server  # noqa: E402


@pytest.fixture(scope="module")
def srv():
    s = Server(os.environ["APP_DIR"])
    s.wait_ready()
    yield s
    s.stop()


@pytest.fixture()
def c(srv):
    with httpx.Client(base_url=srv.url, timeout=15) as client:
        yield client


_n = [0]


def sku():
    _n[0] += 1
    return f"S{os.getpid()}-{_n[0]}"


def mk(c, **kw):
    body = {"sku": sku(), "name": "Widget", **kw}
    r = c.post("/items", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def move(c, item_id, type_, qty, **kw):
    return c.post(f"/items/{item_id}/movements", json={"type": type_, "quantity": qty, **kw})


# ---- items: create / read ----------------------------------------------------

def test_health(c):
    r = c.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_create_item_defaults(c):
    it = mk(c)
    assert it["quantity"] == 0 and it["min_stock"] == 0 and isinstance(it["id"], int)
    assert set(["id", "sku", "name", "min_stock", "quantity"]) <= set(it)


def test_create_ignores_client_quantity_and_id(c):
    r = c.post("/items", json={"sku": sku(), "name": "X", "quantity": 99, "id": 5000})
    assert r.status_code == 201
    assert r.json()["quantity"] == 0 and r.json()["id"] != 5000


def test_duplicate_sku_409(c):
    it = mk(c)
    r = c.post("/items", json={"sku": it["sku"], "name": "Other"})
    assert r.status_code == 409 and "detail" in r.json()


def test_sku_is_case_sensitive(c):
    base = sku()
    assert c.post("/items", json={"sku": base.lower(), "name": "a"}).status_code == 201
    assert c.post("/items", json={"sku": base.upper(), "name": "b"}).status_code == 201


@pytest.mark.parametrize("body", [
    {"name": "no sku"},
    {"sku": "", "name": "empty sku"},
    {"sku": "x" * 33, "name": "long sku"},
    {"sku": "ok1", "name": ""},
    {"sku": "ok2", "name": "n" * 101},
    {"sku": "ok3", "name": "n", "min_stock": -1},
    {"sku": "ok4", "name": "n", "min_stock": "abc"},
    {"sku": "ok5", "name": "n", "min_stock": 1.5},
])
def test_create_validation_422(c, body):
    assert c.post("/items", json=body).status_code == 422


def test_sku_boundaries_ok(c):
    s32 = (sku() + "z" * 32)[:32]
    assert c.post("/items", json={"sku": s32, "name": "n" * 100}).status_code == 201


def test_get_item_and_404(c):
    it = mk(c)
    assert c.get(f"/items/{it['id']}").json() == it
    r = c.get("/items/99999999")
    assert r.status_code == 404 and "detail" in r.json()


def test_list_ordered_and_filter(c):
    a = mk(c, name="Alpha Bolt")
    b = mk(c, name="beta NUT")
    ids = [i["id"] for i in c.get("/items").json()]
    assert ids == sorted(ids) and a["id"] in ids and b["id"] in ids
    got = c.get("/items", params={"q": "ALPHA bo"}).json()
    assert a["id"] in [i["id"] for i in got] and b["id"] not in [i["id"] for i in got]
    by_sku = c.get("/items", params={"q": b["sku"].lower()}).json()
    assert [i["id"] for i in by_sku] == [b["id"]]


def test_update_item(c):
    it = mk(c)
    r = c.put(f"/items/{it['id']}", json={"name": "Renamed", "min_stock": 7, "sku": "HACK"})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Renamed" and body["min_stock"] == 7 and body["sku"] == it["sku"]
    assert c.get(f"/items/{it['id']}").json()["name"] == "Renamed"


def test_update_validation_and_404(c):
    it = mk(c)
    assert c.put(f"/items/{it['id']}", json={"name": "x"}).status_code == 422
    assert c.put(f"/items/{it['id']}", json={"name": "x", "min_stock": -3}).status_code == 422
    assert c.put("/items/99999999", json={"name": "x", "min_stock": 1}).status_code == 404


def test_update_keeps_quantity(c):
    it = mk(c)
    move(c, it["id"], "in", 4)
    c.put(f"/items/{it['id']}", json={"name": "n", "min_stock": 1, "quantity": 100})
    assert c.get(f"/items/{it['id']}").json()["quantity"] == 4


# ---- movements -----------------------------------------------------------------

def test_in_out_balance(c):
    it = mk(c)
    r = move(c, it["id"], "in", 10, note="first")
    assert r.status_code == 201
    m = r.json()
    assert m["balance_after"] == 10 and m["type"] == "in" and m["quantity"] == 10
    assert m["note"] == "first" and m["item_id"] == it["id"] and m["created_at"]
    r = move(c, it["id"], "out", 4)
    assert r.status_code == 201 and r.json()["balance_after"] == 6 and r.json()["note"] is None
    assert c.get(f"/items/{it['id']}").json()["quantity"] == 6


def test_out_exact_balance_to_zero(c):
    it = mk(c)
    move(c, it["id"], "in", 3)
    assert move(c, it["id"], "out", 3).status_code == 201
    assert c.get(f"/items/{it['id']}").json()["quantity"] == 0


def test_out_more_than_balance_409_and_unchanged(c):
    it = mk(c)
    move(c, it["id"], "in", 5)
    r = move(c, it["id"], "out", 6)
    assert r.status_code == 409 and "detail" in r.json()
    assert c.get(f"/items/{it['id']}").json()["quantity"] == 5
    assert len(c.get(f"/items/{it['id']}/movements").json()) == 1


def test_out_on_empty_item_409(c):
    it = mk(c)
    assert move(c, it["id"], "out", 1).status_code == 409


@pytest.mark.parametrize("body", [
    {"type": "in", "quantity": 0},
    {"type": "in", "quantity": -2},
    {"type": "out", "quantity": 1.5},
    {"type": "out", "quantity": "3x"},
    {"type": "move", "quantity": 1},
    {"type": "IN", "quantity": 1},
    {"quantity": 1},
    {"type": "in"},
    {"type": "in", "quantity": 1, "note": "n" * 201},
])
def test_movement_validation_422(c, body):
    it = mk(c)
    assert c.post(f"/items/{it['id']}/movements", json=body).status_code == 422
    assert c.get(f"/items/{it['id']}").json()["quantity"] == 0


def test_movement_note_boundary(c):
    it = mk(c)
    assert move(c, it["id"], "in", 1, note="n" * 200).status_code == 201


def test_movement_on_missing_item_404(c):
    assert move(c, 99999999, "in", 1).status_code == 404
    assert c.get("/items/99999999/movements").status_code == 404


def test_movement_history_order(c):
    it = mk(c)
    move(c, it["id"], "in", 5)
    move(c, it["id"], "out", 2)
    move(c, it["id"], "in", 1)
    hist = c.get(f"/items/{it['id']}/movements").json()
    assert [(m["type"], m["quantity"], m["balance_after"]) for m in hist] == [
        ("in", 5, 5), ("out", 2, 3), ("in", 1, 4)]


def test_concurrent_outs_never_go_negative(srv):
    with httpx.Client(base_url=srv.url, timeout=30) as c0:
        it = mk(c0)
        move(c0, it["id"], "in", 7)

        def go(_):
            with httpx.Client(base_url=srv.url, timeout=30) as cc:
                return move(cc, it["id"], "out", 1).status_code

        with ThreadPoolExecutor(30) as ex:
            codes = list(ex.map(go, range(30)))
        assert codes.count(201) == 7 and codes.count(409) == 23, codes
        assert c0.get(f"/items/{it['id']}").json()["quantity"] == 0


def test_concurrent_ins_are_all_counted(srv):
    with httpx.Client(base_url=srv.url, timeout=30) as c0:
        it = mk(c0)

        def go(_):
            with httpx.Client(base_url=srv.url, timeout=30) as cc:
                return move(cc, it["id"], "in", 2).status_code

        with ThreadPoolExecutor(20) as ex:
            codes = list(ex.map(go, range(20)))
        assert codes.count(201) == 20, codes
        assert c0.get(f"/items/{it['id']}").json()["quantity"] == 40
        hist = c0.get(f"/items/{it['id']}/movements").json()
        assert sorted(m["balance_after"] for m in hist) == list(range(2, 42, 2))


# ---- delete ----------------------------------------------------------------------

def test_delete_with_stock_409_then_ok_after_zero(c):
    it = mk(c)
    move(c, it["id"], "in", 2)
    assert c.delete(f"/items/{it['id']}").status_code == 409
    assert c.get(f"/items/{it['id']}").status_code == 200
    move(c, it["id"], "out", 2)
    assert c.delete(f"/items/{it['id']}").status_code == 204
    assert c.get(f"/items/{it['id']}").status_code == 404
    assert c.get(f"/items/{it['id']}/movements").status_code == 404


def test_delete_404_and_sku_reusable(c):
    assert c.delete("/items/99999999").status_code == 404
    it = mk(c)
    assert c.delete(f"/items/{it['id']}").status_code == 204
    assert c.post("/items", json={"sku": it["sku"], "name": "again"}).status_code == 201


# ---- low-stock report -----------------------------------------------------------------

def test_low_stock_report(c):
    a = mk(c, min_stock=10)          # qty 4 -> shortfall 6
    b = mk(c, min_stock=5)           # qty 5 -> not low (equal)
    d = mk(c, min_stock=0)           # never
    e = mk(c, min_stock=20)          # qty 0 -> shortfall 20
    f = mk(c, min_stock=3)           # qty 0 -> shortfall 3
    move(c, a["id"], "in", 4)
    move(c, b["id"], "in", 5)
    rep = c.get("/reports/low-stock")
    assert rep.status_code == 200
    rows = {r["id"]: r for r in rep.json()}
    assert a["id"] in rows and rows[a["id"]]["shortfall"] == 6
    assert e["id"] in rows and rows[e["id"]]["shortfall"] == 20
    assert f["id"] in rows and rows[f["id"]]["shortfall"] == 3
    assert b["id"] not in rows and d["id"] not in rows
    sf = [r["shortfall"] for r in rep.json()]
    assert sf == sorted(sf, reverse=True)
    assert rows[a["id"]]["quantity"] == 4 and rows[a["id"]]["sku"] == a["sku"]


def test_low_stock_tie_order_by_sku(c):
    x = c.post("/items", json={"sku": "TIE-" + sku() + "-B", "name": "b", "min_stock": 1000}).json()
    y = c.post("/items", json={"sku": "TIE-" + sku() + "-A", "name": "a", "min_stock": 1000}).json()
    rows = [r for r in c.get("/reports/low-stock").json() if r["shortfall"] == 1000]
    ours = [r for r in rows if r["id"] in (x["id"], y["id"])]
    order = [r["sku"] for r in rows]
    assert ours and order == sorted(order)


def test_low_stock_leaves_when_restocked(c):
    it = mk(c, min_stock=5)
    assert it["id"] in [r["id"] for r in c.get("/reports/low-stock").json()]
    move(c, it["id"], "in", 5)
    assert it["id"] not in [r["id"] for r in c.get("/reports/low-stock").json()]
    c.put(f"/items/{it['id']}", json={"name": "n", "min_stock": 6})
    assert it["id"] in [r["id"] for r in c.get("/reports/low-stock").json()]


# ---- persistence -------------------------------------------------------------------------

def test_data_survives_restart(tmp_path):
    db = str(tmp_path / "persist.db")
    s = Server(os.environ["APP_DIR"], db_path=db)
    try:
        s.wait_ready()
        with httpx.Client(base_url=s.url, timeout=15) as c:
            it = mk(c)
            move(c, it["id"], "in", 9)
    finally:
        s.stop()
    s2 = Server(os.environ["APP_DIR"], db_path=db)
    try:
        s2.wait_ready()
        r = httpx.get(f"{s2.url}/items/{it['id']}", timeout=10)
        assert r.status_code == 200 and r.json()["quantity"] == 9
    finally:
        s2.stop()

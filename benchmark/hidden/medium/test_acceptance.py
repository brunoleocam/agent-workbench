"""Hidden black-box acceptance tests: event registration API. Never copied into a run workspace."""
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Server  # noqa: E402

USER, PASSWORD = "root-admin", "s3cret-Pass!"
ENV = {"ADMIN_USER": USER, "ADMIN_PASSWORD": PASSWORD}


@pytest.fixture(scope="module")
def srv():
    s = Server(os.environ["APP_DIR"], extra_env=ENV)
    s.wait_ready()
    yield s
    s.stop()


@pytest.fixture()
def c(srv):
    with httpx.Client(base_url=srv.url, timeout=20) as client:
        yield client


@pytest.fixture(scope="module")
def token(srv):
    r = httpx.post(srv.url + "/admin/login", json={"username": USER, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture()
def adm(token):
    return {"Authorization": f"Bearer {token}"}


_n = [0]


def email():
    _n[0] += 1
    return f"p{os.getpid()}x{_n[0]}@example.com"


def event(c, adm, capacity=2, name="Meetup"):
    r = c.post("/events", json={"name": name, "capacity": capacity}, headers=adm)
    assert r.status_code == 201, r.text
    return r.json()


def reg(c, ev_id, mail=None, name="Ana"):
    return c.post(f"/events/{ev_id}/registrations", json={"name": name, "email": mail or email()})


def must_reg(c, ev_id, mail=None):
    r = reg(c, ev_id, mail)
    assert r.status_code == 201, r.text
    return r.json()


CODE_RE = re.compile(r"^[A-Z0-9]{8}$")


# ---- auth -----------------------------------------------------------------------

def test_health(c):
    assert c.get("/health").json() == {"status": "ok"}


def test_login_ok_and_bad(c):
    assert c.post("/admin/login", json={"username": USER, "password": PASSWORD}).status_code == 200
    assert c.post("/admin/login", json={"username": USER, "password": "nope"}).status_code == 401
    assert c.post("/admin/login", json={"username": "nobody", "password": PASSWORD}).status_code == 401
    assert c.post("/admin/login", json={"username": USER}).status_code == 422


def test_admin_endpoints_need_token(c, adm):
    ev = event(c, adm)
    for method, url, body in [
        ("post", "/events", {"name": "x", "capacity": 1}),
        ("get", f"/events/{ev['id']}/registrations", None),
        ("post", f"/events/{ev['id']}/checkin", {"code": "AAAAAAAA"}),
    ]:
        assert getattr(c, method)(url, **({"json": body} if body else {})).status_code == 401
        h = {"Authorization": "Bearer not-a-token"}
        assert getattr(c, method)(url, headers=h, **({"json": body} if body else {})).status_code == 401
        h = {"Authorization": "Basic abc"}
        assert getattr(c, method)(url, headers=h, **({"json": body} if body else {})).status_code == 401


def test_auth_checked_before_validation_and_404(c):
    assert c.post("/events", json={"name": "", "capacity": 0}).status_code == 401
    assert c.get("/events/99999999/registrations").status_code == 401
    assert c.post("/events/99999999/checkin", json={}).status_code == 401


def test_public_endpoints_need_no_token(c, adm):
    ev = event(c, adm)
    assert c.get("/events").status_code == 200
    assert c.get(f"/events/{ev['id']}").status_code == 200
    r = must_reg(c, ev["id"])
    assert c.get(f"/registrations/{r['id']}").status_code == 200
    assert c.delete(f"/registrations/{r['id']}").status_code == 200


def test_token_works_across_workers(srv, adm):
    codes = set()
    for _ in range(12):
        with httpx.Client(base_url=srv.url, timeout=15) as cc:
            codes.add(cc.get("/events/99999999/registrations", headers=adm).status_code)
    assert codes == {404}


# ---- events -----------------------------------------------------------------------

def test_create_event_shape(c, adm):
    ev = event(c, adm, capacity=3, name="Conf")
    assert ev["name"] == "Conf" and ev["capacity"] == 3
    assert ev["confirmed_count"] == 0 and ev["waitlist_count"] == 0 and ev["checked_in_count"] == 0
    assert c.get(f"/events/{ev['id']}").json() == ev


@pytest.mark.parametrize("body", [
    {"capacity": 2}, {"name": "x"}, {"name": "", "capacity": 2}, {"name": "x", "capacity": 0},
    {"name": "x", "capacity": -4}, {"name": "x", "capacity": "many"}, {"name": "x", "capacity": 2.5},
    {"name": "n" * 101, "capacity": 2},
])
def test_create_event_validation(c, adm, body):
    assert c.post("/events", json=body, headers=adm).status_code == 422


def test_event_list_and_404(c, adm):
    a, b = event(c, adm), event(c, adm)
    ids = [e["id"] for e in c.get("/events").json()]
    assert ids == sorted(ids) and a["id"] in ids and b["id"] in ids
    r = c.get("/events/99999999")
    assert r.status_code == 404 and "detail" in r.json()


# ---- registration ----------------------------------------------------------------------

def test_confirmed_then_waitlisted(c, adm):
    ev = event(c, adm, capacity=2)
    r1, r2, r3, r4 = (must_reg(c, ev["id"]) for _ in range(4))
    assert r1["status"] == r2["status"] == "confirmed"
    assert CODE_RE.match(r1["checkin_code"]) and CODE_RE.match(r2["checkin_code"])
    assert r1["position"] is None
    assert r3["status"] == "waitlisted" and r3["position"] == 1 and r3["checkin_code"] is None
    assert r4["status"] == "waitlisted" and r4["position"] == 2
    got = c.get(f"/events/{ev['id']}").json()
    assert (got["confirmed_count"], got["waitlist_count"]) == (2, 2)


def test_registration_fields_and_get(c, adm):
    ev = event(c, adm)
    r = must_reg(c, ev["id"], "Mixed.Case@Example.COM")
    assert r["email"] == "mixed.case@example.com" and r["event_id"] == ev["id"] and r["name"] == "Ana"
    assert c.get(f"/registrations/{r['id']}").json() == r
    assert c.get("/registrations/99999999").status_code == 404


def test_register_unknown_event_404(c):
    assert reg(c, 99999999).status_code == 404


@pytest.mark.parametrize("body", [
    {"name": "A"}, {"email": "a@b.co"}, {"name": "", "email": "a@b.co"},
    {"name": "A", "email": "not-an-email"}, {"name": "A", "email": "a@"}, {"name": "A", "email": ""},
    {"name": "n" * 101, "email": "a@b.co"},
])
def test_register_validation(c, adm, body):
    ev = event(c, adm)
    assert c.post(f"/events/{ev['id']}/registrations", json=body).status_code == 422
    assert c.get(f"/events/{ev['id']}").json()["confirmed_count"] == 0


def test_duplicate_email_409_case_insensitive(c, adm):
    ev = event(c, adm, capacity=1)
    m = email()
    must_reg(c, ev["id"], m)
    assert reg(c, ev["id"], m.upper()).status_code == 409
    other = must_reg(c, ev["id"])
    assert other["status"] == "waitlisted"
    assert reg(c, ev["id"], other["email"]).status_code == 409
    ev2 = event(c, adm)
    assert reg(c, ev2["id"], m).status_code == 201


def test_codes_unique_and_random_looking(c, adm):
    ev = event(c, adm, capacity=25)
    codes = [must_reg(c, ev["id"])["checkin_code"] for _ in range(25)]
    assert len(set(codes)) == 25 and all(CODE_RE.match(x) for x in codes)
    assert len({x[:3] for x in codes}) > 5  # not sequential


# ---- cancellation ---------------------------------------------------------------------------

def test_cancel_promotes_first_in_line(c, adm):
    ev = event(c, adm, capacity=1)
    a, b, d = (must_reg(c, ev["id"]) for _ in range(3))
    r = c.delete(f"/registrations/{a['id']}")
    assert r.status_code == 200 and r.json()["status"] == "cancelled" and r.json()["checkin_code"] is None
    b2 = c.get(f"/registrations/{b['id']}").json()
    assert b2["status"] == "confirmed" and CODE_RE.match(b2["checkin_code"]) and b2["position"] is None
    d2 = c.get(f"/registrations/{d['id']}").json()
    assert d2["status"] == "waitlisted" and d2["position"] == 1
    got = c.get(f"/events/{ev['id']}").json()
    assert (got["confirmed_count"], got["waitlist_count"]) == (1, 1)


def test_cancel_waitlisted_compacts_positions(c, adm):
    ev = event(c, adm, capacity=1)
    must_reg(c, ev["id"])
    w = [must_reg(c, ev["id"]) for _ in range(3)]
    assert [x["position"] for x in w] == [1, 2, 3]
    assert c.delete(f"/registrations/{w[0]['id']}").status_code == 200
    pos = [c.get(f"/registrations/{x['id']}").json()["position"] for x in w[1:]]
    assert pos == [1, 2]
    assert c.get(f"/events/{ev['id']}").json()["waitlist_count"] == 2


def test_cancel_without_waitlist_frees_seat(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    c.delete(f"/registrations/{a['id']}")
    assert c.get(f"/events/{ev['id']}").json()["confirmed_count"] == 0
    assert must_reg(c, ev["id"])["status"] == "confirmed"


def test_cancel_twice_409_and_404(c, adm):
    ev = event(c, adm)
    a = must_reg(c, ev["id"])
    assert c.delete(f"/registrations/{a['id']}").status_code == 200
    assert c.delete(f"/registrations/{a['id']}").status_code == 409
    assert c.delete("/registrations/99999999").status_code == 404


def test_cancel_twice_does_not_promote_twice(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    b, d = must_reg(c, ev["id"]), must_reg(c, ev["id"])
    c.delete(f"/registrations/{a['id']}")
    c.delete(f"/registrations/{a['id']}")
    assert c.get(f"/registrations/{b['id']}").json()["status"] == "confirmed"
    assert c.get(f"/registrations/{d['id']}").json()["status"] == "waitlisted"


def test_reregister_after_cancel_goes_to_end(c, adm):
    ev = event(c, adm, capacity=1)
    a_mail = email()
    a = must_reg(c, ev["id"], a_mail)
    b = must_reg(c, ev["id"])
    c.delete(f"/registrations/{a['id']}")  # b promoted
    again = must_reg(c, ev["id"], a_mail)
    assert again["id"] != a["id"] and again["status"] == "waitlisted" and again["position"] == 1
    assert b["id"] != again["id"]


# ---- check-in ----------------------------------------------------------------------------------

def test_checkin_flow(c, adm):
    ev = event(c, adm)
    a = must_reg(c, ev["id"])
    r = c.post(f"/events/{ev['id']}/checkin", json={"code": a["checkin_code"]}, headers=adm)
    assert r.status_code == 200 and r.json()["status"] == "checked_in" and r.json()["id"] == a["id"]
    assert r.json()["checkin_code"] == a["checkin_code"]
    got = c.get(f"/events/{ev['id']}").json()
    assert got["checked_in_count"] == 1
    assert c.get(f"/registrations/{a['id']}").json()["status"] == "checked_in"
    again = c.post(f"/events/{ev['id']}/checkin", json={"code": a["checkin_code"]}, headers=adm)
    assert again.status_code == 409


def test_checkin_unknown_other_event_cancelled(c, adm):
    ev, other = event(c, adm), event(c, adm)
    a = must_reg(c, ev["id"])
    path = f"/events/{ev['id']}/checkin"
    assert c.post(path, json={"code": "ZZZZZZZZ"}, headers=adm).status_code == 404
    assert c.post(f"/events/{other['id']}/checkin", json={"code": a["checkin_code"]}, headers=adm).status_code == 404
    assert c.post("/events/99999999/checkin", json={"code": a["checkin_code"]}, headers=adm).status_code == 404
    c.delete(f"/registrations/{a['id']}")
    assert c.post(path, json={"code": a["checkin_code"]}, headers=adm).status_code == 404


def test_checkin_validation(c, adm):
    ev = event(c, adm)
    assert c.post(f"/events/{ev['id']}/checkin", json={}, headers=adm).status_code == 422


def test_promoted_code_checks_in(c, adm):
    ev = event(c, adm, capacity=1)
    a, b = must_reg(c, ev["id"]), must_reg(c, ev["id"])
    c.delete(f"/registrations/{a['id']}")
    code = c.get(f"/registrations/{b['id']}").json()["checkin_code"]
    assert c.post(f"/events/{ev['id']}/checkin", json={"code": code}, headers=adm).status_code == 200


def test_checked_in_cannot_be_cancelled_and_keeps_seat(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    w = must_reg(c, ev["id"])
    c.post(f"/events/{ev['id']}/checkin", json={"code": a["checkin_code"]}, headers=adm)
    assert c.delete(f"/registrations/{a['id']}").status_code == 409
    assert c.get(f"/registrations/{w['id']}").json()["status"] == "waitlisted"
    assert reg(c, ev["id"], a["email"]).status_code == 409  # still an active registration


def test_checked_in_counts_as_seat_for_new_registrations(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    c.post(f"/events/{ev['id']}/checkin", json={"code": a["checkin_code"]}, headers=adm)
    assert must_reg(c, ev["id"])["status"] == "waitlisted"
    got = c.get(f"/events/{ev['id']}").json()
    assert got["checked_in_count"] == 1 and got["waitlist_count"] == 1


# ---- admin listing --------------------------------------------------------------------------------

def test_admin_listing_and_filter(c, adm):
    ev = event(c, adm, capacity=1)
    a, b, d = (must_reg(c, ev["id"]) for _ in range(3))
    c.delete(f"/registrations/{d['id']}")
    rows = c.get(f"/events/{ev['id']}/registrations", headers=adm).json()
    assert [r["id"] for r in rows] == [a["id"], b["id"], d["id"]]
    only = c.get(f"/events/{ev['id']}/registrations", params={"status": "waitlisted"}, headers=adm).json()
    assert [r["id"] for r in only] == [b["id"]]
    assert c.get("/events/99999999/registrations", headers=adm).status_code == 404


# ---- concurrency (two workers, one database) -------------------------------------------------------

def test_no_overbooking_under_concurrent_registration(srv, adm):
    with httpx.Client(base_url=srv.url, timeout=30) as c0:
        ev = event(c0, adm, capacity=5)

    def go(i):
        with httpx.Client(base_url=srv.url, timeout=30) as cc:
            return cc.post(f"/events/{ev['id']}/registrations",
                           json={"name": f"U{i}", "email": f"race{os.getpid()}-{i}@example.com"})

    with ThreadPoolExecutor(40) as ex:
        resp = list(ex.map(go, range(40)))
    assert all(r.status_code == 201 for r in resp), [r.text for r in resp if r.status_code != 201]
    statuses = [r.json()["status"] for r in resp]
    assert statuses.count("confirmed") == 5 and statuses.count("waitlisted") == 35
    positions = sorted(r.json()["position"] for r in resp if r.json()["status"] == "waitlisted")
    assert positions == list(range(1, 36))
    codes = [r.json()["checkin_code"] for r in resp if r.json()["status"] == "confirmed"]
    assert len(set(codes)) == 5
    with httpx.Client(base_url=srv.url, timeout=30) as c0:
        got = c0.get(f"/events/{ev['id']}").json()
    assert (got["confirmed_count"], got["waitlist_count"]) == (5, 35)


def test_concurrent_cancellations_promote_exactly_once_each(srv, adm):
    with httpx.Client(base_url=srv.url, timeout=30) as c0:
        ev = event(c0, adm, capacity=4)
        regs = [must_reg(c0, ev["id"]) for _ in range(10)]
    confirmed = [r for r in regs if r["status"] == "confirmed"]

    def go(r):
        with httpx.Client(base_url=srv.url, timeout=30) as cc:
            return cc.delete(f"/registrations/{r['id']}").status_code

    with ThreadPoolExecutor(8) as ex:
        codes = list(ex.map(go, confirmed + confirmed))  # every cancel sent twice, concurrently
    assert codes.count(200) == 4 and codes.count(409) == 4, codes
    with httpx.Client(base_url=srv.url, timeout=30) as c0:
        got = c0.get(f"/events/{ev['id']}").json()
        assert (got["confirmed_count"], got["waitlist_count"]) == (4, 2)
        pos = sorted(c0.get(f"/registrations/{r['id']}").json()["position"] or 0 for r in regs[4:])
        assert pos == [0, 0, 0, 0, 1, 2]


def test_concurrent_duplicate_registration_only_one_wins(srv, adm):
    with httpx.Client(base_url=srv.url, timeout=30) as c0:
        ev = event(c0, adm, capacity=10)
    m = email()

    def go(_):
        with httpx.Client(base_url=srv.url, timeout=30) as cc:
            return cc.post(f"/events/{ev['id']}/registrations", json={"name": "D", "email": m}).status_code

    with ThreadPoolExecutor(12) as ex:
        codes = list(ex.map(go, range(12)))
    assert codes.count(201) == 1 and codes.count(409) == 11, codes


def test_concurrent_double_checkin_only_one_wins(srv, adm):
    with httpx.Client(base_url=srv.url, timeout=30) as c0:
        ev = event(c0, adm)
        a = must_reg(c0, ev["id"])

    def go(_):
        with httpx.Client(base_url=srv.url, timeout=30) as cc:
            return cc.post(f"/events/{ev['id']}/checkin", json={"code": a["checkin_code"]}, headers=adm).status_code

    with ThreadPoolExecutor(10) as ex:
        codes = list(ex.map(go, range(10)))
    assert codes.count(200) == 1 and codes.count(409) == 9, codes


# ---- config / persistence -----------------------------------------------------------------------------

def test_no_admin_credentials_means_login_always_401(tmp_path):
    s = Server(os.environ["APP_DIR"], extra_env={"ADMIN_USER": None, "ADMIN_PASSWORD": None})
    try:
        s.wait_ready()
        for body in ({"username": "", "password": ""}, {"username": "admin", "password": "admin"}):
            assert httpx.post(s.url + "/admin/login", json=body, timeout=10).status_code == 401
    finally:
        s.stop()


def test_tokens_and_data_survive_restart(tmp_path):
    db = str(tmp_path / "persist.db")
    s = Server(os.environ["APP_DIR"], extra_env=ENV, db_path=db)
    try:
        s.wait_ready()
        tok = httpx.post(s.url + "/admin/login", json={"username": USER, "password": PASSWORD}, timeout=10).json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        ev = httpx.post(s.url + "/events", json={"name": "P", "capacity": 1}, headers=h, timeout=10).json()
        httpx.post(f"{s.url}/events/{ev['id']}/registrations", json={"name": "A", "email": "a@x.io"}, timeout=10)
    finally:
        s.stop()
    s2 = Server(os.environ["APP_DIR"], extra_env=ENV, db_path=db)
    try:
        s2.wait_ready()
        got = httpx.get(f"{s2.url}/events/{ev['id']}", timeout=10).json()
        assert got["confirmed_count"] == 1
        r = httpx.get(f"{s2.url}/events/{ev['id']}/registrations", headers=h, timeout=10)
        assert r.status_code == 200 and len(r.json()) == 1
    finally:
        s2.stop()

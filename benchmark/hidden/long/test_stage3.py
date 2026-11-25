"""Hidden acceptance tests, stage 3: the outbox and the admin cancellation of a checked-in registration.
Never copied into a run workspace."""
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from conftest import CODE_RE, event, get_event, get_reg, kinds, must_reg, outbox, reg


# ---- outbox: auth and filters -----------------------------------------------------

def test_outbox_needs_admin_token(c):
    assert c.get("/admin/outbox").status_code == 401
    assert c.get("/admin/outbox", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert c.get("/admin/outbox?event_id=abc").status_code == 401  # auth before validation


def test_outbox_filter_validation_422(c, adm):
    assert c.get("/admin/outbox", headers=adm, params={"event_id": "abc"}).status_code == 422
    assert c.get("/admin/outbox", headers=adm, params={"registration_id": "x"}).status_code == 422


def test_outbox_item_shape_and_order(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    b = must_reg(c, ev["id"])
    rows = outbox(c, adm, event_id=ev["id"])
    assert [(r["registration_id"], r["kind"]) for r in rows] == [(a["id"], "confirmed"), (b["id"], "waitlisted")]
    assert all(set(r) == {"id", "event_id", "registration_id", "kind"} and r["event_id"] == ev["id"] for r in rows)
    assert [r["id"] for r in rows] == sorted(r["id"] for r in rows)
    assert len({r["id"] for r in rows}) == 2


def test_outbox_filters_by_event_and_registration(c, adm):
    e1, e2 = event(c, adm, capacity=2), event(c, adm, capacity=2)
    a = must_reg(c, e1["id"])
    must_reg(c, e2["id"])
    assert {r["event_id"] for r in outbox(c, adm, event_id=e1["id"])} == {e1["id"]}
    assert [r["kind"] for r in outbox(c, adm, registration_id=a["id"])] == ["confirmed"]
    assert outbox(c, adm, event_id=e1["id"], registration_id=a["id"] + 10_000_000) == []


# ---- outbox: one notification per transition --------------------------------------

def test_registration_records_confirmed_or_waitlisted(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    b = must_reg(c, ev["id"])
    assert kinds(c, adm, a["id"]) == ["confirmed"]
    assert kinds(c, adm, b["id"]) == ["waitlisted"]


def test_cancel_records_cancelled_then_promoted_for_the_next_in_line(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    b = must_reg(c, ev["id"])
    assert c.delete(f"/registrations/{a['id']}").status_code == 200
    rows = outbox(c, adm, event_id=ev["id"])
    assert [(r["registration_id"], r["kind"]) for r in rows] == [
        (a["id"], "confirmed"), (b["id"], "waitlisted"), (a["id"], "cancelled"), (b["id"], "promoted")]


def test_cancel_waitlisted_records_cancelled_only(c, adm):
    ev = event(c, adm, capacity=1)
    must_reg(c, ev["id"])
    w = must_reg(c, ev["id"])
    c.delete(f"/registrations/{w['id']}")
    assert kinds(c, adm, w["id"]) == ["waitlisted", "cancelled"]
    assert [r["kind"] for r in outbox(c, adm, event_id=ev["id"])].count("promoted") == 0


def test_capacity_raise_records_promoted_for_each_person(c, adm):
    """A decision from stage 2 must reach the stage 3 outbox: promotions happen in PATCH too."""
    ev = event(c, adm, capacity=1)
    must_reg(c, ev["id"])
    w = [must_reg(c, ev["id"]) for _ in range(3)]
    assert c.patch(f"/events/{ev['id']}", json={"capacity": 3}, headers=adm).status_code == 200
    rows = [r for r in outbox(c, adm, event_id=ev["id"]) if r["kind"] == "promoted"]
    assert [r["registration_id"] for r in rows] == [w[0]["id"], w[1]["id"]]
    assert kinds(c, adm, w[2]["id"]) == ["waitlisted"]


def test_rename_and_checkin_record_nothing(c, adm):
    ev = event(c, adm, capacity=2)
    a = must_reg(c, ev["id"])
    before = outbox(c, adm, event_id=ev["id"])
    c.patch(f"/events/{ev['id']}", json={"name": "Renamed"}, headers=adm)
    c.post(f"/events/{ev['id']}/checkin", json={"code": a["checkin_code"]}, headers=adm)
    assert outbox(c, adm, event_id=ev["id"]) == before


def test_rejected_requests_record_nothing(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    n = len(outbox(c, adm, event_id=ev["id"]))
    assert reg(c, ev["id"], a["email"]).status_code == 409           # duplicate
    assert reg(c, 999999).status_code == 404                          # unknown event
    assert c.post(f"/events/{ev['id']}/registrations", json={"name": "", "email": "x"}).status_code == 422
    assert c.patch(f"/events/{ev['id']}", json={"capacity": 0}, headers=adm).status_code == 422
    c.delete(f"/registrations/{a['id']}")
    assert c.delete(f"/registrations/{a['id']}").status_code == 409   # second cancel
    assert c.delete("/registrations/999999").status_code == 404
    assert len(outbox(c, adm, event_id=ev["id"])) == n + 1            # only the one real cancellation


def test_failed_capacity_patch_records_nothing(c, adm):
    ev = event(c, adm, capacity=2)
    must_reg(c, ev["id"])
    must_reg(c, ev["id"])
    n = len(outbox(c, adm, event_id=ev["id"]))
    assert c.patch(f"/events/{ev['id']}", json={"capacity": 1}, headers=adm).status_code == 409
    assert len(outbox(c, adm, event_id=ev["id"])) == n


# ---- outbox: concurrency ----------------------------------------------------------

def test_concurrent_registrations_record_exactly_one_notification_each(srv, adm):
    with httpx.Client(base_url=srv.url, timeout=30) as setup:
        ev = event(setup, adm, capacity=3)
    n = 24

    def register(i):
        with httpx.Client(base_url=srv.url, timeout=30) as cl:
            r = cl.post(f"/events/{ev['id']}/registrations", json={"name": f"P{i}", "email": f"ob{ev['id']}x{i}@example.com"})
            return r.status_code, r.json()["id"]

    with ThreadPoolExecutor(12) as pool:
        results = [f.result() for f in [pool.submit(register, i) for i in range(n)]]
    assert all(code == 201 for code, _ in results)
    with httpx.Client(base_url=srv.url, timeout=30) as cl:
        rows = outbox(cl, adm, event_id=ev["id"])
        assert len(rows) == n
        assert sorted(r["registration_id"] for r in rows) == sorted(i for _, i in results)
        assert sorted(r["kind"] for r in rows).count("confirmed") == 3
        assert sorted(r["kind"] for r in rows).count("waitlisted") == n - 3


def test_concurrent_cancel_of_the_same_registration_records_one_cancellation(srv, adm):
    with httpx.Client(base_url=srv.url, timeout=30) as setup:
        ev = event(setup, adm, capacity=1)
        a = must_reg(setup, ev["id"])
        w = must_reg(setup, ev["id"])

    def cancel(_):
        with httpx.Client(base_url=srv.url, timeout=30) as cl:
            return cl.delete(f"/registrations/{a['id']}").status_code

    with ThreadPoolExecutor(8) as pool:
        codes = [f.result() for f in [pool.submit(cancel, i) for i in range(8)]]
    assert sorted(codes) == [200] + [409] * 7
    with httpx.Client(base_url=srv.url, timeout=30) as cl:
        assert kinds(cl, adm, a["id"]) == ["confirmed", "cancelled"]
        assert kinds(cl, adm, w["id"]) == ["waitlisted", "promoted"]
        assert get_reg(cl, w["id"])["status"] == "confirmed"


def test_concurrent_cancellations_and_capacity_raise_promote_each_person_once(srv, adm):
    with httpx.Client(base_url=srv.url, timeout=30) as setup:
        ev = event(setup, adm, capacity=3)
        seated = [must_reg(setup, ev["id"]) for _ in range(3)]
        waiting = [must_reg(setup, ev["id"]) for _ in range(6)]

    def cancel(r):
        with httpx.Client(base_url=srv.url, timeout=30) as cl:
            return cl.delete(f"/registrations/{r['id']}").status_code

    def raise_to(cap):
        with httpx.Client(base_url=srv.url, timeout=30) as cl:
            return cl.patch(f"/events/{ev['id']}", json={"capacity": cap}, headers=adm).status_code

    with ThreadPoolExecutor(8) as pool:
        futures = [pool.submit(cancel, r) for r in seated] + [pool.submit(raise_to, 5), pool.submit(raise_to, 5)]
        assert all(f.result() == 200 for f in futures)
    with httpx.Client(base_url=srv.url, timeout=30) as cl:
        after = get_event(cl, ev["id"])
        assert after["capacity"] == 5 and after["confirmed_count"] == 5 and after["waitlist_count"] == 1
        rows = outbox(cl, adm, event_id=ev["id"])
        promoted = [r["registration_id"] for r in rows if r["kind"] == "promoted"]
        assert len(promoted) == len(set(promoted)) == 5
        assert set(promoted) <= {w["id"] for w in waiting}
        assert [r["kind"] for r in rows].count("cancelled") == 3
        assert len(rows) == 9 + 3 + 5


# ---- changed rule: admin cancels a checked-in registration ------------------------

def checked_in(c, adm, capacity=1):
    ev = event(c, adm, capacity=capacity)
    a = must_reg(c, ev["id"])
    assert c.post(f"/events/{ev['id']}/checkin", json={"code": a["checkin_code"]}, headers=adm).status_code == 200
    return ev, a


def test_checked_in_cancel_without_token_is_still_409(c, adm):
    ev, a = checked_in(c, adm)
    assert c.delete(f"/registrations/{a['id']}").status_code == 409
    assert get_reg(c, a["id"])["status"] == "checked_in"


def test_checked_in_cancel_with_bad_token_is_401_even_for_other_statuses(c, adm):
    ev, a = checked_in(c, adm, capacity=2)
    b = must_reg(c, ev["id"])
    bad = {"Authorization": "Bearer not-a-token"}
    assert c.delete(f"/registrations/{a['id']}", headers=bad).status_code == 401
    assert c.delete(f"/registrations/{b['id']}", headers=bad).status_code == 401
    assert c.delete(f"/registrations/{b['id']}", headers={"Authorization": "Basic zzz"}).status_code == 401
    assert get_reg(c, b["id"])["status"] == "confirmed"


def test_admin_cancels_a_checked_in_registration(c, adm):
    ev, a = checked_in(c, adm, capacity=1)
    w = must_reg(c, ev["id"])
    assert w["status"] == "waitlisted"
    r = c.delete(f"/registrations/{a['id']}", headers=adm)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "cancelled" and body["checkin_code"] is None and body["position"] is None
    promoted = get_reg(c, w["id"])
    assert promoted["status"] == "confirmed" and CODE_RE.match(promoted["checkin_code"])
    after = get_event(c, ev["id"])
    assert after["checked_in_count"] == 0 and after["confirmed_count"] == 1 and after["waitlist_count"] == 0
    assert kinds(c, adm, a["id"]) == ["confirmed", "cancelled"]
    assert kinds(c, adm, w["id"]) == ["waitlisted", "promoted"]


def test_code_of_an_admin_cancelled_registration_stops_working(c, adm):
    ev, a = checked_in(c, adm, capacity=2)
    c.delete(f"/registrations/{a['id']}", headers=adm)
    assert c.post(f"/events/{ev['id']}/checkin", json={"code": a["checkin_code"]}, headers=adm).status_code == 404


def test_admin_cancel_twice_is_409_and_unknown_is_404(c, adm):
    ev, a = checked_in(c, adm, capacity=2)
    assert c.delete(f"/registrations/{a['id']}", headers=adm).status_code == 200
    assert c.delete(f"/registrations/{a['id']}", headers=adm).status_code == 409
    assert c.delete("/registrations/999999", headers=adm).status_code == 404


def test_person_can_register_again_after_admin_cancel(c, adm):
    ev, a = checked_in(c, adm, capacity=1)
    c.delete(f"/registrations/{a['id']}", headers=adm)
    again = reg(c, ev["id"], a["email"])
    assert again.status_code == 201 and again.json()["status"] == "confirmed"


def test_admin_cancel_of_a_normal_registration_still_works(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    assert c.delete(f"/registrations/{a['id']}", headers=adm).status_code == 200
    assert get_reg(c, a["id"])["status"] == "cancelled"

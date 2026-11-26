"""Hidden acceptance tests, stage 2: PATCH /events/{id} and GET /events/{id}/waitlist. Never copied into a run workspace."""
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from conftest import CODE_RE, event, get_event, get_reg, must_reg, reg


# ---- PATCH: auth and validation ---------------------------------------------------

def test_patch_needs_admin_token(c, adm):
    ev = event(c, adm)
    assert c.patch(f"/events/{ev['id']}", json={"name": "X"}).status_code == 401
    assert c.patch(f"/events/{ev['id']}", json={"name": "X"}, headers={"Authorization": "Bearer nope"}).status_code == 401
    assert c.patch(f"/events/{ev['id']}", json={"name": "X"}, headers={"Authorization": "Basic abc"}).status_code == 401


def test_patch_auth_before_404_and_422(c):
    assert c.patch("/events/999999", json={"capacity": 5}).status_code == 401
    assert c.patch("/events/1", json={}).status_code == 401


def test_patch_unknown_event_404(c, adm):
    assert c.patch("/events/999999", json={"capacity": 5}, headers=adm).status_code == 404


@pytest.mark.parametrize("body", [{}, {"capacity": 0}, {"capacity": -3}, {"capacity": "5"}, {"capacity": 2.5},
                                  {"name": ""}, {"name": "x" * 101}, {"name": 7}])
def test_patch_validation_422(c, adm, body):
    ev = event(c, adm, capacity=3, name="Keep")
    r = c.patch(f"/events/{ev['id']}", json=body, headers=adm)
    assert r.status_code == 422, (body, r.text)
    after = get_event(c, ev["id"])
    assert after["capacity"] == 3 and after["name"] == "Keep"


# ---- PATCH: behaviour -------------------------------------------------------------

def test_patch_renames_and_keeps_the_rest(c, adm):
    ev = event(c, adm, capacity=2, name="Old")
    a = must_reg(c, ev["id"])
    r = c.patch(f"/events/{ev['id']}", json={"name": "New name"}, headers=adm)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "New name" and body["capacity"] == 2 and body["confirmed_count"] == 1 and body["id"] == ev["id"]
    assert get_reg(c, a["id"])["status"] == "confirmed"


def test_patch_capacity_below_seats_taken_409_and_changes_nothing(c, adm):
    ev = event(c, adm, capacity=3, name="Same")
    for _ in range(3):
        must_reg(c, ev["id"])
    r = c.patch(f"/events/{ev['id']}", json={"capacity": 2, "name": "Changed"}, headers=adm)
    assert r.status_code == 409, r.text
    after = get_event(c, ev["id"])
    assert after["capacity"] == 3 and after["name"] == "Same"


def test_patch_capacity_counts_checked_in_as_taken(c, adm):
    ev = event(c, adm, capacity=2)
    a = must_reg(c, ev["id"])
    must_reg(c, ev["id"])
    c.post(f"/events/{ev['id']}/checkin", json={"code": a["checkin_code"]}, headers=adm)
    assert c.patch(f"/events/{ev['id']}", json={"capacity": 1}, headers=adm).status_code == 409
    assert c.patch(f"/events/{ev['id']}", json={"capacity": 2}, headers=adm).status_code == 200


def test_patch_capacity_to_exactly_seats_taken_is_ok(c, adm):
    ev = event(c, adm, capacity=4)
    for _ in range(2):
        must_reg(c, ev["id"])
    r = c.patch(f"/events/{ev['id']}", json={"capacity": 2}, headers=adm)
    assert r.status_code == 200 and r.json()["capacity"] == 2
    assert must_reg(c, ev["id"])["status"] == "waitlisted"


def test_patch_cancelled_seat_does_not_count(c, adm):
    ev = event(c, adm, capacity=3)
    a = must_reg(c, ev["id"])
    must_reg(c, ev["id"])
    c.delete(f"/registrations/{a['id']}")
    assert c.patch(f"/events/{ev['id']}", json={"capacity": 1}, headers=adm).status_code == 200


def test_raising_capacity_promotes_the_front_of_the_waiting_list_in_order(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    w = [must_reg(c, ev["id"]) for _ in range(4)]
    assert [x["position"] for x in w] == [1, 2, 3, 4]
    r = c.patch(f"/events/{ev['id']}", json={"capacity": 3}, headers=adm)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["capacity"] == 3 and body["confirmed_count"] == 3 and body["waitlist_count"] == 2
    assert get_reg(c, a["id"])["status"] == "confirmed"
    p1, p2, p3, p4 = (get_reg(c, x["id"]) for x in w)
    assert (p1["status"], p2["status"]) == ("confirmed", "confirmed")
    assert CODE_RE.match(p1["checkin_code"]) and CODE_RE.match(p2["checkin_code"]) and p1["checkin_code"] != p2["checkin_code"]
    assert p1["position"] is None and p2["position"] is None
    assert (p3["status"], p3["position"]) == ("waitlisted", 1)
    assert (p4["status"], p4["position"]) == ("waitlisted", 2)
    assert p3["checkin_code"] is None


def test_raising_capacity_beyond_waiting_list_promotes_everyone(c, adm):
    ev = event(c, adm, capacity=1)
    must_reg(c, ev["id"])
    w = [must_reg(c, ev["id"]) for _ in range(2)]
    body = c.patch(f"/events/{ev['id']}", json={"capacity": 10}, headers=adm).json()
    assert body["confirmed_count"] == 3 and body["waitlist_count"] == 0
    assert all(get_reg(c, x["id"])["status"] == "confirmed" for x in w)


def test_raising_capacity_with_empty_waiting_list(c, adm):
    ev = event(c, adm, capacity=1)
    must_reg(c, ev["id"])
    body = c.patch(f"/events/{ev['id']}", json={"capacity": 5}, headers=adm).json()
    assert body["confirmed_count"] == 1 and body["waitlist_count"] == 0
    assert must_reg(c, ev["id"])["status"] == "confirmed"


def test_promoted_by_capacity_can_check_in(c, adm):
    ev = event(c, adm, capacity=1)
    must_reg(c, ev["id"])
    w = must_reg(c, ev["id"])
    c.patch(f"/events/{ev['id']}", json={"capacity": 2}, headers=adm)
    code = get_reg(c, w["id"])["checkin_code"]
    r = c.post(f"/events/{ev['id']}/checkin", json={"code": code}, headers=adm)
    assert r.status_code == 200 and r.json()["status"] == "checked_in"


def test_patch_skips_cancelled_people_in_the_waiting_list(c, adm):
    ev = event(c, adm, capacity=1)
    must_reg(c, ev["id"])
    w1, w2, w3 = (must_reg(c, ev["id"]) for _ in range(3))
    c.delete(f"/registrations/{w1['id']}")
    c.patch(f"/events/{ev['id']}", json={"capacity": 2}, headers=adm)
    assert get_reg(c, w2["id"])["status"] == "confirmed"
    assert (get_reg(c, w3["id"])["status"], get_reg(c, w3["id"])["position"]) == ("waitlisted", 1)


# ---- PATCH: concurrency -----------------------------------------------------------

def test_capacity_raise_and_registrations_never_overbook(srv, adm):
    with httpx.Client(base_url=srv.url, timeout=30) as setup:
        ev = event(setup, adm, capacity=2)
    n = 30

    def register(i):
        with httpx.Client(base_url=srv.url, timeout=30) as cl:
            return cl.post(f"/events/{ev['id']}/registrations", json={"name": f"P{i}", "email": f"cc{ev['id']}x{i}@example.com"}).status_code

    def raise_to(cap):
        with httpx.Client(base_url=srv.url, timeout=30) as cl:
            return cl.patch(f"/events/{ev['id']}", json={"capacity": cap}, headers=adm).status_code

    with ThreadPoolExecutor(16) as pool:
        regs = [pool.submit(register, i) for i in range(n)]
        raises = [pool.submit(raise_to, cap) for cap in (8, 8, 8)]
        assert all(f.result() == 201 for f in regs)
        assert all(f.result() == 200 for f in raises)
    with httpx.Client(base_url=srv.url, timeout=30) as cl:
        after = get_event(cl, ev["id"])
        assert after["capacity"] == 8
        assert after["confirmed_count"] + after["checked_in_count"] <= 8
        assert after["confirmed_count"] == 8 and after["waitlist_count"] == n - 8
        rows = cl.get(f"/events/{ev['id']}/registrations", headers=adm).json()
        assert sorted(r["position"] for r in rows if r["status"] == "waitlisted") == list(range(1, n - 8 + 1))
        codes = [r["checkin_code"] for r in rows if r["status"] == "confirmed"]
        assert len(set(codes)) == 8


def test_concurrent_capacity_raises_promote_each_person_once(srv, adm):
    with httpx.Client(base_url=srv.url, timeout=30) as setup:
        ev = event(setup, adm, capacity=1)
        must_reg(setup, ev["id"])
        for _ in range(6):
            must_reg(setup, ev["id"])

    def raise_to(_):
        with httpx.Client(base_url=srv.url, timeout=30) as cl:
            return cl.patch(f"/events/{ev['id']}", json={"capacity": 4}, headers=adm).status_code

    with ThreadPoolExecutor(8) as pool:
        assert all(f.result() == 200 for f in [pool.submit(raise_to, i) for i in range(8)])
    with httpx.Client(base_url=srv.url, timeout=30) as cl:
        after = get_event(cl, ev["id"])
        assert after["confirmed_count"] == 4 and after["waitlist_count"] == 3


# ---- waiting list endpoint --------------------------------------------------------

def test_waitlist_needs_admin(c, adm):
    ev = event(c, adm, capacity=1)
    assert c.get(f"/events/{ev['id']}/waitlist").status_code == 401
    assert c.get(f"/events/{ev['id']}/waitlist", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert c.get("/events/999999/waitlist").status_code == 401


def test_waitlist_unknown_event_404(c, adm):
    assert c.get("/events/999999/waitlist", headers=adm).status_code == 404


def test_waitlist_lists_only_waitlisted_in_position_order(c, adm):
    ev = event(c, adm, capacity=1)
    a = must_reg(c, ev["id"])
    assert c.get(f"/events/{ev['id']}/waitlist", headers=adm).json() == []
    w = [must_reg(c, ev["id"]) for _ in range(3)]
    c.delete(f"/registrations/{w[0]['id']}")
    rows = c.get(f"/events/{ev['id']}/waitlist", headers=adm).json()
    assert [r["id"] for r in rows] == [w[1]["id"], w[2]["id"]]
    assert [r["position"] for r in rows] == [1, 2]
    assert all(r["status"] == "waitlisted" and r["checkin_code"] is None for r in rows)
    assert a["id"] not in [r["id"] for r in rows]


def test_waitlist_empties_after_capacity_raise(c, adm):
    ev = event(c, adm, capacity=1)
    must_reg(c, ev["id"])
    must_reg(c, ev["id"])
    c.patch(f"/events/{ev['id']}", json={"capacity": 2}, headers=adm)
    assert c.get(f"/events/{ev['id']}/waitlist", headers=adm).json() == []


def test_register_still_waitlists_when_full_after_patch(c, adm):
    ev = event(c, adm, capacity=1)
    must_reg(c, ev["id"])
    c.patch(f"/events/{ev['id']}", json={"capacity": 2}, headers=adm)
    assert must_reg(c, ev["id"])["status"] == "confirmed"
    assert reg(c, ev["id"]).json()["status"] == "waitlisted"

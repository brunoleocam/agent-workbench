"""Fixtures and helpers for the hidden tests of the long task (stages 2 and 3). Never copied into a run workspace."""
import os
import re
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Server  # noqa: E402

USER, PASSWORD = "root-admin", "s3cret-Pass!"
ENV = {"ADMIN_USER": USER, "ADMIN_PASSWORD": PASSWORD}
CODE_RE = re.compile(r"^[A-Z0-9]{8}$")


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
    return f"l{os.getpid()}x{_n[0]}@example.com"


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


def get_event(c, ev_id):
    r = c.get(f"/events/{ev_id}")
    assert r.status_code == 200, r.text
    return r.json()


def get_reg(c, reg_id):
    r = c.get(f"/registrations/{reg_id}")
    assert r.status_code == 200, r.text
    return r.json()


def outbox(c, adm, **params):
    r = c.get("/admin/outbox", headers=adm, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def kinds(c, adm, reg_id):
    return [n["kind"] for n in outbox(c, adm, registration_id=reg_id)]

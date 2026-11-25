"""Reference implementation used ONLY to validate the hidden tests. Never given to an agent."""
import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import string
import time
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, StrictInt

DB = os.environ.get("DB_PATH", "events.db")
app = FastAPI()
ALPHA = string.ascii_uppercase + string.digits
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def conn():
    c = sqlite3.connect(DB, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    return c


c0 = conn()
c0.execute("PRAGMA journal_mode=WAL")
c0.executescript("""
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, capacity INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS regs(id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, name TEXT NOT NULL,
  email TEXT NOT NULL, status TEXT NOT NULL, code TEXT UNIQUE, seq INTEGER NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS one_active ON regs(event_id, email) WHERE status != 'cancelled';
""")
c0.close()


def key():
    return (os.environ.get("ADMIN_PASSWORD") or "").encode()


def make_token():
    exp = str(int(time.time()) + 3600)
    sig = hmac.new(key(), exp.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{exp}.{sig}".encode()).decode()


def admin(authorization: Optional[str] = Header(default=None)):
    try:
        scheme, tok = (authorization or "").split(" ", 1)
        if scheme != "Bearer" or not key():
            raise ValueError
        exp, sig = base64.urlsafe_b64decode(tok.encode()).decode().split(".", 1)
        good = hmac.new(key(), exp.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, good) or int(exp) < time.time():
            raise ValueError
    except Exception:
        raise HTTPException(401, "unauthorized")


class Login(BaseModel):
    username: str
    password: str


class EventIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    capacity: StrictInt = Field(ge=1)


class RegIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str


class CheckIn(BaseModel):
    code: str


def event_out(c, e):
    n = lambda st: c.execute("SELECT COUNT(*) FROM regs WHERE event_id=? AND status IN (%s)" % st, (e["id"],)).fetchone()[0]
    return {"id": e["id"], "name": e["name"], "capacity": e["capacity"],
            "confirmed_count": n("'confirmed','checked_in'") - n("'checked_in'"),
            "waitlist_count": n("'waitlisted'"), "checked_in_count": n("'checked_in'")}


def reg_out(c, r):
    pos = None
    if r["status"] == "waitlisted":
        pos = c.execute("SELECT COUNT(*) FROM regs WHERE event_id=? AND status='waitlisted' AND seq<=?",
                        (r["event_id"], r["seq"])).fetchone()[0]
    return {"id": r["id"], "event_id": r["event_id"], "name": r["name"], "email": r["email"],
            "status": r["status"], "position": pos, "checkin_code": r["code"]}


def new_code(c):
    while True:
        code = "".join(secrets.choice(ALPHA) for _ in range(8))
        if not c.execute("SELECT 1 FROM regs WHERE code=?", (code,)).fetchone():
            return code


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/admin/login")
def login(b: Login):
    u, p = os.environ.get("ADMIN_USER"), os.environ.get("ADMIN_PASSWORD")
    if not u or not p:
        raise HTTPException(401, "invalid credentials")
    ok = hmac.compare_digest(b.username.encode(), u.encode()) & hmac.compare_digest(b.password.encode(), p.encode())
    if not ok:
        raise HTTPException(401, "invalid credentials")
    return {"token": make_token()}


@app.post("/events", status_code=201, dependencies=[Depends(admin)])
def create_event(b: EventIn):
    c = conn()
    cur = c.execute("INSERT INTO events(name,capacity) VALUES(?,?)", (b.name, b.capacity))
    return event_out(c, c.execute("SELECT * FROM events WHERE id=?", (cur.lastrowid,)).fetchone())


@app.get("/events")
def list_events():
    c = conn()
    return [event_out(c, e) for e in c.execute("SELECT * FROM events ORDER BY id")]


def ev_or_404(c, event_id):
    e = c.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if not e:
        raise HTTPException(404, "event not found")
    return e


@app.get("/events/{event_id}")
def get_event(event_id: int):
    c = conn()
    return event_out(c, ev_or_404(c, event_id))


@app.post("/events/{event_id}/registrations", status_code=201)
def register(event_id: int, b: RegIn):
    if not EMAIL.match(b.email):
        raise HTTPException(422, "invalid email")
    email = b.email.lower()
    c = conn()
    c.execute("BEGIN IMMEDIATE")
    try:
        e = ev_or_404(c, event_id)
        if c.execute("SELECT 1 FROM regs WHERE event_id=? AND email=? AND status!='cancelled'", (event_id, email)).fetchone():
            raise HTTPException(409, "already registered")
        taken = c.execute("SELECT COUNT(*) FROM regs WHERE event_id=? AND status IN ('confirmed','checked_in')", (event_id,)).fetchone()[0]
        seq = (c.execute("SELECT COALESCE(MAX(seq),0) FROM regs WHERE event_id=?", (event_id,)).fetchone()[0]) + 1
        if taken < e["capacity"]:
            status, code = "confirmed", new_code(c)
        else:
            status, code = "waitlisted", None
        cur = c.execute("INSERT INTO regs(event_id,name,email,status,code,seq) VALUES(?,?,?,?,?,?)",
                        (event_id, b.name, email, status, code, seq))
        out = reg_out(c, c.execute("SELECT * FROM regs WHERE id=?", (cur.lastrowid,)).fetchone())
        c.execute("COMMIT")
        return out
    except BaseException:
        if c.in_transaction:
            c.execute("ROLLBACK")
        raise


@app.get("/registrations/{reg_id}")
def get_reg(reg_id: int):
    c = conn()
    r = c.execute("SELECT * FROM regs WHERE id=?", (reg_id,)).fetchone()
    if not r:
        raise HTTPException(404, "registration not found")
    return reg_out(c, r)


@app.delete("/registrations/{reg_id}")
def cancel(reg_id: int):
    c = conn()
    c.execute("BEGIN IMMEDIATE")
    try:
        r = c.execute("SELECT * FROM regs WHERE id=?", (reg_id,)).fetchone()
        if not r:
            raise HTTPException(404, "registration not found")
        if r["status"] in ("cancelled", "checked_in"):
            raise HTTPException(409, "cannot cancel")
        was = r["status"]
        c.execute("UPDATE regs SET status='cancelled', code=NULL WHERE id=?", (reg_id,))
        if was == "confirmed":
            nxt = c.execute("SELECT id FROM regs WHERE event_id=? AND status='waitlisted' ORDER BY seq LIMIT 1", (r["event_id"],)).fetchone()
            if nxt:
                c.execute("UPDATE regs SET status='confirmed', code=? WHERE id=?", (new_code(c), nxt["id"]))
        out = reg_out(c, c.execute("SELECT * FROM regs WHERE id=?", (reg_id,)).fetchone())
        c.execute("COMMIT")
        return out
    except BaseException:
        if c.in_transaction:
            c.execute("ROLLBACK")
        raise


@app.get("/events/{event_id}/registrations", dependencies=[Depends(admin)])
def admin_list(event_id: int, status: Optional[str] = None):
    c = conn()
    ev_or_404(c, event_id)
    rows = c.execute("SELECT * FROM regs WHERE event_id=? ORDER BY id", (event_id,)).fetchall()
    return [reg_out(c, r) for r in rows if not status or r["status"] == status]


@app.post("/events/{event_id}/checkin", dependencies=[Depends(admin)])
def checkin(event_id: int, b: CheckIn):
    c = conn()
    c.execute("BEGIN IMMEDIATE")
    try:
        ev_or_404(c, event_id)
        r = c.execute("SELECT * FROM regs WHERE event_id=? AND code=? AND status IN ('confirmed','checked_in')", (event_id, b.code)).fetchone()
        if not r:
            raise HTTPException(404, "code not found")
        if r["status"] == "checked_in":
            raise HTTPException(409, "already checked in")
        c.execute("UPDATE regs SET status='checked_in' WHERE id=?", (r["id"],))
        out = reg_out(c, c.execute("SELECT * FROM regs WHERE id=?", (r["id"],)).fetchone())
        c.execute("COMMIT")
        return out
    except BaseException:
        if c.in_transaction:
            c.execute("ROLLBACK")
        raise

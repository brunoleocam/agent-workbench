"""Reference implementation used ONLY to validate the hidden tests. Never given to an agent."""
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt

DB = os.environ.get("DB_PATH", "stock.db")
app = FastAPI()


def conn():
    c = sqlite3.connect(DB, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    return c


def init():
    c = conn()
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL, min_stock INTEGER NOT NULL DEFAULT 0, quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity>=0));
    CREATE TABLE IF NOT EXISTS movements(id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL,
      type TEXT NOT NULL, quantity INTEGER NOT NULL, note TEXT, balance_after INTEGER NOT NULL, created_at TEXT NOT NULL);
    """)
    c.close()


init()


class ItemIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sku: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=100)
    min_stock: StrictInt = Field(default=0, ge=0)


class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=100)
    min_stock: StrictInt = Field(ge=0)


class MovIn(BaseModel):
    type: str = Field(pattern="^(in|out)$")
    quantity: StrictInt = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=200)


def row(r):
    return dict(r)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/items", status_code=201)
def create(b: ItemIn):
    c = conn()
    try:
        cur = c.execute("INSERT INTO items(sku,name,min_stock) VALUES(?,?,?)", (b.sku, b.name, b.min_stock))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "sku already exists")
    return row(c.execute("SELECT * FROM items WHERE id=?", (cur.lastrowid,)).fetchone())


@app.get("/items")
def list_items(q: Optional[str] = None):
    c = conn()
    rows = c.execute("SELECT * FROM items ORDER BY id").fetchall()
    out = [row(r) for r in rows]
    if q:
        ql = q.lower()
        out = [r for r in out if ql in r["sku"].lower() or ql in r["name"].lower()]
    return out


def get_or_404(c, item_id):
    r = c.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not r:
        raise HTTPException(404, "item not found")
    return r


@app.get("/items/{item_id}")
def get_item(item_id: int):
    return row(get_or_404(conn(), item_id))


@app.put("/items/{item_id}")
def update(item_id: int, b: ItemUpdate):
    c = conn()
    get_or_404(c, item_id)
    c.execute("UPDATE items SET name=?, min_stock=? WHERE id=?", (b.name, b.min_stock, item_id))
    return row(get_or_404(c, item_id))


@app.delete("/items/{item_id}")
def delete(item_id: int):
    c = conn()
    c.execute("BEGIN IMMEDIATE")
    r = c.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not r:
        c.execute("ROLLBACK")
        raise HTTPException(404, "item not found")
    if r["quantity"] > 0:
        c.execute("ROLLBACK")
        raise HTTPException(409, "item has stock")
    c.execute("DELETE FROM movements WHERE item_id=?", (item_id,))
    c.execute("DELETE FROM items WHERE id=?", (item_id,))
    c.execute("COMMIT")
    return Response(status_code=204)


@app.post("/items/{item_id}/movements", status_code=201)
def move(item_id: int, b: MovIn):
    c = conn()
    c.execute("BEGIN IMMEDIATE")
    r = c.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not r:
        c.execute("ROLLBACK")
        raise HTTPException(404, "item not found")
    bal = r["quantity"] + (b.quantity if b.type == "in" else -b.quantity)
    if bal < 0:
        c.execute("ROLLBACK")
        raise HTTPException(409, "insufficient stock")
    now = datetime.now(timezone.utc).isoformat()
    c.execute("UPDATE items SET quantity=? WHERE id=?", (bal, item_id))
    cur = c.execute("INSERT INTO movements(item_id,type,quantity,note,balance_after,created_at) VALUES(?,?,?,?,?,?)",
                    (item_id, b.type, b.quantity, b.note, bal, now))
    c.execute("COMMIT")
    return row(c.execute("SELECT * FROM movements WHERE id=?", (cur.lastrowid,)).fetchone())


@app.get("/items/{item_id}/movements")
def history(item_id: int):
    c = conn()
    get_or_404(c, item_id)
    return [row(r) for r in c.execute("SELECT * FROM movements WHERE item_id=? ORDER BY id", (item_id,))]


@app.get("/reports/low-stock")
def low():
    c = conn()
    rows = [row(r) for r in c.execute("SELECT * FROM items WHERE quantity < min_stock")]
    for r in rows:
        r["shortfall"] = r["min_stock"] - r["quantity"]
    rows.sort(key=lambda r: (-r["shortfall"], r["sku"]))
    return rows

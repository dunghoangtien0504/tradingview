"""Nhat ky giao dich — dung khuon Bai 20: ngay, boi canh da khung, muc
tieu/ly do, diem vao, SL, khoi luong, ket qua, dung/sai ke hoach.

SQLite don gian, 1 file, khong can server DB rieng — phu hop quy mo ca
nhan. File nam ngoai git (xem .gitignore).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent.parent / "journal.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    khung_choi TEXT NOT NULL,
    boi_canh_da_khung TEXT,
    ly_do TEXT,
    huong TEXT,
    entry_price REAL,
    sl_price REAL,
    khoi_luong_usd REAL,
    ket_qua TEXT DEFAULT 'dang_mo',
    exit_price REAL,
    pnl_usd REAL,
    dung_ke_hoach INTEGER DEFAULT 1,
    ghi_chu TEXT
);
"""


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_FILE)
    c.row_factory = sqlite3.Row
    c.execute(_SCHEMA)
    return c


def add_trade(**fields) -> int:
    fields.setdefault("created_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    cols = ", ".join(fields.keys())
    qs = ", ".join(["?"] * len(fields))
    with _conn() as c:
        cur = c.execute(f"INSERT INTO trades ({cols}) VALUES ({qs})", list(fields.values()))
        return cur.lastrowid


def update_trade(trade_id: int, **fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    with _conn() as c:
        c.execute(f"UPDATE trades SET {sets} WHERE id = ?", [*fields.values(), trade_id])


def delete_trade(trade_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM trades WHERE id = ?", [trade_id])


def list_trades(limit: int = 200) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", [limit]
        ).fetchall()
        return [dict(r) for r in rows]


def stats() -> dict:
    with _conn() as c:
        rows = c.execute("SELECT ket_qua, pnl_usd, dung_ke_hoach FROM trades").fetchall()
    total = len(rows)
    closed = [r for r in rows if r["ket_qua"] in ("thang", "thua")]
    wins = [r for r in closed if r["ket_qua"] == "thang"]
    dung_kh = [r for r in rows if r["dung_ke_hoach"]]
    total_pnl = sum(r["pnl_usd"] or 0 for r in rows)
    return {
        "tong_so_lenh": total,
        "dang_mo": total - len(closed),
        "da_dong": len(closed),
        "winrate_pct": round(100 * len(wins) / len(closed), 1) if closed else None,
        "tong_pnl_usd": round(total_pnl, 2),
        "ty_le_dung_ke_hoach_pct": round(100 * len(dung_kh) / total, 1) if total else None,
    }

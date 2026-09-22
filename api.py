"""FastAPI mong bao quanh lsteven_mcp core — phuc vu dashboard HTML/JS.

Chay:  uvicorn api:app --reload --port 8787
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from lsteven_mcp import journal as journal_db
from lsteven_mcp.data import DataError, get_klines
from lsteven_mcp.form_trap import detect_forms, detect_traps
from lsteven_mcp.indicators import add_lines
from lsteven_mcp.multiframe import ORDER, snapshot as mf_snapshot
from lsteven_mcp.risk import position_size

app = FastAPI(title="LSteven Cockpit API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STATIC_DIR = Path(__file__).resolve().parent / "webapp"

# Khung -> do dai 1 nen, dung de tinh dem nguoc toi luc dong nen tiep theo.
_TF_SECONDS = {
    "H1": 3600, "H2": 2 * 3600, "H3": 3 * 3600, "H4": 4 * 3600,
    "H6": 6 * 3600, "H12": 12 * 3600,
    "D": 24 * 3600, "2D": 2 * 24 * 3600, "3D": 3 * 24 * 3600, "4D": 4 * 24 * 3600,
    "W": 7 * 24 * 3600,
    "M": None,  # thang khong co do dai co dinh, xu ly rieng
}


def _next_close(tf: str, last_open_iso: str) -> str:
    """Uoc luong thoi diem dong nen TIEP THEO cho mot khung, tu open_time
    cua nen gan nhat da fetch. Day la uoc luong lich UTC don gian (khung
    Binance dong theo bien UTC co dinh cho hau het interval), du dung cho
    muc dich "con bao lau nua nen dong" tren dashboard — khong phai nguon
    su that giao dich, chi la tin hieu hien thi.
    """
    last_open = datetime.fromisoformat(last_open_iso)
    if last_open.tzinfo is None:
        last_open = last_open.replace(tzinfo=timezone.utc)

    if tf == "M":
        y, m = last_open.year, last_open.month
        nm, ny = (m % 12) + 1, y + (1 if m == 12 else 0)
        nxt = last_open.replace(year=ny, month=nm)
        # nen thang tiep theo do; cong them 1 chu ky nua neu nen hien tai da qua
        while nxt <= datetime.now(timezone.utc):
            y2, m2 = nxt.year, nxt.month
            nm2, ny2 = (m2 % 12) + 1, y2 + (1 if m2 == 12 else 0)
            nxt = nxt.replace(year=ny2, month=nm2)
        return nxt.isoformat()

    sec = _TF_SECONDS[tf]
    close = last_open + timedelta(seconds=sec)
    now = datetime.now(timezone.utc)
    while close <= now:
        close += timedelta(seconds=sec)
    return close.isoformat()


@app.get("/api/snapshot")
def api_snapshot(symbol: str = "BTCUSDT"):
    snap = mf_snapshot(symbol)
    for tf, r in snap["readings"].items():
        r["next_close"] = _next_close(tf, r["last_close_time"])
    snap["server_time"] = datetime.now(timezone.utc).isoformat()
    return snap


@app.get("/api/signals")
def api_signals(symbol: str = "BTCUSDT", timeframe: str = "D"):
    try:
        raw = get_klines(symbol, timeframe, limit=300)
    except DataError as e:
        raise HTTPException(400, str(e))
    df = add_lines(raw)
    forms = detect_forms(df, lookback=200)[-10:][::-1]
    traps = detect_traps(df, lookback=300)[-10:][::-1]
    return {
        "forms": [{"direction": f.direction, "diem3_time": f.diem3_time,
                    "diem3_rsi": round(f.diem3_rsi, 1)} for f in forms],
        "traps": [{"direction": t.direction, "start_time": t.start_time,
                    "status": t.status, "extreme_rsi": round(t.extreme_rsi, 1),
                    "detail": t.detail} for t in traps],
    }


class SizeReq(BaseModel):
    equity: float
    entry: float
    sl: float
    risk_pct: float = 2.0


@app.post("/api/position-size")
def api_position_size(req: SizeReq):
    return position_size(req.equity, req.entry, req.sl, req.risk_pct)


# ------------------------------------------------------------ journal ---

class TradeIn(BaseModel):
    symbol: str
    khung_choi: str
    huong: str
    boi_canh_da_khung: str | None = None
    ly_do: str | None = None
    entry_price: float | None = None
    sl_price: float | None = None
    khoi_luong_usd: float | None = None
    ghi_chu: str | None = None


class TradeUpdate(BaseModel):
    ket_qua: str | None = None
    exit_price: float | None = None
    pnl_usd: float | None = None
    dung_ke_hoach: int | None = None
    ghi_chu: str | None = None


@app.get("/api/journal")
def api_journal_list():
    return {"trades": journal_db.list_trades(), "stats": journal_db.stats()}


@app.post("/api/journal")
def api_journal_add(t: TradeIn):
    tid = journal_db.add_trade(**t.model_dump())
    return {"id": tid}


@app.patch("/api/journal/{trade_id}")
def api_journal_update(trade_id: int, t: TradeUpdate):
    fields = {k: v for k, v in t.model_dump().items() if v is not None}
    journal_db.update_trade(trade_id, **fields)
    return {"ok": True}


@app.delete("/api/journal/{trade_id}")
def api_journal_delete(trade_id: int):
    journal_db.delete_trade(trade_id)
    return {"ok": True}


# ------------------------------------------------------------- static ---

app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")

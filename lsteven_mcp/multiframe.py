"""Multi-timeframe snapshot (Bai 6 & 8): read every LSteven timeframe at
once, in the same "M -> W -> 3D -> D -> H12 -> H4 -> H1" order the method
reads a plan in (Bai 20 Quy trinh buoc 1).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd

from . import indicators as ind
from .data import TIMEFRAMES, get_klines
from .form_trap import detect_traps


ORDER = ["M", "W", "3D", "D", "H12", "H4", "H1"]  # large -> small, matches Bai 20


@dataclass
class TFReading:
    timeframe: str
    last_close_time: str
    price: float
    rsi: float
    ema9: float
    wma45: float
    above_45: bool
    muc_luc: int
    imbalance_side: str | None
    imbalance_candles: int
    active_trap: str | None   # "down" | "up" | None


def read_timeframe(symbol: str, tf: str, limit: int = 300) -> tuple[pd.DataFrame, TFReading]:
    raw = get_klines(symbol, tf, limit=limit)
    df = ind.add_lines(raw)
    last = df.iloc[-1]
    imb = ind.mat_can_bang(df["rsi"])

    traps = detect_traps(df, lookback=limit)
    active_trap = None
    if traps and traps[-1].status == "dang_dien_ra":
        active_trap = traps[-1].direction

    reading = TFReading(
        timeframe=tf,
        last_close_time=str(last["open_time"]),
        price=round(float(last["close"]), 2),
        rsi=round(float(last["rsi"]), 2),
        ema9=round(float(last["ema9"]), 2),
        wma45=round(float(last["wma45"]), 2),
        above_45=bool(last["rsi"] > 45),
        muc_luc=ind.muc_luc(last["rsi"], last["ema9"], last["wma45"]),
        imbalance_side=imb["side"],
        imbalance_candles=imb["candles_on_side"],
        active_trap=active_trap,
    )
    return df, reading


def snapshot(symbol: str = "BTCUSDT") -> dict:
    """One call = Bai 20 buoc 1: doc bo canh da khung. Returns per-timeframe
    readings in M->H1 order plus a same-side-of-45 dong-thuan map for every
    adjacent pair (Bai 8's "hai khung lien ke")."
    """
    readings: dict[str, TFReading] = {}
    errors: dict[str, str] = {}
    for tf in ORDER:
        try:
            _, r = read_timeframe(symbol, tf)
            readings[tf] = r
        except Exception as e:  # keep going even if one timeframe's fetch fails
            errors[tf] = str(e)

    dong_thuan = {}
    for a, b in zip(ORDER, ORDER[1:]):
        if a in readings and b in readings:
            dong_thuan[f"{a}-{b}"] = readings[a].above_45 == readings[b].above_45

    return {
        "symbol": symbol.upper(),
        "readings": {tf: asdict(r) for tf, r in readings.items()},
        "dong_thuan_ke_nhau": dong_thuan,
        "errors": errors or None,
    }

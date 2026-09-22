"""Multi-timeframe snapshot (Bai 6 & 8): read every LSteven timeframe at
once, in the same "M -> W -> 3D -> D -> H12 -> H4 -> H1" order the method
reads a plan in (Bai 20 Quy trinh buoc 1).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict

import pandas as pd

from . import indicators as ind
from .assess import assess
from .data import CANONICAL, get_klines
from .form_trap import detect_traps


# Large -> small, the order Bai 20 buoc 1 reads a plan in. The 7 frames in
# CANONICAL are the method's own set; the rest are user-added extras.
ORDER = ["M", "W", "4D", "3D", "2D", "D", "H12", "H6", "H4", "H3", "H2", "H1"]


@dataclass
class TFReading:
    timeframe: str
    last_close_time: str
    price: float
    open_price: float
    rsi: float
    ema9: float
    wma45: float
    above_45: bool
    muc_luc: int
    imbalance_side: str | None
    imbalance_candles: int
    active_trap: str | None   # "down" | "up" | None
    canonical: bool = True    # True = khung thuoc bo goc LSteven (Bai 6)
    rsi_series: list[float] = None
    ema9_series: list[float] = None
    wma45_series: list[float] = None
    nhan_dinh: dict = None


def read_timeframe(symbol: str, tf: str, limit: int = 300, sparkline_n: int = 24) -> tuple[pd.DataFrame, TFReading]:
    raw = get_klines(symbol, tf, limit=limit)
    df = ind.add_lines(raw)
    last = df.iloc[-1]
    imb = ind.mat_can_bang(df)

    traps = detect_traps(df, lookback=limit)
    active_trap = None
    if traps and traps[-1].status == "dang_dien_ra":
        active_trap = traps[-1].direction

    tail = df.tail(sparkline_n)
    reading = TFReading(
        timeframe=tf,
        last_close_time=str(last["open_time"]),
        price=round(float(last["close"]), 2),
        open_price=round(float(last["open"]), 2),
        rsi=round(float(last["rsi"]), 2),
        ema9=round(float(last["ema9"]), 2),
        wma45=round(float(last["wma45"]), 2),
        # "tren/duoi duong 45" = RSI vs the WMA45 LINE (Bai 3: "moi tin hieu
        # len/xuong deu doc qua viec RSI nam tren hay duoi no"), not vs the
        # number 45.
        above_45=bool(last["rsi"] > last["wma45"]),
        muc_luc=ind.muc_luc(last["rsi"], last["ema9"], last["wma45"]),
        imbalance_side=imb["side"],
        imbalance_candles=imb["candles_on_side"],
        active_trap=active_trap,
        canonical=tf in CANONICAL,
        rsi_series=[round(float(v), 2) for v in tail["rsi"]],
        ema9_series=[round(float(v), 2) for v in tail["ema9"]],
        wma45_series=[round(float(v), 2) for v in tail["wma45"]],
    )
    reading.nhan_dinh = asdict(assess(df, reading))
    return df, reading


def snapshot(symbol: str = "BTCUSDT") -> dict:
    """One call = Bai 20 buoc 1: doc bo canh da khung. Returns per-timeframe
    readings in M->H1 order plus a same-side-of-45 dong-thuan map for every
    adjacent pair (Bai 8's "hai khung lien ke")."
    """
    readings: dict[str, TFReading] = {}
    errors: dict[str, str] = {}

    def _one(tf: str):
        try:
            _, r = read_timeframe(symbol, tf)
            return tf, r, None
        except Exception as e:  # keep going even if one timeframe's fetch fails
            return tf, None, str(e)

    # 12 frames sequentially would mean 12+ round trips to Binance per refresh;
    # fan them out so a snapshot stays snappy.
    with ThreadPoolExecutor(max_workers=6) as pool:
        for tf, r, err in pool.map(_one, ORDER):
            if err:
                errors[tf] = err
            else:
                readings[tf] = r
    readings = {tf: readings[tf] for tf in ORDER if tf in readings}

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

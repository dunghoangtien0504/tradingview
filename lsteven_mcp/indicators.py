"""The three lines (Bai 3): RSI, EMA9-of-RSI, WMA45-of-RSI — plus two
derived readings the method uses constantly: muc_luc (strength 1-6) and
mat_can_bang (imbalance).

IMPORTANT — what is exact vs. what is an interpretation:
  * RSI(14) Wilder smoothing, EMA(9) and WMA(45) applied to the RSI series
    are the method's own explicit, unambiguous definitions (Bai 3).
  * `muc_luc` (1-6) and the imbalance thresholds are NOT given as exact
    numbers anywhere in the source material — the book only describes them
    qualitatively ("so RSI position against the two lines", "read as a
    process, not a snapshot"). The mapping used here is this project's own
    reasonable operationalisation, documented inline, so callers can see
    exactly what a "6" or a "mat can bang" flag actually means and adjust
    it. Treat these two as decision-support, not ground truth.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rsi_wilder(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def wma(series: pd.Series, length: int) -> pd.Series:
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def add_lines(df: pd.DataFrame, rsi_len: int = 14, ema_len: int = 9, wma_len: int = 45) -> pd.DataFrame:
    """Return a copy of df with rsi / ema9 / wma45 columns added."""
    out = df.copy()
    out["rsi"] = rsi_wilder(out["close"], rsi_len)
    out["ema9"] = ema(out["rsi"], ema_len)
    out["wma45"] = wma(out["rsi"], wma_len)
    return out


def muc_luc(rsi: float, ema9: float, wma45: float) -> int:
    """Strength scale 1-6 (Bai 4): higher = buyers more in control.

    Operationalisation (see module docstring): position of RSI relative to
    EMA9/WMA45, and whether each line already cleared the 45 boundary.
        6: RSI > EMA9 > WMA45, all three above 45      (fully bullish, mature)
        5: RSI > EMA9 > WMA45, but WMA45 still <= 45    (bullish, still forming)
        4: RSI > EMA9, RSI <= WMA45                     (early bullish: diem 1-2)
        3: RSI <= EMA9, RSI > WMA45                      (early bearish: diem 1-2)
        2: RSI <= EMA9 <= WMA45, but WMA45 still > 45    (bearish, still forming)
        1: RSI <= EMA9 <= WMA45, all three <= 45         (fully bearish, mature)
    """
    if any(pd.isna(v) for v in (rsi, ema9, wma45)):
        return 0
    if rsi > ema9 >= wma45 or (rsi > ema9 and ema9 > wma45):
        return 6 if (rsi > 45 and wma45 > 45) else 5
    if rsi > ema9:
        return 4
    if rsi <= ema9 and rsi > wma45:
        return 3
    if wma45 > 45:
        return 2
    return 1


def mat_can_bang(rsi_series: pd.Series, lookback: int = 30) -> dict:
    """Imbalance read (Bai 9): RSI parked on one side of 45 for a long time
    with no return trip is a real, quotable pattern in the source ("BTC 2022
    bottom: RSI W stuck 31-37 for ~4 months"). This just measures how long
    and how far RSI has stayed on its current side of 45 over `lookback`
    candles — it is a magnitude/duration read, not a trap (trap needs the
    20/80 threshold, see form_trap.py).
    """
    s = rsi_series.dropna().tail(lookback)
    if len(s) < 5:
        return {"side": None, "candles_on_side": 0, "mean_distance_from_45": None}
    side = "above" if s.iloc[-1] >= 45 else "below"
    on_side = (s >= 45) if side == "above" else (s < 45)
    # count the currently-running streak from the end
    streak = 0
    for v in on_side.iloc[::-1]:
        if v:
            streak += 1
        else:
            break
    recent = s.tail(streak) if streak else s.tail(1)
    return {
        "side": side,
        "candles_on_side": int(streak),
        "mean_distance_from_45": round(float((recent - 45).abs().mean()), 2),
    }

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

    Purely the RELATIVE ORDER of the three lines, which is exactly how the
    book describes it ("vi tri tuong quan cua ba duong"). Deliberately does
    NOT test RSI against the number 45: in the source, "duong 45" is the
    WMA45 line itself (the same sentence calls it "duong WMA45 (do)" and
    "duong 45"), not the numeric RSI level 45.

        6: RSI > EMA9 > WMA45     (full bullish stack)
        5: RSI > EMA9, EMA9 <= WMA45  (RSI leading, EMA9 hasn't cleared red)
        4: RSI > WMA45, RSI <= EMA9   (pullback inside a bullish read)
        3: RSI <= WMA45, RSI > EMA9   (bounce inside a bearish read)
        2: RSI <= EMA9, EMA9 > WMA45  (bearish forming)
        1: RSI <= EMA9 <= WMA45   (full bearish stack)
    """
    if any(pd.isna(v) for v in (rsi, ema9, wma45)):
        return 0
    if rsi > ema9:
        return 6 if ema9 > wma45 else 5
    # rsi <= ema9
    if rsi > wma45:
        return 4
    if ema9 > wma45:
        return 2
    return 1 if rsi <= ema9 else 3


def mat_can_bang(df: pd.DataFrame, lookback: int = 60) -> dict:
    """Imbalance read (Bai 9): RSI parked on one side of the WMA45 line for a
    long time with no return trip. The book is explicit that this is measured
    against "duong 45" — i.e. the WMA45 line, not the price and not the
    numeric RSI level 45.
    """
    sub = df[["rsi", "wma45"]].dropna().tail(lookback)
    if len(sub) < 5:
        return {"side": None, "candles_on_side": 0, "mean_distance": None}

    above = sub["rsi"] > sub["wma45"]
    side = "above" if bool(above.iloc[-1]) else "below"
    on_side = above if side == "above" else ~above

    streak = 0
    for v in on_side.iloc[::-1]:
        if v:
            streak += 1
        else:
            break
    recent = sub.tail(streak) if streak else sub.tail(1)
    return {
        "side": side,
        "candles_on_side": int(streak),
        "mean_distance": round(float((recent["rsi"] - recent["wma45"]).abs().mean()), 2),
    }

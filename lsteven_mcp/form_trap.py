"""Form (Bai 4) and Trap (Bai 10-11) detectors.

These operationalise qualitative rules from the source into deterministic
scans over the RSI/EMA9/WMA45 series. The source itself is explicit that
this reading is a *process*, judged with discretion ("mot khoang, khong
tuyet doi") — these detectors are decision support for a human reader,
not a black-box signal generator. Every function returns the underlying
dates/values so a caller (or Claude) can sanity-check the call.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


# ------------------------------------------------------------------ Form ---

@dataclass
class FormEvent:
    direction: str          # "buy" | "sell"
    diem1_time: str | None  # local RSI extremum before the cross sequence
    diem1_rsi: float | None
    diem2_time: str         # RSI crosses EMA9
    diem2_rsi: float
    diem3_time: str         # RSI crosses WMA45 (confirmation)
    diem3_rsi: float


def detect_forms(df: pd.DataFrame, lookback: int = 200, extremum_window: int = 10) -> list[FormEvent]:
    """Scan the last `lookback` candles for form buy/sell sequences:
    RSI crosses EMA9 (diem 2), then later crosses WMA45 in the same
    direction (diem 3) before reversing. diem 1 is the RSI local
    extremum in the `extremum_window` candles right before diem 2.
    """
    d = df.dropna(subset=["rsi", "ema9", "wma45"]).tail(lookback).reset_index(drop=True)
    if len(d) < 5:
        return []

    above_ema = (d["rsi"] > d["ema9"]).to_numpy()
    above_wma = (d["rsi"] > d["wma45"]).to_numpy()
    events: list[FormEvent] = []
    pending: dict | None = None  # a diem2 waiting for its diem3

    for i in range(1, len(d)):
        ema_cross_up = above_ema[i] and not above_ema[i - 1]
        ema_cross_dn = (not above_ema[i]) and above_ema[i - 1]
        wma_cross_up = above_wma[i] and not above_wma[i - 1]
        wma_cross_dn = (not above_wma[i]) and above_wma[i - 1]

        if ema_cross_up:
            pending = {"direction": "buy", "diem2_i": i}
        elif ema_cross_dn:
            pending = {"direction": "sell", "diem2_i": i}

        if pending is not None:
            if pending["direction"] == "buy" and wma_cross_up and i >= pending["diem2_i"]:
                j2 = pending["diem2_i"]
                lo = max(0, j2 - extremum_window)
                j1 = d["rsi"].iloc[lo:j2 + 1].idxmin() if j2 > lo else None
                events.append(FormEvent(
                    "buy",
                    str(d["open_time"].iloc[j1]) if j1 is not None else None,
                    float(d["rsi"].iloc[j1]) if j1 is not None else None,
                    str(d["open_time"].iloc[j2]), float(d["rsi"].iloc[j2]),
                    str(d["open_time"].iloc[i]), float(d["rsi"].iloc[i]),
                ))
                pending = None
            elif pending["direction"] == "sell" and wma_cross_dn and i >= pending["diem2_i"]:
                j2 = pending["diem2_i"]
                lo = max(0, j2 - extremum_window)
                j1 = d["rsi"].iloc[lo:j2 + 1].idxmax() if j2 > lo else None
                events.append(FormEvent(
                    "sell",
                    str(d["open_time"].iloc[j1]) if j1 is not None else None,
                    float(d["rsi"].iloc[j1]) if j1 is not None else None,
                    str(d["open_time"].iloc[j2]), float(d["rsi"].iloc[j2]),
                    str(d["open_time"].iloc[i]), float(d["rsi"].iloc[i]),
                ))
                pending = None
            # if the opposite EMA cross happens before WMA confirms, the
            # pending sequence is simply superseded (handled above since
            # ema_cross_up/dn reassigns `pending`).

    return events


# ------------------------------------------------------------------ Trap ---

@dataclass
class TrapEpisode:
    direction: str            # "down" (RSI<20) | "up" (RSI>80)
    start_time: str
    end_time: str              # last candle still inside the 20/80 zone
    extreme_rsi: float
    status: str                 # "dang_dien_ra" | "tra_thanh_cong" | "tra_khong_thanh_cong" | "hong"
    resolved_time: str | None = None
    detail: str = ""


def detect_traps(df: pd.DataFrame, lookback: int = 400,
                  pre_extreme_window: int = 30, resolve_horizon: int = 90) -> list[TrapEpisode]:
    """Scan for RSI<20 / RSI>80 episodes and classify how each resolved,
    per Bai 10-11's own rules:
      - "tra_trap" = RSI crosses back through WMA45 (giving it a chance to
        curl, i.e. WMA45 wasn't left far behind) before hitting the 70/30
        undo-threshold. Split into thanh_cong / khong_thanh_cong by whether
        price then also cleared the pre-episode local extreme.
      - "hong" = RSI reaches 70 (down-trap) or 30 (up-trap) while WMA45 is
        still a long way off (rule of thumb: >=15 RSI points away) — i.e.
        it never got the chance to curl into a form.
      - "dang_dien_ra" = neither happened within `resolve_horizon` candles.
    """
    d = df.dropna(subset=["rsi", "ema9", "wma45"]).tail(lookback).reset_index(drop=True)
    if len(d) < 20:
        return []

    rsi = d["rsi"].to_numpy()
    wma = d["wma45"].to_numpy()
    close = d["close"].to_numpy()
    n = len(d)

    below20 = rsi < 20
    above80 = rsi > 80
    episodes: list[TrapEpisode] = []

    def _scan(mask, direction):
        i = 0
        while i < n:
            if not mask[i]:
                i += 1
                continue
            start = i
            while i < n and mask[i]:
                i += 1
            end = i - 1
            seg = rsi[start:end + 1]
            extreme = float(seg.min() if direction == "down" else seg.max())
            ep = TrapEpisode(
                direction=direction,
                start_time=str(d["open_time"].iloc[start]),
                end_time=str(d["open_time"].iloc[end]),
                extreme_rsi=extreme,
                status="dang_dien_ra",
            )
            pre_lo = max(0, start - pre_extreme_window)
            pre_extreme_px = (close[pre_lo:start].max() if direction == "down"
                               else close[pre_lo:start].min()) if start > pre_lo else None

            horizon_end = min(n, end + 1 + resolve_horizon)
            resolved = False
            for k in range(end + 1, horizon_end):
                crossed_wma = (rsi[k] > wma[k]) if direction == "down" else (rsi[k] < wma[k])
                if crossed_wma:
                    ep.resolved_time = str(d["open_time"].iloc[k])
                    if direction == "down":
                        px_ok = pre_extreme_px is not None and close[k:horizon_end].max() >= pre_extreme_px
                    else:
                        px_ok = pre_extreme_px is not None and close[k:horizon_end].min() <= pre_extreme_px
                    ep.status = "tra_thanh_cong" if px_ok else "tra_khong_thanh_cong"
                    ep.detail = (f"RSI cat lai {'tren' if direction=='down' else 'duoi'} WMA45 tai "
                                 f"{ep.resolved_time}; gia {'da' if px_ok else 'chua'} vuot "
                                 f"{'dinh' if direction=='down' else 'day'} cu.")
                    resolved = True
                    break
                undo_hit = (rsi[k] >= 70) if direction == "down" else (rsi[k] <= 30)
                gap = abs(rsi[k] - wma[k])
                if undo_hit and gap >= 15:
                    ep.resolved_time = str(d["open_time"].iloc[k])
                    ep.status = "hong"
                    ep.detail = (f"RSI toi {'>=70' if direction=='down' else '<=30'} tai {ep.resolved_time} "
                                 f"trong khi WMA45 con cach {gap:.1f} diem — bat thang, khong kip cuon.")
                    resolved = True
                    break
            if not resolved:
                ep.detail = "Van trong vung trap, chua co ket luan trong horizon quan sat."
            episodes.append(ep)

    _scan(below20, "down")
    _scan(above80, "up")
    episodes.sort(key=lambda e: e.start_time)
    return episodes

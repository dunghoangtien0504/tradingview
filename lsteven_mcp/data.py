"""Market data access — Binance public REST API, no API key required.

Only spot klines (candlesticks) are used. Binance's native intervals cover
every timeframe the LSteven method uses directly:
    H1 -> 1h · H4 -> 4h · H12 -> 12h · D -> 1d · 3D -> 3d · W -> 1w · M -> 1M
so no resampling is needed anywhere in this package.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd
import requests

BINANCE_BASE = "https://api.binance.com/api/v3/klines"

# LSteven's fixed timeframe set (Sach, Chuong 3). Keys are what tools accept;
# values are Binance's own interval strings.
TIMEFRAMES: dict[str, str] = {
    "H1": "1h",
    "H4": "4h",
    "H12": "12h",
    "D": "1d",
    "3D": "3d",
    "W": "1w",
    "M": "1M",
}

_KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "qav", "trades", "tbbav", "tbqav", "ignore",
]


class DataError(RuntimeError):
    pass


@dataclass
class _CacheEntry:
    at: float
    df: pd.DataFrame


_CACHE: dict[tuple[str, str, int], _CacheEntry] = {}
_CACHE_TTL_S = 30  # short TTL: cheap safety net against hammering Binance
                    # on repeated tool calls within one analysis session.


def get_klines(symbol: str, tf_key: str, limit: int = 300) -> pd.DataFrame:
    """Fetch the most recent `limit` candles for `symbol` at LSteven timeframe
    `tf_key` (one of TIMEFRAMES). Returns a DataFrame sorted oldest->newest
    with columns open_time, open, high, low, close, volume (floats/Timestamp).
    """
    tf_key = tf_key.upper()
    if tf_key not in TIMEFRAMES:
        raise DataError(f"unknown timeframe {tf_key!r}; use one of {list(TIMEFRAMES)}")
    interval = TIMEFRAMES[tf_key]
    limit = max(60, min(limit, 1000))  # floor of 60 so indicators (WMA45) have warmup

    key = (symbol.upper(), interval, limit)
    hit = _CACHE.get(key)
    if hit and (time.time() - hit.at) < _CACHE_TTL_S:
        return hit.df

    try:
        r = requests.get(
            BINANCE_BASE,
            params={"symbol": symbol.upper(), "interval": interval, "limit": limit},
            timeout=15,
        )
        r.raise_for_status()
        raw = r.json()
    except requests.RequestException as e:
        raise DataError(f"Binance request failed for {symbol} {tf_key}: {e}") from e

    if isinstance(raw, dict) and raw.get("code"):
        raise DataError(f"Binance error for {symbol} {tf_key}: {raw}")
    if not raw:
        raise DataError(f"Binance returned no candles for {symbol} {tf_key} "
                         f"(bad symbol, or pair not listed?)")

    df = pd.DataFrame(raw, columns=_KLINE_COLS)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    df = df[["open_time", "open", "high", "low", "close", "volume"]].reset_index(drop=True)

    _CACHE[key] = _CacheEntry(at=time.time(), df=df)
    return df


def get_klines_extended(symbol: str, tf_key: str, start: str, end: str | None = None) -> pd.DataFrame:
    """Paginated fetch for backtesting — Binance caps a single request to
    1000 candles, so this loops. `start`/`end` are anything pandas.Timestamp
    understands (e.g. "2019-01-01"). Not cached (backtests call this once
    per run, not per tool call, so the 30s TTL cache is the wrong tool here).
    """
    tf_key = tf_key.upper()
    if tf_key not in TIMEFRAMES:
        raise DataError(f"unknown timeframe {tf_key!r}; use one of {list(TIMEFRAMES)}")
    interval = TIMEFRAMES[tf_key]

    start_ms = int(pd.Timestamp(start).timestamp() * 1000)
    end_ms = int(pd.Timestamp(end).timestamp() * 1000) if end else int(time.time() * 1000)

    rows: list = []
    cur = start_ms
    while cur < end_ms:
        try:
            r = requests.get(
                BINANCE_BASE,
                params={"symbol": symbol.upper(), "interval": interval,
                        "startTime": cur, "endTime": end_ms, "limit": 1000},
                timeout=20,
            )
            r.raise_for_status()
            batch = r.json()
        except requests.RequestException as e:
            raise DataError(f"Binance request failed for {symbol} {tf_key}: {e}") from e
        if isinstance(batch, dict) and batch.get("code"):
            raise DataError(f"Binance error for {symbol} {tf_key}: {batch}")
        if not batch:
            break
        rows.extend(batch)
        last_open = batch[-1][0]
        if last_open <= cur:
            break
        cur = last_open + 1
        if len(batch) < 1000:
            break

    if not rows:
        raise DataError(f"Binance returned no candles for {symbol} {tf_key} in range")

    df = pd.DataFrame(rows, columns=_KLINE_COLS)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    df = (df[["open_time", "open", "high", "low", "close", "volume"]]
          .drop_duplicates("open_time").reset_index(drop=True))
    return df

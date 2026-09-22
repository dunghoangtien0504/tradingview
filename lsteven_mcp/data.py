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

# LSteven's own fixed timeframe set (Sach, Chuong 3) is H1·H4·H12·D·3D·W·M —
# the book deliberately skips in-between frames ("cac khung le o giua nhu 2D bi
# bo qua de tranh loan"). The extra frames below are opt-in additions the user
# asked for; CANONICAL marks which ones the method itself sanctions so the UI
# can flag the difference instead of silently blurring it.
CANONICAL = {"H1", "H4", "H12", "D", "3D", "W", "M"}

# Frames Binance serves natively.
TIMEFRAMES: dict[str, str] = {
    "H1": "1h",
    "H2": "2h",
    "H4": "4h",
    "H6": "6h",
    "H12": "12h",
    "D": "1d",
    "3D": "3d",
    "W": "1w",
    "M": "1M",
}

# Frames Binance does NOT serve (3h / 2d / 4d are rejected with "Invalid
# interval"), so they are built here from a base interval.
#   tf_key -> (binance base interval, base candle length in seconds, candles per bucket)
# NOTE: buckets are anchored to the unix epoch by integer division, NOT by
# pandas' resample(origin=...) — that argument is silently ignored for
# day-based rules, which would let bucket boundaries drift depending on how
# much history happened to be fetched.
SYNTHETIC: dict[str, tuple[str, int, int]] = {
    "H3": ("1h", 3600, 3),
    "2D": ("1d", 86400, 2),
    "4D": ("1d", 86400, 4),
}

ALL_TIMEFRAMES = list(TIMEFRAMES) + list(SYNTHETIC)

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


def _resample(df: pd.DataFrame, base_seconds: int, factor: int) -> pd.DataFrame:
    """Build synthetic candles (3h / 2D / 4D) from a smaller native interval.

    Bucket boundaries are anchored to the unix epoch so the same wall-clock
    candle always lands in the same bucket, no matter how much history was
    fetched. A leading partial bucket is dropped (its open/high/low would be
    wrong); the trailing in-progress bucket is kept, matching how Binance
    itself returns a live last candle.
    """
    bucket_len = base_seconds * factor
    # Convert to epoch SECONDS explicitly: pandas' datetime64 unit varies
    # (3.x hands back datetime64[ms] here, 2.x nanoseconds), so dividing a raw
    # astype("int64") by a hardcoded factor silently produces garbage buckets.
    secs = df["open_time"].values.astype("datetime64[s]").astype("int64")
    bucket = secs // bucket_len

    out = (df.assign(_b=bucket)
             .groupby("_b", as_index=False)
             .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                  close=("close", "last"), volume=("volume", "sum"),
                  _n=("open", "size")))
    out["open_time"] = pd.to_datetime(out["_b"] * bucket_len, unit="s", utc=True)

    # drop a leading bucket that is missing candles (partial history)
    if len(out) > 1 and out["_n"].iloc[0] < factor:
        out = out.iloc[1:]

    return out[["open_time", "open", "high", "low", "close", "volume"]].reset_index(drop=True)


def get_klines(symbol: str, tf_key: str, limit: int = 300) -> pd.DataFrame:
    """Fetch the most recent `limit` candles for `symbol` at LSteven timeframe
    `tf_key`. Returns a DataFrame sorted oldest->newest with columns
    open_time, open, high, low, close, volume (floats/Timestamp).

    Synthetic frames (see SYNTHETIC) fetch their base interval and resample.
    """
    tf_key = tf_key.upper()

    if tf_key in SYNTHETIC:
        base_interval, base_seconds, factor = SYNTHETIC[tf_key]
        base_key = next(k for k, v in TIMEFRAMES.items() if v == base_interval)
        base = get_klines(symbol, base_key, limit=min(limit * factor + factor, 1000))
        out = _resample(base, base_seconds, factor)
        if out.empty:
            raise DataError(f"resample produced no candles for {symbol} {tf_key}")
        return out.tail(limit).reset_index(drop=True)

    if tf_key not in TIMEFRAMES:
        raise DataError(f"unknown timeframe {tf_key!r}; use one of {ALL_TIMEFRAMES}")
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

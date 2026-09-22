"""MCP server exposing the LSteven RSI/EMA9/WMA45 reading engine as tools.

Run directly for a smoke test:
    python -m lsteven_mcp.server --selftest
Run as an MCP server (stdio, the normal way a client launches it):
    python -m lsteven_mcp.server
"""
from __future__ import annotations

import sys
from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from . import indicators as ind
from .data import TIMEFRAMES, DataError, get_klines
from .form_trap import detect_forms, detect_traps
from .multiframe import ORDER, read_timeframe, snapshot

mcp = FastMCP(
    name="LSteven Trading Reader",
    instructions=(
        "Doc BTC/crypto theo dung phuong phap LSteven: RSI(14) + EMA9-cua-RSI + "
        "WMA45-cua-RSI, doc theo da khung H1/H4/H12/D/3D/W/M, phat hien Form "
        "buy/sell va Trap (xuat hien / tra trap thanh cong-khong thanh cong / hong). "
        "Day la cong cu ho tro doc chart, khong phai loi khuyen dau tu va khong tu "
        "dong dat lenh."
    ),
)


@mcp.tool()
def multi_timeframe_snapshot(symbol: str = "BTCUSDT") -> dict:
    """Doc toan bo 7 khung (M->W->3D->D->H12->H4->H1) mot luot — dung Bai 20 buoc 1.

    Tra ve cho moi khung: gia dong cua gan nhat, RSI/EMA9/WMA45, RSI dang
    tren/duoi 45, muc luc 1-6, trang thai mat can bang, va co dang trap
    (len/xuong) hay khong. Kem bang dong-thuan giua tung cap khung lien ke.
    """
    return snapshot(symbol)


@mcp.tool()
def get_indicator_series(symbol: str, timeframe: str, limit: int = 90) -> dict:
    """Lay chuoi RSI/EMA9/WMA45 + OHLC gan nhat cho MOT khung, de ve chart
    hoac kiem tra tay.

    Args:
        symbol: cap giao dich Binance, vd "BTCUSDT".
        timeframe: mot trong H1, H4, H12, D, 3D, W, M.
        limit: so nen tra ve (toi da 500).
    """
    limit = max(20, min(limit, 500))
    try:
        df = ind.add_lines(get_klines(symbol, timeframe, limit=limit + 45))
    except DataError as e:
        return {"error": str(e)}
    tail = df.tail(limit)
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe.upper(),
        "candles": [
            {
                "time": str(row.open_time), "close": round(row.close, 2),
                "rsi": None if row.rsi != row.rsi else round(row.rsi, 2),
                "ema9": None if row.ema9 != row.ema9 else round(row.ema9, 2),
                "wma45": None if row.wma45 != row.wma45 else round(row.wma45, 2),
            }
            for row in tail.itertuples()
        ],
    }


@mcp.tool()
def detect_form_events(symbol: str, timeframe: str, lookback: int = 200) -> dict:
    """Tim cac form buy/sell gan day (Bai 4): RSI cat len/xuong EMA9 (diem 2)
    roi cat len/xuong WMA45 (diem 3), kem diem 1 (day/dinh RSI) tim nguoc lai.
    """
    try:
        df = ind.add_lines(get_klines(symbol, timeframe, limit=max(lookback + 60, 120)))
    except DataError as e:
        return {"error": str(e)}
    events = detect_forms(df, lookback=lookback)
    return {
        "symbol": symbol.upper(), "timeframe": timeframe.upper(),
        "count": len(events),
        "events": [asdict(e) for e in events],
    }


@mcp.tool()
def detect_trap_events(symbol: str, timeframe: str, lookback: int = 400) -> dict:
    """Tim cac vung Trap gan day (RSI<20 hoac >80) va cach chung ket thuc:
    tra_thanh_cong / tra_khong_thanh_cong / hong / dang_dien_ra (Bai 10-11).
    """
    try:
        df = ind.add_lines(get_klines(symbol, timeframe, limit=max(lookback + 90, 150)))
    except DataError as e:
        return {"error": str(e)}
    episodes = detect_traps(df, lookback=lookback)
    return {
        "symbol": symbol.upper(), "timeframe": timeframe.upper(),
        "count": len(episodes),
        "episodes": [asdict(e) for e in episodes],
    }


@mcp.tool()
def check_dong_thuan(symbol: str, tf_a: str, tf_b: str) -> dict:
    """Kiem tra dong thuan giua 2 khung bat ky (Bai 8): cung tren/duoi 45,
    va so sanh muc luc. Dung khi muon biet hai khung "lien ke" co thuan
    tien de choi hay khong (khong bat buoc phai lien ke trong bang ORDER).
    """
    try:
        _, ra = read_timeframe(symbol, tf_a)
        _, rb = read_timeframe(symbol, tf_b)
    except DataError as e:
        return {"error": str(e)}
    return {
        "symbol": symbol.upper(),
        "a": asdict(ra), "b": asdict(rb),
        "dong_thuan": ra.above_45 == rb.above_45,
        "ghi_chu": (
            "Dong thuan = hai khung cung phe (cung tren hoac cung duoi 45). "
            "Day la dieu kien toi thieu de choi (Bai 8) — khong can du moi khung."
        ),
    }


@mcp.resource("lsteven://timeframes")
def timeframes_resource() -> str:
    """The fixed timeframe set the method reads, and their Binance intervals."""
    return "\n".join(f"{k} -> {v}" for k, v in TIMEFRAMES.items())


def _selftest() -> None:
    print("Self-test: fetching BTCUSDT multi-timeframe snapshot...", file=sys.stderr)
    snap = snapshot("BTCUSDT")
    for tf in ORDER:
        r = snap["readings"].get(tf)
        if r:
            print(f"  {tf:>3}: close={r['price']:<10} rsi={r['rsi']:<6} "
                  f"ema9={r['ema9']:<6} wma45={r['wma45']:<6} "
                  f"muc_luc={r['muc_luc']} trap={r['active_trap']}", file=sys.stderr)
        else:
            print(f"  {tf:>3}: ERROR {snap['errors'].get(tf)}", file=sys.stderr)
    print("dong_thuan_ke_nhau:", snap["dong_thuan_ke_nhau"], file=sys.stderr)

    print("\nSelf-test: trap episodes on BTCUSDT/D (last 400 candles)...", file=sys.stderr)
    ev = detect_trap_events("BTCUSDT", "D", 400)
    for e in ev.get("episodes", []):
        print(f"  {e['direction']:>4} {e['start_time'][:10]} -> {e['end_time'][:10]} "
              f"extreme={e['extreme_rsi']:.1f} status={e['status']}", file=sys.stderr)

    print("\nSelf-test OK.", file=sys.stderr)


def main() -> None:
    if "--selftest" in sys.argv:
        _selftest()
        return
    mcp.run()


if __name__ == "__main__":
    main()

"""Lop 3: backtest mot tap luat CO HOC HOA don gian, tren du lieu that.

KHONG phai ban sao day du phuong phap LSteven — phuong phap that doi hoi
doc da khung + xa/gan + gu ca nhan, thu nay khong the may moc hoa het (da
noi ro trong README). Day la mot tap luat RUT GON, chi dung phan co cong
thuc/dieu kien ro rang:

  VAO:  Form buy diem 3 hoan thanh (RSI cat len WMA45 sau khi da cat len
        EMA9) tren MOT khung co dinh -> vao LONG o gia MO CUA cay ke tiep
        (dung nguyen tac Bai 14: doi dong nen, vao o cay sau).
        (huong "both" them Form sell -> SHORT, nhung Bai 18 canh bao danh
        xuong kho hon nhieu — mac dinh chi long).
  SL:   day thap nhat trong N cay truoc luc vao (xap xi "day gan nhat"
        cua Bai 17). KHONG BAO GIO noi rong sau khi vao.
  KHOI LUONG: dung dung cong thuc 2% (Bai 17), tinh lai theo equity hien
        tai truoc moi lenh (compounding).
  RA:   tin hieu doi chieu (Form sell diem 3 xuat hien) HOAC gia cham SL,
        cai nao truoc. KHONG dat take-profit (dung Bai 16).

Day la cong cu do luong mot tap luat DON GIAN, khong phai loi khuyen dau
tu, khong dung de tu dong dat lenh that.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict

import pandas as pd

from . import indicators as ind
from .data import get_klines, get_klines_extended
from .form_trap import detect_forms


@dataclass
class Trade:
    direction: str
    entry_time: str
    entry_price: float
    sl_price: float
    exit_time: str | None = None
    exit_price: float | None = None
    exit_reason: str | None = None   # "tin_hieu_doi_chieu" | "SL"
    position_usd: float | None = None
    pnl_usd: float | None = None
    r_multiple: float | None = None  # pnl / so tien rui ro ban dau (2% equity luc vao)


def _position_size(equity: float, entry: float, sl: float, risk_pct: float) -> tuple[float, float]:
    sl_pct = abs(entry - sl) / entry
    risk_usd = equity * (risk_pct / 100.0)
    return risk_usd, risk_usd / sl_pct


def run_backtest(symbol: str, timeframe: str, limit: int = 1000, start: str | None = None,
                  initial_equity: float = 1000.0, risk_pct: float = 2.0,
                  sl_lookback: int = 20, direction: str = "long_only",
                  commission_pct: float = 0.05) -> dict:
    """`start` (vd "2019-01-01") lay lich su dai qua nhieu request, bo qua
    gioi han 1000 nen/lan cua Binance — dung cho backtest nhieu nam. Neu
    khong dua `start`, dung `limit` nen gan nhat (nhanh, du cho test nhanh).
    """
    raw = get_klines_extended(symbol, timeframe, start) if start else get_klines(symbol, timeframe, limit=limit)
    df = ind.add_lines(raw)
    events = detect_forms(df, lookback=len(df))
    events.sort(key=lambda e: e.diem3_time)

    times = df["open_time"].astype(str).tolist()
    idx_of = {t: i for i, t in enumerate(times)}
    opens = df["open"].to_numpy()
    lows = df["low"].to_numpy()
    highs = df["high"].to_numpy()

    equity = initial_equity
    equity_curve = [{"time": times[0], "equity": equity}]
    trades: list[Trade] = []
    open_trade: Trade | None = None

    def _sl_for(entry_i: int, side: str) -> float:
        lo = max(0, entry_i - sl_lookback)
        if side == "buy":
            return float(lows[lo:entry_i].min())
        return float(highs[lo:entry_i].max())

    n = len(df)
    ev_i = 0
    for i in range(1, n):
        # 1) check SL on the open trade using this candle's range
        if open_trade is not None:
            hit_sl = (lows[i] <= open_trade.sl_price) if open_trade.direction == "long" \
                else (highs[i] >= open_trade.sl_price)
            if hit_sl:
                _close_trade(open_trade, times[i], open_trade.sl_price, "SL",
                             commission_pct)
                equity += open_trade.pnl_usd
                equity_curve.append({"time": times[i], "equity": round(equity, 2)})
                trades.append(open_trade)
                open_trade = None

        # 2) process any form events whose diem3 candle is `i-1` (signal
        #    confirmed on close of i-1 -> act at open of i, per Bai 14/15)
        while ev_i < len(events) and idx_of.get(events[ev_i].diem3_time) == i - 1:
            e = events[ev_i]
            ev_i += 1
            if open_trade is not None:
                if (open_trade.direction == "long" and e.direction == "sell") or \
                   (open_trade.direction == "short" and e.direction == "buy"):
                    _close_trade(open_trade, times[i], float(opens[i]), "tin_hieu_doi_chieu",
                                 commission_pct)
                    equity += open_trade.pnl_usd
                    equity_curve.append({"time": times[i], "equity": round(equity, 2)})
                    trades.append(open_trade)
                    open_trade = None
                continue  # signal used only to exit; don't also flip-open same candle

            if open_trade is None:
                if e.direction == "buy" and direction in ("long_only", "both"):
                    entry_price = float(opens[i])
                    sl = _sl_for(i, "buy")
                    if sl >= entry_price:
                        continue  # degenerate SL, skip this signal
                    risk_usd, pos = _position_size(equity, entry_price, sl, risk_pct)
                    open_trade = Trade("long", times[i], entry_price, sl, position_usd=pos)
                    open_trade.__dict__["_risk_usd"] = risk_usd
                elif e.direction == "sell" and direction in ("short_only", "both"):
                    entry_price = float(opens[i])
                    sl = _sl_for(i, "sell")
                    if sl <= entry_price:
                        continue
                    risk_usd, pos = _position_size(equity, entry_price, sl, risk_pct)
                    open_trade = Trade("short", times[i], entry_price, sl, position_usd=pos)
                    open_trade.__dict__["_risk_usd"] = risk_usd

    if open_trade is not None:
        _close_trade(open_trade, times[-1], float(df["close"].iloc[-1]), "het_du_lieu",
                     commission_pct)
        equity += open_trade.pnl_usd
        equity_curve.append({"time": times[-1], "equity": round(equity, 2)})
        trades.append(open_trade)

    return _summarize(symbol, timeframe, trades, equity_curve, initial_equity, df)


def _close_trade(t: Trade, exit_time: str, exit_price: float, reason: str, commission_pct: float) -> None:
    sign = 1 if t.direction == "long" else -1
    gross_pct = sign * (exit_price - t.entry_price) / t.entry_price
    fee_pct = commission_pct / 100.0 * 2  # entry + exit
    pnl_usd = t.position_usd * (gross_pct - fee_pct)
    risk_usd = t.__dict__.get("_risk_usd", abs(t.entry_price - t.sl_price) / t.entry_price * t.position_usd)
    t.exit_time, t.exit_price, t.exit_reason = exit_time, exit_price, reason
    t.pnl_usd = round(pnl_usd, 2)
    t.r_multiple = round(pnl_usd / risk_usd, 3) if risk_usd else None


def _summarize(symbol, timeframe, trades: list[Trade], equity_curve, initial_equity, df) -> dict:
    n = len(trades)
    wins = [t for t in trades if t.pnl_usd and t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd and t.pnl_usd <= 0]
    final_equity = equity_curve[-1]["equity"] if equity_curve else initial_equity

    peak = initial_equity
    max_dd = 0.0
    for pt in equity_curve:
        peak = max(peak, pt["equity"])
        dd = (peak - pt["equity"]) / peak if peak else 0
        max_dd = max(max_dd, dd)

    buy_hold_pct = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100

    avg_r = round(sum(t.r_multiple for t in trades if t.r_multiple is not None) / n, 3) if n else None

    return {
        "symbol": symbol.upper(), "timeframe": timeframe.upper(),
        "period": f"{df['open_time'].iloc[0]} -> {df['open_time'].iloc[-1]}",
        "so_lenh": n,
        "thang": len(wins), "thua": len(losses),
        "winrate_pct": round(100 * len(wins) / n, 1) if n else None,
        "trung_binh_R_moi_lenh": avg_r,
        "von_dau": initial_equity,
        "von_cuoi": round(final_equity, 2),
        "loi_nhuan_pct": round((final_equity / initial_equity - 1) * 100, 2),
        "buy_and_hold_pct": round(buy_hold_pct, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "trades": [asdict(t) for t in trades],
        "equity_curve": equity_curve,
    }


def print_report(result: dict) -> None:
    print(f"\n=== Backtest {result['symbol']} {result['timeframe']} ===")
    print(f"Giai doan: {result['period']}")
    print(f"So lenh: {result['so_lenh']}  (thang {result['thang']} / thua {result['thua']}, "
          f"winrate {result['winrate_pct']}%)")
    print(f"Trung binh R/lenh: {result['trung_binh_R_moi_lenh']}")
    print(f"Von: {result['von_dau']} -> {result['von_cuoi']} ({result['loi_nhuan_pct']}%)")
    print(f"Buy & Hold cung giai doan: {result['buy_and_hold_pct']}%")
    print(f"Max drawdown: {result['max_drawdown_pct']}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--timeframe", default="D")
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--start", default=None, help='vd "2019-01-01" — lay ca lich su dai, bo qua --limit')
    ap.add_argument("--equity", type=float, default=1000.0)
    ap.add_argument("--risk-pct", type=float, default=2.0)
    ap.add_argument("--sl-lookback", type=int, default=20)
    ap.add_argument("--direction", choices=["long_only", "short_only", "both"], default="long_only")
    ap.add_argument("--csv", default=None, help="luu trade log ra file CSV")
    args = ap.parse_args()

    result = run_backtest(args.symbol, args.timeframe, args.limit, args.start, args.equity,
                           args.risk_pct, args.sl_lookback, args.direction)
    print_report(result)
    if args.csv:
        pd.DataFrame(result["trades"]).to_csv(args.csv, index=False)
        print(f"Da luu trade log: {args.csv}")


if __name__ == "__main__":
    main()

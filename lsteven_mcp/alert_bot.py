"""Bot canh bao Telegram — Lop 2 trong lo trinh (thuan doc, KHONG dat lenh).

Chay dinh ky (qua Windows Task Scheduler, xem README), moi lan:
  1. Doc snapshot da khung + trap/form gan nhat cho tung symbol trong CONFIG.
  2. So voi lan chay truoc (luu trong state.json) de tim THAY DOI thuc su:
       - mot con Trap vua duoc giai quyet (tra thanh cong / khong thanh cong / hong)
       - mot Form buy/sell vua hoan thanh (diem 3 moi)
       - dong thuan giua 2 khung lien ke vua doi phe
  3. Neu co thay doi -> gui tin nhan Telegram. Khong co gi moi -> im lang,
     khong spam.

An toan: khong can API key san, khong dat lenh, khong giu vi. Chi can
TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID (xem README de lay 2 thu nay).

Chay thu khong can token (in ra thay vi gui):
    python -m lsteven_mcp.alert_bot --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass  # .env optional — TELEGRAM_* co the dat truc tiep bang bien moi truong

# Windows console mac dinh dung cp1252, khong in duoc emoji trong tin nhan.
# Chi anh huong duong in ra man hinh (dry-run) — goi Telegram that van gui
# JSON UTF-8 binh thuong, khong lien quan dong nay.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

from . import indicators as ind
from .data import DataError, get_klines
from .form_trap import detect_forms, detect_traps
from .multiframe import read_timeframe

# ---------------------------------------------------------------- config ---

SYMBOLS = ["BTCUSDT"]
# H1 co tinh nhung bo qua: Bai 18 day ro "lo di tin hieu song be nhu H1/M15
# de keo ky luat len it nhat tu H4 tro len". M bo qua vi qua thua (1 lan/thang).
ALERT_TIMEFRAMES = ["H4", "H12", "D", "3D", "W"]
ADJACENT_PAIRS = [("H4", "H12"), ("H12", "D"), ("D", "3D"), ("3D", "W")]

STATE_FILE = Path(__file__).resolve().parent.parent / "alert_state.json"


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _send_telegram(text: str, dry_run: bool) -> bool:
    """Return True if the message is considered delivered (or dry-run)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if dry_run or not token or not chat_id:
        print("--- (dry-run / thieu token, khong gui that) ---", file=sys.stderr)
        print(text)
        print("--- het tin nhan ---", file=sys.stderr)
        return True
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        if not r.ok:
            print(f"[alert_bot] Telegram loi {r.status_code}: {r.text}", file=sys.stderr)
            return False
        return True
    except requests.RequestException as e:
        print(f"[alert_bot] Telegram request that bai: {e}", file=sys.stderr)
        return False


def _scan_symbol(symbol: str, prev: dict) -> tuple[dict, list[str]]:
    """Return (new_state_for_symbol, list_of_alert_lines)."""
    lines: list[str] = []
    new_state: dict = {"readings": {}, "trap_end": {}, "form_diem3": {}}

    readings = {}
    for tf in ALERT_TIMEFRAMES:
        try:
            df, r = read_timeframe(symbol, tf)
        except DataError as e:
            lines.append(f"⚠️ {symbol} {tf}: loi lay du lieu ({e})")
            continue
        readings[tf] = r
        new_state["readings"][tf] = {"above_45": r.above_45, "muc_luc": r.muc_luc}

        # --- trap resolutions ---
        traps = detect_traps(df, lookback=250)
        resolved = [t for t in traps if t.status != "dang_dien_ra"]
        last_seen_end = prev.get("trap_end", {}).get(tf)
        for t in resolved:
            if t.end_time != last_seen_end and (last_seen_end is None or t.end_time > last_seen_end):
                icon = {"tra_thanh_cong": "✅", "tra_khong_thanh_cong": "〰️", "hong": "❌"}[t.status]
                dir_label = "XUỐNG" if t.direction == "down" else "LÊN"
                lines.append(
                    f"{icon} <b>{symbol} {tf}</b>: Trap {dir_label} vừa kết thúc — "
                    f"<b>{t.status.replace('_', ' ').upper()}</b> (đỉnh/đáy RSI {t.extreme_rsi:.1f}). "
                    f"{t.detail}"
                )
        if resolved:
            new_state["trap_end"][tf] = max(t.end_time for t in resolved)
        elif last_seen_end:
            new_state["trap_end"][tf] = last_seen_end

        # --- new active trap appearing (worth flagging even before resolution) ---
        active = [t for t in traps if t.status == "dang_dien_ra"]
        if active:
            a = active[-1]
            prev_active_start = prev.get("active_trap_start", {}).get(tf)
            if a.start_time != prev_active_start:
                dir_label = "XUỐNG (RSI<20)" if a.direction == "down" else "LÊN (RSI>80)"
                lines.append(f"🟡 <b>{symbol} {tf}</b>: Trap {dir_label} mới xuất hiện, "
                              f"RSI hiện {a.extreme_rsi:.1f}. Chưa hành động — chờ trả/hỏng.")
            new_state.setdefault("active_trap_start", {})[tf] = a.start_time
        else:
            new_state.setdefault("active_trap_start", {})[tf] = None

        # --- form events (diem 3) ---
        forms = detect_forms(df, lookback=150)
        last_diem3 = prev.get("form_diem3", {}).get(tf)
        for f in forms:
            if f.diem3_time != last_diem3 and (last_diem3 is None or f.diem3_time > last_diem3):
                icon = "🟢" if f.direction == "buy" else "🔴"
                lines.append(
                    f"{icon} <b>{symbol} {tf}</b>: Form {f.direction.upper()} vừa hoàn thành điểm 3 "
                    f"(RSI cắt lên đỏ tại RSI={f.diem3_rsi:.1f})."
                )
        if forms:
            new_state["form_diem3"][tf] = max(f.diem3_time for f in forms)
        elif last_diem3:
            new_state["form_diem3"][tf] = last_diem3

    # --- dong thuan flips between adjacent pairs ---
    for a, b in ADJACENT_PAIRS:
        if a in readings and b in readings:
            now_dt = readings[a].above_45 == readings[b].above_45
            key = f"{a}-{b}"
            prev_dt = prev.get("dong_thuan", {}).get(key)
            new_state.setdefault("dong_thuan", {})[key] = now_dt
            if prev_dt is not None and prev_dt != now_dt:
                trang_thai = "ĐỒNG THUẬN" if now_dt else "KHÔNG còn đồng thuận"
                lines.append(f"🔵 <b>{symbol}</b>: cặp {a}-{b} vừa chuyển sang {trang_thai}.")

    return new_state, lines


def run_once(dry_run: bool = False) -> None:
    state = _load_state()
    all_lines: list[str] = []
    new_state: dict = {}

    for symbol in SYMBOLS:
        is_first_run = symbol not in state
        prev_sym = state.get(symbol, {})
        sym_state, lines = _scan_symbol(symbol, prev_sym)
        new_state[symbol] = sym_state
        if is_first_run:
            # Dung lich su lam bien: dung bao "vua xay ra" cho nhung thu da
            # xay ra tu truoc khi bot bat dau chay lan dau.
            print(f"[{symbol}] lan chay dau tien, thiet lap baseline, khong gui canh bao.",
                  file=sys.stderr)
        else:
            all_lines.extend(lines)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if all_lines:
        header = f"📡 <b>LSteven Alert</b> — {ts}\n"
        ok = _send_telegram(header + "\n".join(all_lines), dry_run)
        if not ok:
            # Dung luu state moi — de lan chay sau phat hien lai cung thay doi
            # nay va thu gui lai, thay vi mat canh bao vinh vien.
            print("[alert_bot] gui that bai, GIU state cu de thu lai lan sau.", file=sys.stderr)
            return
    else:
        print(f"[{ts}] khong co gi moi, khong gui.", file=sys.stderr)

    _save_state(new_state)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                     help="In ra console thay vi goi Telegram that (khong can token)")
    ap.add_argument("--reset-state", action="store_true",
                     help="Xoa state cu truoc khi chay (lan dau nen dung, tranh spam toan bo lich su)")
    args = ap.parse_args()

    if args.reset_state and STATE_FILE.exists():
        STATE_FILE.unlink()

    run_once(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

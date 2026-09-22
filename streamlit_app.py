"""LSteven Cockpit — dashboard doc chart + nhat ky, bao quanh lsteven_mcp.

Chay:  streamlit run streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

from lsteven_mcp import journal
from lsteven_mcp.data import DataError
from lsteven_mcp.form_trap import detect_forms, detect_traps
from lsteven_mcp.indicators import add_lines
from lsteven_mcp.data import get_klines
from lsteven_mcp.multiframe import ORDER, snapshot
from lsteven_mcp.risk import position_size

st.set_page_config(page_title="LSteven Cockpit", page_icon="📈", layout="wide")

TF_LABEL = {"M": "Tháng", "W": "Tuần", "3D": "3 Ngày", "D": "Ngày",
            "H12": "12h", "H4": "4h", "H1": "1h"}


# ------------------------------------------------------------------ utils --

def _color_for(above_45: bool) -> str:
    return "#1c8f63" if above_45 else "#c9432f"


def _luc_bar(muc_luc: int) -> str:
    filled = "🟩" * muc_luc + "⬜" * (6 - muc_luc)
    return filled


def _summary_sentence(snap: dict) -> str:
    readings = snap["readings"]
    if not readings:
        return "Không lấy được dữ liệu."
    up = [tf for tf, r in readings.items() if r["above_45"]]
    down = [tf for tf, r in readings.items() if not r["above_45"]]
    traps = {tf: r["active_trap"] for tf, r in readings.items() if r["active_trap"]}

    parts = []
    if len(up) == len(readings):
        parts.append("Tất cả các khung đang đọc **LÊN** (RSI trên 45).")
    elif len(down) == len(readings):
        parts.append("Tất cả các khung đang đọc **XUỐNG** (RSI dưới 45).")
    else:
        parts.append(f"Lên: {', '.join(up) or '—'} · Xuống: {', '.join(down) or '—'} — **các khung đang mâu thuẫn**, đọc kỹ Bài 6/9 trước khi vào.")

    if traps:
        chi_tiet = ", ".join(f"{tf} ({'lên' if d=='up' else 'xuống'})" for tf, d in traps.items())
        parts.append(f"⚠️ Đang có Trap chưa giải quyết ở: {chi_tiet} — đọc theo chiều trap, chưa vội kết luận đảo chiều.")
    return " ".join(parts)


# ------------------------------------------------------------------ pages --

def page_dashboard():
    st.title("📈 LSteven Cockpit — Dashboard")
    st.caption("Không phải lời khuyên đầu tư · Công cụ hỗ trợ đọc chart theo phương pháp LSteven")

    col1, col2 = st.columns([3, 1])
    symbol = col1.text_input("Symbol", value="BTCUSDT").upper().strip()
    refresh = col2.button("🔄 Làm mới", use_container_width=True)

    cache_key = f"snap_{symbol}"
    if refresh or cache_key not in st.session_state:
        with st.spinner("Đang đọc 7 khung..."):
            try:
                st.session_state[cache_key] = snapshot(symbol)
            except Exception as e:
                st.error(f"Lỗi lấy dữ liệu: {e}")
                return
    snap = st.session_state[cache_key]

    if snap.get("errors"):
        st.warning(f"Một vài khung lỗi: {snap['errors']}")

    st.markdown(f"> {_summary_sentence(snap)}")

    st.subheader("Bối cảnh đa khung (Bài 20 bước 1)")
    cols = st.columns(len(ORDER))
    for i, tf in enumerate(ORDER):
        r = snap["readings"].get(tf)
        with cols[i]:
            if not r:
                st.markdown(f"**{tf}**\n\n_lỗi_")
                continue
            color = _color_for(r["above_45"])
            arrow = "▲" if r["above_45"] else "▼"
            trap_badge = ""
            if r["active_trap"] == "up":
                trap_badge = "🟡 TRAP LÊN"
            elif r["active_trap"] == "down":
                trap_badge = "🟡 TRAP XUỐNG"
            st.markdown(
                f"<div style='text-align:center;border:1px solid #33261;border-radius:10px;padding:10px'>"
                f"<div style='font-weight:700'>{tf} · {TF_LABEL[tf]}</div>"
                f"<div style='font-size:26px;color:{color}'>{arrow}</div>"
                f"<div style='font-size:12px;color:#888'>RSI {r['rsi']:.1f}</div>"
                f"<div>{_luc_bar(r['muc_luc'])}</div>"
                f"<div style='font-size:11px'>{trap_badge}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.subheader("Đồng thuận giữa các khung liền kề (Bài 8)")
    dt = snap.get("dong_thuan_ke_nhau", {})
    if dt:
        cols2 = st.columns(len(dt))
        for i, (pair, ok) in enumerate(dt.items()):
            cols2[i].metric(pair, "✅ Đồng thuận" if ok else "❌ Lệch phe")

    st.divider()
    st.subheader("Tín hiệu gần nhất")
    tf_pick = st.selectbox("Xem tín hiệu trên khung", ORDER, index=ORDER.index("D"))
    try:
        raw = get_klines(symbol, tf_pick, limit=300)
        df = add_lines(raw)
    except DataError as e:
        st.error(str(e))
        df = None

    if df is not None:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Form buy/sell gần đây**")
            forms = detect_forms(df, lookback=200)
            if forms:
                fdf = pd.DataFrame([{
                    "hướng": f.direction, "điểm 3 (xác nhận)": f.diem3_time[:16],
                    "RSI tại điểm 3": round(f.diem3_rsi, 1),
                } for f in forms[-8:][::-1]])
                st.dataframe(fdf, hide_index=True, use_container_width=True)
            else:
                st.caption("Chưa có form nào trong lookback.")
        with c2:
            st.markdown("**Trap gần đây**")
            traps = detect_traps(df, lookback=300)
            if traps:
                tdf = pd.DataFrame([{
                    "hướng": t.direction, "bắt đầu": t.start_time[:10],
                    "trạng thái": t.status, "RSI cực trị": round(t.extreme_rsi, 1),
                } for t in traps[-8:][::-1]])
                st.dataframe(tdf, hide_index=True, use_container_width=True)
            else:
                st.caption("Chưa có trap nào trong lookback.")

    st.divider()
    st.subheader("Tính khối lượng — công thức 2% (Bài 17)")
    c1, c2, c3, c4 = st.columns(4)
    equity = c1.number_input("Vốn (USD)", min_value=0.0, value=1000.0, step=50.0)
    entry = c2.number_input("Giá vào", min_value=0.0, value=float(snap["readings"].get("D", {}).get("price", 0) or 0))
    sl = c3.number_input("Giá SL", min_value=0.0, value=0.0)
    risk_pct = c4.number_input("% rủi ro/kế hoạch", min_value=0.1, max_value=10.0, value=2.0, step=0.1)
    if entry and sl and entry != sl:
        res = position_size(equity, entry, sl, risk_pct)
        if "error" not in res:
            m1, m2, m3 = st.columns(3)
            m1.metric("Chiều", res["direction"])
            m2.metric("Khối lượng tối đa", f"${res['khoi_luong_toi_da_usd']:,.0f}")
            m3.metric("Mất tối đa nếu SL", f"${res['so_tien_cho_phep_mat_usd']:,.0f}")
            st.caption("Đây là mức TỐI ĐA — build dần từ khung nhỏ lên lớn (Bài 15), không vào hết một lần.")


def page_journal():
    st.title("📓 Nhật ký giao dịch")
    st.caption("Đúng khuôn Bài 20 — ghi trước khi vào, không giải thích ngược sau khi biết kết quả.")

    s = journal.stats()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng số lệnh", s["tong_so_lenh"])
    m2.metric("Đang mở", s["dang_mo"])
    m3.metric("Winrate (đã đóng)", f"{s['winrate_pct']}%" if s["winrate_pct"] is not None else "—")
    m4.metric("Tổng P&L", f"${s['tong_pnl_usd']:,.2f}")

    with st.expander("➕ Thêm lệnh mới", expanded=s["tong_so_lenh"] == 0):
        with st.form("new_trade"):
            c1, c2, c3 = st.columns(3)
            symbol = c1.text_input("Symbol", value="BTCUSDT")
            khung = c2.selectbox("Khung chơi", ORDER, index=ORDER.index("D"))
            huong = c3.selectbox("Hướng", ["long", "short"])
            boi_canh = st.text_area("Bối cảnh đa khung (dán từ Dashboard)", height=80)
            ly_do = st.text_input("Lý do vào (form gì / khung nào / trap gì)")
            c4, c5, c6 = st.columns(3)
            entry = c4.number_input("Giá vào", min_value=0.0, value=0.0)
            sl = c5.number_input("Giá SL", min_value=0.0, value=0.0)
            khoi_luong = c6.number_input("Khối lượng (USD)", min_value=0.0, value=0.0)
            ghi_chu = st.text_input("Ghi chú")
            if st.form_submit_button("Lưu"):
                journal.add_trade(symbol=symbol.upper(), khung_choi=khung, huong=huong,
                                   boi_canh_da_khung=boi_canh, ly_do=ly_do,
                                   entry_price=entry or None, sl_price=sl or None,
                                   khoi_luong_usd=khoi_luong or None, ghi_chu=ghi_chu)
                st.success("Đã lưu.")
                st.rerun()

    st.subheader("Danh sách lệnh")
    trades = journal.list_trades()
    if not trades:
        st.info("Chưa có lệnh nào.")
        return

    for t in trades:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            c1.markdown(f"**{t['symbol']} · {t['khung_choi']} · {t['huong']}**  \n{t['created_at'][:16]}")
            c2.markdown(f"Entry {t['entry_price']} → SL {t['sl_price']}  \nKL: {t['khoi_luong_usd']}")
            c3.markdown(f"_{t['ly_do'] or ''}_")
            new_status = c4.selectbox("Kết quả", ["dang_mo", "thang", "thua", "hoa"],
                                       index=["dang_mo", "thang", "thua", "hoa"].index(t["ket_qua"]),
                                       key=f"status_{t['id']}")
            if new_status != t["ket_qua"]:
                journal.update_trade(t["id"], ket_qua=new_status)
                st.rerun()
            if t["boi_canh_da_khung"]:
                with st.expander("Bối cảnh lúc vào"):
                    st.write(t["boi_canh_da_khung"])
            if st.button("🗑️ Xoá", key=f"del_{t['id']}"):
                journal.delete_trade(t["id"])
                st.rerun()


# ------------------------------------------------------------------ main --

st.sidebar.title("LSteven Cockpit")
page = st.sidebar.radio("Trang", ["📈 Dashboard", "📓 Nhật ký"])
st.sidebar.divider()
st.sidebar.caption("Dữ liệu: Binance public API · Không lưu vị thế trên sàn nào · "
                    "Không phải lời khuyên đầu tư.")

if page == "📈 Dashboard":
    page_dashboard()
else:
    page_journal()

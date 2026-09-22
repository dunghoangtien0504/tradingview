"""Nhan dinh theo tung khung — doc trang thai + kich ban dieu kien.

QUAN TRONG — day KHONG phai du bao gia. Bai 1 cua giao trinh noi thang:
"khong bao gio doan truoc gia se di den dau... chi phan ung khi thi truong
phat tin hieu". Vi vay module nay khong tra ve "gia se len/xuong bao nhieu".
No tra ve dung ba thu ma phuong phap cho phep noi:

  1. Hien tai dang doc la gi (len/xuong/cho) va dang o giai doan nao cua song
  2. Dieu kien gi se XAC NHAN huong do di tiep
  3. Dieu kien gi se HUY doc do

Do la dung khuon "ke hoach dieu kien" cua Bai 20 ("neu H12 len form buy thi
buy truoc o H12 du H4 con trap"), khong phai loi tien tri.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Assessment:
    bias: str                       # "LEN" | "XUONG" | "CHO"
    bias_label: str
    giai_doan: str                  # "moi_di" | "nua_duong" | "gan_cuoi" | "chum"
    giai_doan_label: str
    do_mo_rong: str                 # "chum" | "dang_gian" | "gian_cuc_dai"
    tom_tat: str
    xac_nhan: list[str] = field(default_factory=list)
    huy: list[str] = field(default_factory=list)
    luu_y: list[str] = field(default_factory=list)


def _spread_state(df: pd.DataFrame, lookback: int = 40) -> tuple[str, float]:
    """Do mo rong cua 3 duong (Bai 5 + Nang cao muc 1): moi tach = moi di,
    gian cuc dai = da di xa/gan cuoi, chum lai = sap breakout."""
    sub = df[["rsi", "ema9", "wma45"]].dropna().tail(lookback)
    if len(sub) < 5:
        return "dang_gian", 0.5
    spread = sub.max(axis=1) - sub.min(axis=1)
    cur = float(spread.iloc[-1])
    lo, hi = float(spread.min()), float(spread.max())
    pct = (cur - lo) / ((hi - lo) or 1)
    if pct >= 0.78:
        return "gian_cuc_dai", pct
    if pct <= 0.28:
        return "chum", pct
    return "dang_gian", pct


def _candles_since_cross(df: pd.DataFrame, col_a: str, col_b: str, limit: int = 60) -> int | None:
    """So nen ke tu lan cuoi col_a cat qua col_b. None neu khong tim thay."""
    sub = df[[col_a, col_b]].dropna().tail(limit)
    if len(sub) < 3:
        return None
    above = (sub[col_a] > sub[col_b]).to_numpy()
    for i in range(len(above) - 1, 0, -1):
        if above[i] != above[i - 1]:
            return len(above) - 1 - i
    return None


def assess(df: pd.DataFrame, reading) -> Assessment:
    """`reading` la mot TFReading (xem multiframe.py)."""
    rsi, ema9, wma45 = reading.rsi, reading.ema9, reading.wma45
    trap = reading.active_trap
    mo_rong, _pct = _spread_state(df)
    since_45 = _candles_since_cross(df, "rsi", "wma45")
    since_ema = _candles_since_cross(df, "rsi", "ema9")

    # ---- bias: con trap thi doc theo chieu trap (Bai 10) ----
    if trap == "up":
        bias, bias_label = "LEN", "Còn trap lên → vẫn đọc LÊN"
    elif trap == "down":
        bias, bias_label = "XUONG", "Còn trap xuống → vẫn đọc XUỐNG"
    elif rsi > wma45:
        bias, bias_label = "LEN", "RSI trên đường đỏ → đọc LÊN"
    elif rsi < wma45:
        bias, bias_label = "XUONG", "RSI dưới đường đỏ → đọc XUỐNG"
    else:
        bias, bias_label = "CHO", "RSI đang bám sát đường đỏ → chưa rõ"

    # ---- giai doan / xa-gan (Bai 7, cp2) ----
    if mo_rong == "chum":
        giai_doan, gd_label = "chum", "Ba đường chụm — sắp breakout"
    elif since_45 is not None and since_45 <= 4:
        giai_doan, gd_label = "moi_di", "Mới đi (RSI vừa cắt đường đỏ)"
    elif mo_rong == "gian_cuc_dai":
        giai_doan, gd_label = "gan_cuoi", "Giãn cực đại — đã đi xa, gần cuối"
    else:
        giai_doan, gd_label = "nua_duong", "Nửa đường"

    xac_nhan: list[str] = []
    huy: list[str] = []
    luu_y: list[str] = []

    # ---- kich ban theo trang thai ----
    if trap == "down":
        xac_nhan.append("RSI cuộn lên cắt EMA9 (điểm 2), rồi cắt lên WMA45 (điểm 3) = trả trap xong")
        xac_nhan.append("Ba đường phải giãn nở rồi thu lại — chỉ cắt một lần là chưa đủ")
        huy.append("RSI bật thẳng lên ≥70 mà không kịp tạo form = hỏng trap → đứng ngoài chờ")
        luu_y.append("SL phải đặt DƯỚI vùng đáy trap — trả trap thường quét xuống rồi mới bật")
    elif trap == "up":
        xac_nhan.append("RSI cuộn xuống cắt EMA9, rồi cắt xuống WMA45 = trả trap xong")
        huy.append("RSI rơi thẳng về ≤30 mà không tạo form = hỏng trap → đứng ngoài chờ")
        luu_y.append("Neo lâu ở vùng 70-80 vẫn là còn hiệu lực — đừng bán chỉ vì \"quá mua\"")
    elif giai_doan == "chum":
        xac_nhan.append("Đà breakout phải DUY TRÌ sau khi nến đóng")
        huy.append("Vừa đẩy đã xìu về → breakout hỏng, thoát")
        luu_y.append("Chụm ≈ 50-50: sai thì SL rất ngắn, đúng thì ăn cả con sóng")
    elif bias == "LEN":
        xac_nhan.append("RSI giữ được trên WMA45 khi đóng nến kế tiếp")
        xac_nhan.append("Ba đường giãn rộng thêm theo chiều lên")
        huy.append("RSI cắt xuống lại WMA45 (form sell điểm 3) ở khung này")
    elif bias == "XUONG":
        xac_nhan.append("RSI giữ dưới WMA45 khi đóng nến kế tiếp")
        huy.append("RSI cắt lên lại WMA45 (form buy điểm 3) ở khung này")

    if giai_doan == "gan_cuoi":
        luu_y.append("Đã giãn cực đại → canh chốt bằng khung nhỏ hơn 1-2 bậc, đừng nhắm xa")
    if giai_doan == "moi_di":
        luu_y.append("Mới đi → được phép nhắm xa, ra muộn (quy tắc xa/gần, cp2)")

    if since_ema is not None and since_ema <= 2:
        luu_y.append("Vừa cắt đường vàng (\"ting ting\") — chuông báo sớm, CHƯA phải lệnh")

    if reading.imbalance_candles and reading.imbalance_candles >= 20:
        phia = "dưới" if reading.imbalance_side == "below" else "trên"
        doi = "trên" if reading.imbalance_side == "below" else "dưới"
        luu_y.append(
            f"Mất cân bằng: RSI nằm phía {phia} đường WMA45 đã {reading.imbalance_candles} nến "
            f"→ vùng trống phía {doi} là mục tiêu (Bài 9)"
        )

    tom_tat = f"{bias_label}. {gd_label}."
    return Assessment(
        bias=bias, bias_label=bias_label,
        giai_doan=giai_doan, giai_doan_label=gd_label,
        do_mo_rong=mo_rong, tom_tat=tom_tat,
        xac_nhan=xac_nhan, huy=huy, luu_y=luu_y,
    )

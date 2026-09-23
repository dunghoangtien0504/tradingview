"""Tong hop nhom khung (Lon / Trung / Nho) + ke hoach — gop nhieu khung da
doc o multiframe.py thanh MOT khuyen nghi, theo dung cach Bai 6/8/18 doc
"bo canh da khung roi moi ra ke hoach", khong phai them mot cach doc gia moi.

Quy tac gan LEN/XUONG/GIUA cho tung khung (rieng bang nay, don gian hoa de
gop nhom): RSI nam CUNG PHIA voi CA HAI duong EMA9 va WMA45 -> LEN/XUONG ro;
RSI nam GIUA hai duong (bat ke thu tu) -> GIUA, tuc dang o "diem 2" cua Bai 4
(da cat mot duong, chua cat duong con lai) - chua xac nhan xong form.

Nhom khung theo dung tinh than "khung lon quyet huong, khung nho canh diem
vao" cua Bai 6/Bai 20, dung 16 khung da co san trong ORDER (khong fetch them):
  KHUNG LON   (huong)     : M, W, 4D, 3D, 2D, D
  KHUNG TRUNG               : H12, H8, H6, H4, H3, H2, H1
  KHUNG NHO   (thoi diem)  : M30, M15, M5

CANH BAO rieng cho nhom Nho: M30/M15/M5 nam duoi ca san H1/M15 ma Bai 18 da
noi ro la nen "lo di de giu ky luat" — nhom nay chi de xem thoi diem vao/thoat
trong ke hoach da duoc khung lon+trung xac nhan, KHONG dung de tu quyet dinh
huong.
"""
from __future__ import annotations

from dataclasses import dataclass, field

NHOM: dict[str, list[str]] = {
    "lon": ["M", "W", "4D", "3D", "2D", "D"],
    "trung": ["H12", "H8", "H6", "H4", "H3", "H2", "H1"],
    "nho": ["M30", "M15", "M5"],
}
NHOM_LABEL = {"lon": "Khung lớn (hướng)", "trung": "Khung trung", "nho": "Khung nhỏ (thời điểm)"}


def classify_simple(rsi: float, ema9: float, wma45: float) -> str:
    """"len" | "xuong" | "giua" — RSI cung phia ca hai duong = ro; nam giua
    hai duong = chua ro (diem 2, Bai 4)."""
    if rsi > ema9 and rsi > wma45:
        return "len"
    if rsi < ema9 and rsi < wma45:
        return "xuong"
    return "giua"


@dataclass
class NhomRow:
    timeframe: str
    rsi: float
    ema9: float
    wma45: float
    trang_thai: str  # "len" | "xuong" | "giua"
    canonical: bool


@dataclass
class NhomKhung:
    key: str
    label: str
    rows: list[NhomRow]
    trang_thai: str          # "len" | "xuong" | "giua" — bieu quyet da so
    so_len: int
    so_xuong: int
    so_giua: int


@dataclass
class TongHop:
    nhom: dict[str, NhomKhung]
    khuyen_nghi: str         # cau ngan, vd "CHO SHORT / DUNG NGOAI"
    huong_de_xuat: str       # "LEN" | "XUONG" | "CHO"
    bullets: list[str] = field(default_factory=list)


def _vote(rows: list[NhomRow]) -> tuple[str, int, int, int]:
    n_len = sum(1 for r in rows if r.trang_thai == "len")
    n_xuong = sum(1 for r in rows if r.trang_thai == "xuong")
    n_giua = sum(1 for r in rows if r.trang_thai == "giua")
    if n_len > n_xuong and n_len > n_giua:
        state = "len"
    elif n_xuong > n_len and n_xuong > n_giua:
        state = "xuong"
    else:
        state = "giua"
    return state, n_len, n_xuong, n_giua


def _plan(nhom: dict[str, NhomKhung]) -> tuple[str, str, list[str]]:
    lon, trung, nho = nhom["lon"].trang_thai, nhom["trung"].trang_thai, nhom["nho"].trang_thai
    bullets: list[str] = []

    # Ca 3 dong thuan mot chieu (Bai 6/8: dong thuan cang nhieu khung cang chac)
    if lon == trung == nho and lon in ("len", "xuong"):
        huong = lon
        ten = "LÊN" if huong == "len" else "XUỐNG"
        khuyen_nghi = f"ĐI THEO {ten} — đồng thuận cả 3 nhóm"
        bullets.append(f"Khung lớn, khung trung, khung nhỏ đều đọc {ten} — đồng thuận hiếm, độ tin cậy cao (Bài 8).")
        bullets.append("Vẫn chờ form/trap xác nhận đúng khung định vào trước khi vào lệnh — đồng thuận không thay thế điểm vào (Bài 20).")
        return khuyen_nghi, huong, bullets

    # Lon va Trung dong thuan mot chieu, Nho nguoc lai -> hoi ky thuat, khong phai dao chieu
    if lon == trung and lon in ("len", "xuong") and nho != "giua" and nho != lon:
        ten_lon = "LÊN" if lon == "len" else "XUỐNG"
        ten_nho = "LÊN" if nho == "len" else "XUỐNG"
        phia_cho = "SHORT" if lon == "xuong" else "LONG"
        khuyen_nghi = f"CHỜ {phia_cho} / ĐỨNG NGOÀI"
        bullets.append(f"Trend khung lớn {ten_lon} + khung nhỏ đang {ten_nho.lower()} → nhiều khả năng là hồi kỹ thuật, không phải đảo chiều.")
        bullets.append(f"Đừng đuổi lệnh {phia_cho.lower()} ngay tại đáy/đỉnh hồi; chờ khung nhỏ đi hết nhịp hồi rồi khi khung trung quay đầu lại theo {ten_lon.lower()} mới build {phia_cho.lower()}.")
        huong_doi = "LÊN" if lon == "xuong" else "XUỐNG"
        bullets.append(f"Chỉ đảo sang {('LONG' if lon == 'xuong' else 'SHORT')} khi khung lớn (3D/D) tự nó tạo form {'buy' if lon == 'xuong' else 'sell'} + trap {huong_doi.lower()} — không đảo chỉ vì khung nhỏ nảy lên.")
        return khuyen_nghi, "CHO", bullets

    # Lon va Trung mau thuan nhau -> chua ro, dung ngoai
    if lon in ("len", "xuong") and trung in ("len", "xuong") and lon != trung:
        khuyen_nghi = "ĐỨNG NGOÀI — khung lớn và khung trung mâu thuẫn"
        bullets.append("Khung lớn và khung trung đang đọc ngược chiều nhau — theo Bài 18, đây là lúc dễ vào lệnh sai nhất.")
        bullets.append("Chờ một trong hai nhóm đổi chiều để đồng thuận trở lại rồi mới lên kế hoạch, thay vì đoán bên nào thắng.")
        return khuyen_nghi, "CHO", bullets

    # Bat ky nhom nao dang "giua" nhieu -> con dang hinh thanh, chua co form ro
    khuyen_nghi = "ĐỨNG NGOÀI — tín hiệu chưa đủ rõ"
    if lon == "giua":
        bullets.append("Khung lớn đang ở \"điểm 2\" (RSI kẹp giữa EMA9 và WMA45) — hướng chính chưa xác nhận, chưa nên định hướng lệnh.")
    if trung == "giua":
        bullets.append("Khung trung đang ở \"điểm 2\" — chưa có form rõ để canh điểm vào.")
    if nho == "giua" and lon != "giua" and trung != "giua":
        bullets.append("Khung nhỏ đang lưng chừng — chưa phải lúc vào, cứ để khung lớn/trung dẫn hướng trước.")
    if not bullets:
        bullets.append("Các nhóm khung chưa đồng thuận đủ rõ để ra kế hoạch — đứng ngoài quan sát thêm (Bài 18).")
    return khuyen_nghi, "CHO", bullets


def tong_hop(readings: dict) -> TongHop:
    """`readings` = snap["readings"] tu multiframe.snapshot() (dict tf -> TFReading-nhu-dict hoac object)."""
    nhom: dict[str, NhomKhung] = {}
    for key, tfs in NHOM.items():
        rows: list[NhomRow] = []
        for tf in tfs:
            r = readings.get(tf)
            if r is None:
                continue
            rsi = r["rsi"] if isinstance(r, dict) else r.rsi
            ema9 = r["ema9"] if isinstance(r, dict) else r.ema9
            wma45 = r["wma45"] if isinstance(r, dict) else r.wma45
            canonical = r["canonical"] if isinstance(r, dict) else r.canonical
            rows.append(NhomRow(
                timeframe=tf, rsi=rsi, ema9=ema9, wma45=wma45,
                trang_thai=classify_simple(rsi, ema9, wma45), canonical=canonical,
            ))
        state, n_len, n_xuong, n_giua = _vote(rows)
        nhom[key] = NhomKhung(
            key=key, label=NHOM_LABEL[key], rows=rows, trang_thai=state,
            so_len=n_len, so_xuong=n_xuong, so_giua=n_giua,
        )

    khuyen_nghi, huong, bullets = _plan(nhom)
    return TongHop(nhom=nhom, khuyen_nghi=khuyen_nghi, huong_de_xuat=huong, bullets=bullets)

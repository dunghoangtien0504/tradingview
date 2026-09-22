"""Bai 17's 2% formula, as a pure function shared by the MCP tool and the
Streamlit app — one implementation, two callers, no drift between them.
"""
from __future__ import annotations


def position_size(equity_usd: float, entry_price: float, stop_loss_price: float,
                   risk_pct: float = 2.0) -> dict:
    if equity_usd <= 0 or entry_price <= 0 or stop_loss_price <= 0:
        return {"error": "equity_usd, entry_price, stop_loss_price phai > 0"}
    if entry_price == stop_loss_price:
        return {"error": "entry_price va stop_loss_price khong duoc bang nhau"}

    sl_pct = abs(entry_price - stop_loss_price) / entry_price
    risk_usd = equity_usd * (risk_pct / 100.0)
    max_position_usd = risk_usd / sl_pct
    direction = "long (mua)" if stop_loss_price < entry_price else "short (ban)"

    return {
        "direction": direction,
        "sl_khoang_cach_pct": round(sl_pct * 100, 3),
        "so_tien_cho_phep_mat_usd": round(risk_usd, 2),
        "khoi_luong_toi_da_usd": round(max_position_usd, 2),
        "vi_du_vao_30_phan_tram": round(max_position_usd * 0.30, 2),
    }

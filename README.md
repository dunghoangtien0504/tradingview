# lsteven-mcp

MCP server đọc BTC/crypto đúng bộ chỉ báo trong **Phương pháp giao dịch BTC theo xu hướng đa khung (LSteven)**: RSI(14) Wilder + EMA9 và WMA45 tính **trên chính RSI** (không phải trên giá), đọc theo bộ khung cố định `H1 · H4 · H12 · D · 3D · W · M`, có phát hiện **Form buy/sell** (Bài 4) và **Trap** (Bài 10–11: xuất hiện / trả trap thành công / trả trap không thành công / hỏng trap).

Dữ liệu lấy trực tiếp từ **Binance public REST API** (không cần API key). Không đặt lệnh, không kết nối sàn — đây thuần là công cụ đọc chart hỗ trợ quyết định, **không phải lời khuyên đầu tư**.

## Vì sao viết riêng thay vì dùng MCP có sẵn

Các MCP TradingView có sẵn (vd. `tradingview-mcp` của cộng đồng) chỉ trả về chỉ báo chuẩn (RSI thường, MACD…), không tính được đúng tổ hợp **EMA9-của-RSI / WMA45-của-RSI** mà phương pháp này dùng làm cốt lõi. Server này build riêng để khớp 100% với giáo trình.

## Cài đặt

```bash
cd lsteven-mcp
pip install -e .
```

## Kiểm tra nhanh (không cần MCP client)

```bash
python -m lsteven_mcp.server --selftest
```

In ra snapshot đa khung của BTCUSDT + danh sách các đợt Trap gần nhất trên khung D, kèm cách chúng kết thúc.

## Đăng ký làm MCP server cho Claude Code

Thêm vào `.mcp.json` ở gốc project (đã có sẵn file mẫu, xem `../.mcp.json`), rồi khởi động lại phiên Claude Code / reload MCP servers.

## Các tool

| Tool | Việc gì | Khớp bài nào |
|---|---|---|
| `multi_timeframe_snapshot(symbol)` | Đọc cả 7 khung một lượt: giá, RSI/EMA9/WMA45, trên/dưới 45, mức lực 1-6, mất cân bằng, có đang trap không, bảng đồng thuận giữa các khung liền kề | Bài 6, 8, 9, 20 bước 1 |
| `get_indicator_series(symbol, timeframe, limit)` | Chuỗi RSI/EMA9/WMA45 + giá gần nhất của 1 khung, để tự vẽ hoặc kiểm tra tay | Bài 3 |
| `detect_form_events(symbol, timeframe, lookback)` | Các form buy/sell gần đây, kèm điểm 1-2-3 | Bài 4 |
| `detect_trap_events(symbol, timeframe, lookback)` | Các đợt Trap gần đây và cách kết thúc | Bài 10-11 |
| `check_dong_thuan(symbol, tf_a, tf_b)` | So sánh nhanh 2 khung bất kỳ có đồng thuận không | Bài 8 |

## Giới hạn cần biết (đọc trước khi tin số)

- **`muc_luc` (1-6) và `mất cân bằng`** là cách vận hành hoá của người viết cho một mô tả *định tính* trong sách (sách không cho công thức số cụ thể) — xem docstring trong `indicators.py`. Coi là gợi ý, không phải chân lý.
- **`detect_trap_events`** dùng một ngưỡng heuristic ("WMA45 còn cách RSI ≥15 điểm khi RSI chạm 70/30 thì tính là hỏng") để phân biệt *trả trap* và *hỏng trap* — khớp với mọi ví dụ thật đã kiểm chứng tay (COVID crash 2020, đáy 06/2026…) nhưng vẫn là một xấp xỉ, không phải luật tuyệt đối. Sách cũng nói rõ ranh giới này "chỉ biết là một khoảng, không tuyệt đối".
- Đây **không phải** hệ thống tự động vào/ra lệnh. Nó chỉ trả lời "chart đang nói gì" — quyết định vào lệnh, khối lượng, dừng lỗ vẫn theo kỷ luật ở Bài 15-17 của giáo trình.

## Roadmap (chưa build)

Lõi đọc (`indicators.py`, `form_trap.py`, `multiframe.py`) không phụ thuộc gì vào MCP — import thẳng được vào một FastAPI app hoặc một bot để làm dashboard realtime / cảnh báo, khi cần bước đó.

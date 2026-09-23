# lsteven-mcp

MCP server đọc BTC/crypto đúng bộ chỉ báo trong **Phương pháp giao dịch BTC theo xu hướng đa khung (LSteven)**: RSI(14) Wilder + EMA9 và WMA45 tính **trên chính RSI** (không phải trên giá), đọc theo **12 khung**: bộ gốc của phương pháp `H1 · H4 · H12 · D · 3D · W · M` cộng 5 khung mở rộng `H2 · H3 · H6 · 2D · 4D` (được đánh dấu riêng trong giao diện, vì Bài 6 nói rõ bộ gốc cố tình bỏ các khung lẻ ở giữa), có phát hiện **Form buy/sell** (Bài 4) và **Trap** (Bài 10–11: xuất hiện / trả trap thành công / trả trap không thành công / hỏng trap).

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
| `multi_timeframe_snapshot(symbol)` | Đọc cả 12 khung một lượt (tải song song): giá, RSI/EMA9/WMA45, RSI trên/dưới đường WMA45, mức lực 1-6, mất cân bằng, trap, nhận định + kịch bản xác nhận/huỷ, bảng đồng thuận giữa các khung liền kề | Bài 6, 8, 9, 20 bước 1 |
| `get_indicator_series(symbol, timeframe, limit)` | Chuỗi RSI/EMA9/WMA45 + giá gần nhất của 1 khung, để tự vẽ hoặc kiểm tra tay | Bài 3 |
| `detect_form_events(symbol, timeframe, lookback)` | Các form buy/sell gần đây, kèm điểm 1-2-3 | Bài 4 |
| `detect_trap_events(symbol, timeframe, lookback)` | Các đợt Trap gần đây và cách kết thúc | Bài 10-11 |
| `check_dong_thuan(symbol, tf_a, tf_b)` | So sánh nhanh 2 khung bất kỳ có đồng thuận không | Bài 8 |
| `plan_position_size(equity, entry, sl, risk_pct)` | Tính khối lượng tối đa đúng công thức 2% — phần duy nhất trong phương pháp có công thức số 100%, an toàn để máy móc hoá | Bài 17 |

## Giới hạn cần biết (đọc trước khi tin số)

- **`muc_luc` (1-6) và `mất cân bằng`** là cách vận hành hoá của người viết cho một mô tả *định tính* trong sách (sách không cho công thức số cụ thể) — xem docstring trong `indicators.py`. Coi là gợi ý, không phải chân lý.
- **`detect_trap_events`** dùng một ngưỡng heuristic ("WMA45 còn cách RSI ≥15 điểm khi RSI chạm 70/30 thì tính là hỏng") để phân biệt *trả trap* và *hỏng trap* — khớp với mọi ví dụ thật đã kiểm chứng tay (COVID crash 2020, đáy 06/2026…) nhưng vẫn là một xấp xỉ, không phải luật tuyệt đối. Sách cũng nói rõ ranh giới này "chỉ biết là một khoảng, không tuyệt đối".
- Đây **không phải** hệ thống tự động vào/ra lệnh. Nó chỉ trả lời "chart đang nói gì" — quyết định vào lệnh, khối lượng, dừng lỗ vẫn theo kỷ luật ở Bài 15-17 của giáo trình.

## Nhận định theo từng khung (`assess.py`)

Mỗi khung có một khối nhận định gồm: **đọc lên/xuống/chờ**, **giai đoạn** (mới đi / nửa đường / gần cuối / ba đường chụm), **điều kiện xác nhận đi tiếp**, **điều kiện huỷ**, và **lưu ý**.

Đây **không phải dự báo giá**. Bài 1 nói thẳng "không bao giờ đoán trước giá sẽ đi đến đâu", nên module này chỉ trả về đúng thứ phương pháp cho phép nói: hiện đang đọc là gì, và điều kiện nào xác nhận/huỷ cách đọc đó — đúng khuôn kế hoạch điều kiện của Bài 20.

### Khung tự dựng (3h, 2D, 4D)

Binance **không** phục vụ 3 khung này (`Invalid interval`), nên chúng được ghép từ nến 1h/1D. Mốc chia nến neo theo epoch bằng phép chia nguyên — không dùng `resample(origin=...)` của pandas vì tham số đó bị bỏ qua với rule theo ngày, khiến biên nến trôi theo lượng dữ liệu tải về. Đã đối chiếu: nến 2D tự ghép khớp chính xác OHLC của 2 nến D gốc.

## Tổng hợp theo nhóm khung (`tonghop.py`)

Dashboard có thêm một bảng gộp 16 khung thành 3 nhóm — **Khung lớn** (M, W, 4D, 3D, 2D, D), **Khung trung** (H12, H8, H6, H4, H3, H2, H1), **Khung nhỏ** (M30, M15, M5) — mỗi khung được gán nhanh **LÊN / XUỐNG / giữa**: RSI nằm cùng phía cả EMA9 lẫn WMA45 thì rõ hướng, còn nằm *giữa* hai đường (đã cắt một, chưa cắt đường kia) thì là "giữa" — đúng khái niệm "điểm 2" của Bài 4, chưa phải form đã xác nhận.

Từ 3 nhóm đó, mục **Tổng hợp & kế hoạch** tự sinh một khuyến nghị + vài dòng lý do theo đúng logic đồng thuận đa khung của Bài 6/8/18 (không bịa quy tắc mới): cả 3 nhóm cùng chiều thì đi theo chiều đó; khung lớn+trung cùng chiều nhưng khung nhỏ ngược lại thì cảnh báo *hồi kỹ thuật, không phải đảo chiều* và chỉ ra điều kiện mới được đảo; khung lớn/trung mâu thuẫn nhau hoặc còn "giữa" thì khuyến nghị đứng ngoài. Vẫn **không phải dự báo giá** — chỉ là gộp cách đọc, lệnh cụ thể vẫn chờ form/trap xác nhận đúng khung định vào (Bài 20).

⚠️ M30/M15/M5 nằm dưới sàn mà Bài 18 khuyến nghị ("lờ tín hiệu sóng bé như H1/M15 để giữ kỷ luật từ H4 trở lên") — dashboard vẫn hiển thị để canh thời điểm vào/thoát trong một kế hoạch đã được khung lớn+trung xác nhận, nhưng cố tình **không** để nhóm Nhỏ tự quyết định hướng trong logic tổng hợp ở trên.

## Bot cảnh báo Telegram (Lớp 2 — thuần đọc, không đặt lệnh)

Chạy định kỳ, so với lần chạy trước, **chỉ nhắn khi có gì thật sự mới**: một con Trap vừa trả xong (thành công/không thành công/hỏng), một Form vừa hoàn thành điểm 3, hoặc đồng thuận giữa 2 khung liền kề vừa đổi phe. Mặc định theo dõi `H4 · H12 · D · 3D · W` (bỏ H1 và M — Bài 18 dặn "lờ tín hiệu sóng bé như H1/M15 để giữ kỷ luật từ H4 trở lên", còn M quá thưa để cảnh báo).

### 1. Lấy Telegram bot token

1. Mở Telegram, tìm **@BotFather**, gửi `/newbot`, đặt tên tuỳ ý.
2. BotFather trả về một token dạng `123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` — copy lại.

### 2. Lấy chat_id của bạn

1. Nhắn bất kỳ tin gì cho bot vừa tạo (bắt buộc, bot chỉ thấy chat sau khi bạn nhắn trước).
2. Mở trình duyệt vào: `https://api.telegram.org/bot<TOKEN>/getUpdates` (thay `<TOKEN>`).
3. Tìm `"chat":{"id": ...}` trong JSON trả về — đó là `chat_id` (số, có thể âm nếu là group).

### 3. Cấu hình

```bash
cd lsteven-mcp
cp .env.example .env
# mo .env, dien TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID
```

### 4. Chạy thử (không cần token, in ra console)

```bash
python -m lsteven_mcp.alert_bot --dry-run --reset-state   # lan dau: thiet lap baseline, khong gui gi
python -m lsteven_mcp.alert_bot --dry-run                  # lan sau: chi in neu co thay doi that
```

### 5. Chạy thật + lên lịch (Windows Task Scheduler, 30 phút/lần)

```powershell
schtasks /create /tn "LSteven Alert Bot" /tr "\"<đường dẫn python.exe>\" -m lsteven_mcp.alert_bot" ^
  /sc minute /mo 30 /sd 01/01/2020 /st 00:00 /f
```
(Chạy trong thư mục `lsteven-mcp` — hoặc dùng `/tr` với đường dẫn tuyệt đối tới thư mục này làm working directory qua Task Scheduler GUI.)

Xoá lịch: `schtasks /delete /tn "LSteven Alert Bot" /f`

State (những gì bot "đã thấy") lưu ở `alert_state.json`, không commit lên git.

## Backtest (Lớp 3 — đo tập luật, không phải bot)

**Tập luật rút gọn** (không phải toàn bộ phương pháp — xem cảnh báo bên dưới): vào khi Form điểm 3 hoàn thành (mở cửa nến kế tiếp, đúng Bài 14), SL = đáy/đỉnh thấp/cao nhất N nến trước đó, khối lượng đúng công thức 2% Bài 17 (tính lại theo equity mỗi lệnh), ra khi có tín hiệu đảo chiều hoặc dính SL, không take-profit (Bài 16).

```bash
python -m lsteven_mcp.backtest --symbol BTCUSDT --timeframe D --start 2019-01-01 --direction long_only --csv trades.csv
```

Kết quả thật đã chạy (BTCUSDT, 01/2019 – 09/2026, vốn 1000 USD, rủi ro 2%/lệnh):

| Khung | Số lệnh | Winrate | R trung bình | Vốn cuối | Buy&Hold cùng kỳ | Max drawdown |
|---|---|---|---|---|---|---|
| **W** (long only) | 13 | 53.8% | **+0.96R** | 1.261 | 2.374% | **4.3%** |
| **D** (long only) | 140 | 34.3% | +0.30R | 2.176 (+117.6%) | 2.165% | 8.2% |
| **D** (long+short) | 152 | 30.3% | +0.14R | 1.459 (+45.9%) | 2.165% | 26.3% |
| **H4** (long only, từ 2023) | 416 | 26.9% | +0.10R | 1.796 (+79.6%) | 420% | 32.7% |

**Đọc kết quả này thế nào:**
- R trung bình **dương ở mọi khung** dù winrate chỉ 27–54% — đúng tinh thần "thắng ít nhưng ăn nhiều, thua nhiều nhưng lỗ ít" (Bài 19), kể cả với tập luật đã rút gọn tới mức tối thiểu.
- Khung càng lớn, **winrate và chất lượng R càng cao, drawdown càng thấp** (W: 4.3% · D: 8.2% · H4: 32.7%) — khớp chính xác lời dặn Bài 18 "lờ tín hiệu sóng bé, kéo kỷ luật lên từ H4 trở lên". H4 gần 3 năm 416 lệnh mà lãi ròng chỉ hơn 1 nửa so với D 140 lệnh trong 7.7 năm — nhiễu nhiều, chất lượng thấp.
- **Thua xa Buy & Hold** — đừng hiểu lầm đây là "phương pháp dở hơn giữ coin". Giai đoạn 2019–2026 BTC tăng ~21 lần, bất kỳ hệ thống nào ra/vào theo tín hiệu (không cầm xuyên suốt) đều thua hold trong một con bull run mạnh. Cái tập luật này đổi lấy là **drawdown thấp hơn nhiều lần** (8% so với ~80% của việc cầm BTC xuyên qua 2018/2022) — đánh đổi giữa lợi nhuận và biên độ chịu đựng tâm lý, đúng khái niệm Bài 17.
- **13 lệnh trên Weekly là mẫu quá nhỏ** để tin tuyệt đối (R=0.96 đẹp nhưng có thể may mắn) — cần chạy trên nhiều symbol/giai đoạn hơn trước khi kết luận.

⚠️ **Đây KHÔNG phải bằng chứng phương pháp LSteven "work"** — tập luật này chỉ dùng 1 khung, 1 loại tín hiệu (Form), bỏ hoàn toàn phần cốt lõi thật sự của phương pháp: đọc đa khung đồng thời, bồi lệnh theo đồng thuận, xa/gần, và discretion của người trade. Coi đây là **sàn tối thiểu** (nếu phần máy móc hoá được đã dương kỳ vọng, phần discretion làm đúng sẽ còn tốt hơn), không phải trần.

## Dashboard + Nhật ký (FastAPI + HTML/JS — chạy local trên máy bạn)

Cockpit riêng, thiết kế theo hệ thống **Minimalism & Swiss** (dark, `ui-ux-pro-max` design-system search — variance 3, motion 4, density 7): dải 7 khung đọc nhanh kèm **đếm ngược thời gian tới lúc nến đóng** cho từng khung (đúng nguyên tắc Bài 14 "chưa đóng nến thì chưa kết luận" — số liệu chỉ thật sự đổi khi nến đóng, không phải tick giá), đường nối đồng thuận giữa các khung liền kề, tín hiệu Form/Trap gần nhất, máy tính khối lượng 2%, nhật ký giao dịch (SQLite, `journal.db`, không commit), và checklist Quy trình 8 bước (Bài 20) tự reset mỗi ngày.

```bash
cd lsteven-mcp
pip install -e .
uvicorn api:app --reload --port 8787
```

Mở `http://localhost:8787`. Chỉ chạy trên máy bạn — không deploy, không mật khẩu, dữ liệu nhật ký hoàn toàn local. Backend (`api.py`) chỉ bọc mỏng quanh `lsteven_mcp` core, không viết lại logic gì.

File giao diện: `webapp/index.html`, `webapp/styles.css`, `webapp/app.js` — vanilla JS, không build step, không React, dễ chỉnh sửa tay.

Đã test tay toàn bộ luồng trên trình duyệt thật: snapshot BTCUSDT thật, chuyển tab, thêm/sửa trạng thái/xoá lệnh trong nhật ký, tick checklist quy trình, và responsive ở 375px (đã bắt và sửa 2 lỗi tràn ngang CSS Grid thật trong lúc test).

Bản Streamlit cũ (`streamlit_app.py`) vẫn còn trong repo, hoạt động độc lập nếu muốn dùng, nhưng dashboard trên là bản chính giờ.

### Chạy nền, không phụ thuộc phiên Claude Code

Lệnh `uvicorn api:app --reload` ở trên chỉ sống trong terminal đang mở nó — đóng terminal (hoặc đóng phiên Claude Code nếu là Claude chạy nó để test) là mất kết nối, giao diện báo "Lỗi lấy dữ liệu: Failed to fetch". Để nó tự chạy mỗi khi bạn đăng nhập Windows, không cần giữ cửa sổ nào mở:

```bash
cd lsteven-mcp
python serve_background.py   # test thu, xem no chay dung khong (Ctrl+C de dung)
```

Chạy ổn thì đăng ký tự khởi động — sao chép launcher vào thư mục Startup của Windows (không cần quyền admin, không cần Task Scheduler):

```powershell
Copy-Item "run_server_template.bat" "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\LSteven Cockpit.bat"
```

Từ lần đăng nhập sau, `pythonw.exe` (không cửa sổ console) sẽ tự chạy `serve_background.py` ở nền. Log ghi ra `server.log` trong thư mục này — mở file đó khi cần tra lỗi. Muốn tắt: mở Task Manager, tìm tiến trình `pythonw.exe` ứng với `serve_background.py`, kết thúc nó; hoặc xoá file `.bat` khỏi thư mục Startup để không tự chạy lần sau.

**Kiểm tra server có đang sống không** (từ PowerShell bất kỳ lúc nào):
```powershell
Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*python*" }
```
hoặc đơn giản mở `http://localhost:8787` — không vào được là server đã chết, chạy lại `python serve_background.py`.

## Roadmap

- ✅ Lớp 1 — đọc chart qua MCP tool.
- ✅ Lớp 2 — cảnh báo Telegram.
- ✅ Lớp 3 — backtest tập luật rút gọn.
- ✅ Dashboard + Nhật ký — FastAPI + HTML/JS local (ở trên).
- ⏭ Lớp 4 — paper trading / testnet.
- ⏭ Deploy dashboard lên cloud để xem từ điện thoại (khi thấy dùng hàng ngày thật sự).
- ⛔ Lớp 5 — đặt lệnh tiền thật: **không tự động hoá bởi AI**, nếu làm thì người dùng tự vận hành với API key của chính mình.

Lõi đọc (`indicators.py`, `form_trap.py`, `multiframe.py`) không phụ thuộc gì vào MCP, Telegram hay FastAPI — dùng chung cho cả ba, và sẵn sàng cho một bot sau này mà không phải viết lại.

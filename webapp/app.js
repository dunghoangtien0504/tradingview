// LSteven Cockpit — vanilla JS, no build step.
"use strict";

const API = "";

const TF_LABEL = {
  M: "Tháng", W: "Tuần", "4D": "4 Ngày", "3D": "3 Ngày", "2D": "2 Ngày", D: "Ngày",
  H12: "12 giờ", H6: "6 giờ", H4: "4 giờ", H3: "3 giờ", H2: "2 giờ", H1: "1 giờ",
};
const ORDER = ["M", "W", "4D", "3D", "2D", "D", "H12", "H6", "H4", "H3", "H2", "H1"];

const ICONS = {
  trendUp: `<svg viewBox="0 0 24 24" fill="none"><path d="M3 17l6-6 4 4 8-8M21 7v6M21 7h-6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  trendDown: `<svg viewBox="0 0 24 24" fill="none"><path d="M3 7l6 6 4-4 8 8M21 17v-6M21 17h-6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  warning: `<svg viewBox="0 0 24 24" fill="none"><path d="M12 9v4m0 4h.01M10.3 3.86L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.86a2 2 0 00-3.4 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  pause: `<svg viewBox="0 0 24 24" fill="none"><path d="M9 6v12M15 6v12" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>`,
  chevron: `<svg viewBox="0 0 24 24" fill="none" class="chev"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  trash: `<svg viewBox="0 0 24 24" fill="none"><path d="M4 7h16M9 7V5a2 2 0 012-2h2a2 2 0 012 2v2m2 0v12a2 2 0 01-2 2H9a2 2 0 01-2-2V7h10z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};

// -------------------------------------------------------- gauge & spark --
function gaugeArcPath(cx, cy, r, startDeg, endDeg) {
  const rad = d => (d * Math.PI) / 180;
  const sx = cx + r * Math.cos(rad(startDeg)), sy = cy - r * Math.sin(rad(startDeg));
  const ex = cx + r * Math.cos(rad(endDeg)), ey = cy - r * Math.sin(rad(endDeg));
  const large = (startDeg - endDeg) > 180 ? 1 : 0;
  return `M ${sx.toFixed(2)} ${sy.toFixed(2)} A ${r} ${r} 0 ${large} 1 ${ex.toFixed(2)} ${ey.toFixed(2)}`;
}
const lucTone = v => (v <= 2 ? "lo" : v <= 4 ? "mid" : "hi");
const lucColor = v => (v <= 2 ? "var(--down)" : v <= 4 ? "var(--warn)" : "var(--up)");

function radialGauge(value, max, size) {
  const v = Math.max(0, Math.min(1, value / max));
  const cx = size / 2, cy = size * 0.56, r = size * 0.40, sw = size * 0.11;
  const color = lucColor(value);
  const uid = "g" + Math.random().toString(36).slice(2, 8);
  return `<svg viewBox="0 0 ${size} ${size * 0.64}" class="gauge" role="img" aria-label="Mức lực ${value} trên ${max}">
      <defs><filter id="${uid}" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter></defs>
      <path d="${gaugeArcPath(cx, cy, r, 180, 0)}" fill="none" stroke="var(--surface-3)" stroke-width="${sw}" stroke-linecap="round"/>
      <path d="${gaugeArcPath(cx, cy, r, 180, 180 - 180 * v)}" fill="none" stroke="${color}" stroke-width="${sw}" stroke-linecap="round" filter="url(#${uid})"/>
      <text x="${cx}" y="${cy - 2}" text-anchor="middle" class="gauge-num" font-size="${size * 0.22}" fill="${color}">${value}</text>
      <text x="${cx}" y="${cy + size * 0.1}" text-anchor="middle" font-size="${size * 0.075}" fill="var(--ink-faint)" font-family="var(--font-mono)">/ ${max}</text>
    </svg>`;
}

/** Mini 3-line chart: RSI trắng (theo yêu cầu), EMA9 vàng, WMA45 hồng. */
function sparkline(rsiArr, ema9Arr, wma45Arr, w = 132, h = 34) {
  if (!rsiArr || rsiArr.length < 2) return "";
  const all = [...rsiArr, ...ema9Arr, ...wma45Arr].filter(v => v != null && !isNaN(v));
  const min = Math.min(...all), max = Math.max(...all), range = (max - min) || 1;
  const pts = arr => arr.map((v, i) => {
    const x = (i / (arr.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 5) - 2.5;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const uid = "s" + Math.random().toString(36).slice(2, 8);
  return `<svg viewBox="0 0 ${w} ${h}" class="spark" preserveAspectRatio="none" aria-hidden="true">
      <defs><filter id="${uid}" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="1.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter></defs>
      <polyline points="${pts(wma45Arr)}" fill="none" stroke="var(--wma)" stroke-width="1.4" opacity=".85"/>
      <polyline points="${pts(ema9Arr)}" fill="none" stroke="var(--warn)" stroke-width="1.4" opacity=".9"/>
      <polyline points="${pts(rsiArr)}" fill="none" stroke="var(--rsi)" stroke-width="1.9" filter="url(#${uid})"/>
    </svg>`;
}

// ------------------------------------------------------------- tab nav --
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => { b.classList.remove("active"); b.setAttribute("aria-selected", "false"); });
    btn.classList.add("active"); btn.setAttribute("aria-selected", "true");
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");
    window.scrollTo({ top: 0, behavior: "instant" });
  });
});

// ----------------------------------------------------------- top clock --
function tickClock() {
  document.getElementById("serverClock").textContent = new Date().toISOString().slice(11, 19) + " UTC";
}
setInterval(tickClock, 1000); tickClock();

// ------------------------------------------------------- countdown ------
function fmtCountdown(iso) {
  const ms = new Date(iso) - new Date();
  if (ms <= 0) return "đang đóng…";
  const s = Math.floor(ms / 1000);
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}n ${h}g`;
  if (h > 0) return `${h}g ${m}p`;
  return `${m}p ${s % 60}s`;
}
let countdownTimers = {};
setInterval(() => {
  for (const tf in countdownTimers) {
    const el = document.getElementById(`cd-${tf}`);
    if (el) el.textContent = fmtCountdown(countdownTimers[tf]);
  }
}, 1000);

// ------------------------------------------------------------ snapshot --
let lastFetch = 0;
let lastSnap = null;
const openRows = new Set();

async function loadSnapshot() {
  const symbol = document.getElementById("symbolInput").value.trim().toUpperCase() || "BTCUSDT";
  const btn = document.getElementById("refreshBtn");
  btn.classList.add("spinning");
  try {
    const res = await fetch(`${API}/api/snapshot?symbol=${encodeURIComponent(symbol)}`);
    const snap = await res.json();
    lastSnap = snap;
    renderSnapshot(snap);
    lastFetch = Date.now();
    loadSignals();
  } catch (e) {
    document.getElementById("summaryBanner").innerHTML = `<span style="color:var(--down)">Lỗi lấy dữ liệu: ${e}</span>`;
  } finally {
    btn.classList.remove("spinning");
  }
}

function renderSnapshot(snap) {
  const readings = snap.readings || {};
  const frames = ORDER.filter(tf => readings[tf]);
  countdownTimers = {};

  // ---- hero ----
  const d = readings.D;
  if (d) {
    document.getElementById("heroSymbolLabel").textContent = `${snap.symbol} · DAILY`;
    document.getElementById("heroPrice").textContent = "$" + d.price.toLocaleString(undefined, { maximumFractionDigits: 2 });
    const chg = ((d.price - d.open_price) / d.open_price) * 100;
    const chgEl = document.getElementById("heroChange");
    chgEl.innerHTML = `${chg >= 0 ? ICONS.trendUp : ICONS.trendDown}<span>${chg >= 0 ? "+" : ""}${chg.toFixed(2)}% trong nến ngày</span>`;
    chgEl.className = "hero-change mono " + (chg >= 0 ? "up" : "down");
    document.getElementById("heroSub").textContent =
      `RSI ${d.rsi.toFixed(1)} · EMA9 ${d.ema9.toFixed(1)} · WMA45 ${d.wma45.toFixed(1)}`;
    document.getElementById("heroGauge").innerHTML = radialGauge(d.muc_luc, 6, 160);
  }

  // ---- verdict ----
  const up = frames.filter(tf => readings[tf].above_45);
  const down = frames.filter(tf => !readings[tf].above_45);
  const traps = frames.filter(tf => readings[tf].active_trap);
  let html = "";
  if (down.length === 0) html += `<span class="pill up">${ICONS.trendUp}ĐỌC LÊN</span>Cả ${frames.length} khung đều có RSI <b>trên</b> đường WMA45.`;
  else if (up.length === 0) html += `<span class="pill down">${ICONS.trendDown}ĐỌC XUỐNG</span>Cả ${frames.length} khung đều có RSI <b>dưới</b> đường WMA45.`;
  else html += `<span class="pill mixed">${ICONS.warning}MÂU THUẪN</span>Lên: <b>${up.join(" ")}</b> · Xuống: <b>${down.join(" ")}</b> — mâu thuẫn rõ ràng thì vẫn chơi được, lưng chừng mới nên đứng ngoài (Bài 18).`;
  if (traps.length) {
    const chi = traps.map(tf => `${tf} (${readings[tf].active_trap === "up" ? "lên" : "xuống"})`).join(", ");
    html += `<br><span class="pill mixed" style="margin-top:8px">${ICONS.warning}TRAP</span>Chưa giải quyết ở <b>${chi}</b> — còn trap thì còn đọc theo chiều trap.`;
  }
  document.getElementById("summaryBanner").innerHTML = html;

  // ---- dong thuan chain ----
  const chain = document.getElementById("dongThuanChain");
  chain.innerHTML = frames.map((tf, i) => {
    const r = readings[tf];
    const node = `<span class="chain-node ${r.above_45 ? "up" : "down"}">${tf}</span>`;
    if (i === 0) return node;
    const prev = readings[frames[i - 1]];
    const ok = prev.above_45 === r.above_45;
    return `<span class="chain-link ${ok ? "ok" : "bad"}"></span>${node}`;
  }).join("");

  const extras = frames.filter(tf => !readings[tf].canonical);
  document.getElementById("matrixNote").textContent = extras.length
    ? `${extras.join(", ")} là khung mở rộng — bộ gốc của phương pháp chỉ dùng 7 khung (Bài 6)`
    : "";

  // ---- matrix ----
  const body = document.getElementById("matrixBody");
  body.innerHTML = frames.map(tf => {
    const r = readings[tf];
    const nd = r.nhan_dinh || {};
    countdownTimers[tf] = r.next_close;
    const biasCls = nd.bias === "LEN" ? "up" : nd.bias === "XUONG" ? "down" : "cho";
    const biasIcon = nd.bias === "LEN" ? ICONS.trendUp : nd.bias === "XUONG" ? ICONS.trendDown : ICONS.pause;
    const biasTxt = nd.bias === "LEN" ? "LÊN" : nd.bias === "XUONG" ? "XUỐNG" : "CHỜ";
    const bars = Array.from({ length: 6 }, (_, k) =>
      `<i class="${k < r.muc_luc ? "on " + lucTone(r.muc_luc) : ""}"></i>`).join("");
    const trapFlag = r.active_trap
      ? `<span class="trap-flag" title="Trap chưa được giải quyết">${ICONS.warning}TRAP ${r.active_trap === "up" ? "LÊN" : "XUỐNG"}</span>` : "";
    return `
      <tr class="row ${openRows.has(tf) ? "open" : ""}" data-tf="${tf}" tabindex="0" role="button" aria-expanded="${openRows.has(tf)}">
        <td>
          <div class="tf-badge">
            <span class="tf-code">${tf}</span>
            ${r.canonical ? "" : `<span class="tf-extra">mở rộng</span>`}
          </div>
          <span class="tf-sub">${TF_LABEL[tf] || ""}</span>
        </td>
        <td><span class="read-chip ${biasCls}">${biasIcon}${biasTxt}</span>${trapFlag}</td>
        <td class="num"><span class="val rsi">${r.rsi.toFixed(1)}</span></td>
        <td class="num hide-sm"><span class="val ema">${r.ema9.toFixed(1)}</span></td>
        <td class="num hide-sm"><span class="val wma">${r.wma45.toFixed(1)}</span></td>
        <td><span class="luc-bar">${bars}<span class="luc-num">${r.muc_luc}</span></span></td>
        <td class="spark-cell hide-sm">${sparkline(r.rsi_series, r.ema9_series, r.wma45_series)}</td>
        <td><span class="stage ${nd.giai_doan || ""}">${nd.giai_doan_label || "—"}</span></td>
        <td class="hide-sm"><span class="cd" id="cd-${tf}">${fmtCountdown(r.next_close)}</span></td>
        <td>${ICONS.chevron}</td>
      </tr>
      <tr class="detail" data-detail="${tf}" ${openRows.has(tf) ? "" : "hidden"}>
        <td colspan="10">
          <div class="detail-inner">
            <div class="detail-block ok">
              <h4>Xác nhận đi tiếp</h4>
              ${listOrEmpty(nd.xac_nhan)}
            </div>
            <div class="detail-block no">
              <h4>Huỷ đọc này</h4>
              ${listOrEmpty(nd.huy)}
            </div>
            <div class="detail-block">
              <h4>Lưu ý</h4>
              ${listOrEmpty(nd.luu_y)}
            </div>
          </div>
        </td>
      </tr>`;
  }).join("");

  body.querySelectorAll("tr.row").forEach(row => {
    const toggle = () => {
      const tf = row.dataset.tf;
      const det = body.querySelector(`tr[data-detail="${tf}"]`);
      const nowOpen = det.hidden;
      det.hidden = !nowOpen;
      row.classList.toggle("open", nowOpen);
      row.setAttribute("aria-expanded", String(nowOpen));
      if (nowOpen) openRows.add(tf); else openRows.delete(tf);
    };
    row.addEventListener("click", toggle);
    row.addEventListener("keydown", e => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
    });
  });

  const entryField = document.getElementById("calcEntry");
  if (!entryField.dataset.touched && d) entryField.value = d.price;
  runCalc();
  updateAgoLabel();
}

function listOrEmpty(arr) {
  if (!arr || !arr.length) return `<p class="detail-empty">Không có ghi chú</p>`;
  return `<ul>${arr.map(x => `<li>${x}</li>`).join("")}</ul>`;
}

function updateAgoLabel() {
  const secs = Math.floor((Date.now() - lastFetch) / 1000);
  document.getElementById("updatedAgo").textContent = lastFetch ? `cập nhật ${secs}s trước` : "—";
}
setInterval(updateAgoLabel, 1000);

document.getElementById("refreshBtn").addEventListener("click", loadSnapshot);
document.getElementById("symbolInput").addEventListener("keydown", e => { if (e.key === "Enter") loadSnapshot(); });
// Lam moi dinh ky chi de so lieu khong bi cu; tin hieu that chi doi khi NEN
// DONG — xem cot "nen dong sau" (Bai 14).
setInterval(loadSnapshot, 30000);

// -------------------------------------------------------------- signals -
async function loadSignals() {
  const symbol = document.getElementById("symbolInput").value.trim().toUpperCase() || "BTCUSDT";
  const tf = document.getElementById("signalTf").value || "D";
  try {
    const res = await fetch(`${API}/api/signals?symbol=${symbol}&timeframe=${tf}`);
    const data = await res.json();
    renderTimeline("formList", data.forms, f =>
      `<span class="dot ${f.direction === "buy" ? "up" : "down"}"></span>Form ${f.direction === "buy" ? "BUY" : "SELL"} · RSI ${f.diem3_rsi}<time>${f.diem3_time.slice(0, 16).replace("T", " ")}</time>`);
    renderTimeline("trapList", data.traps, t =>
      `<span class="dot ${t.direction === "down" ? "down" : "up"}"></span>${t.direction === "down" ? "Xuống" : "Lên"} · ${t.status.replace(/_/g, " ")}<time>${t.start_time.slice(0, 10)}</time>`);
  } catch (e) { /* panel phu, khong chan luong chinh */ }
}
function renderTimeline(id, items, fmt) {
  const el = document.getElementById(id);
  if (!items || !items.length) { el.innerHTML = `<li class="empty">Chưa có dữ liệu</li>`; return; }
  el.innerHTML = items.map(it => `<li>${fmt(it)}</li>`).join("");
}

// ----------------------------------------------------------- calculator -
let calcDebounce;
["calcEquity", "calcRisk", "calcEntry", "calcSl"].forEach(id => {
  document.getElementById(id).addEventListener("input", e => {
    if (id === "calcEntry") e.target.dataset.touched = "1";
    clearTimeout(calcDebounce);
    calcDebounce = setTimeout(runCalc, 250);
  });
});
async function runCalc() {
  const equity = parseFloat(document.getElementById("calcEquity").value);
  const risk_pct = parseFloat(document.getElementById("calcRisk").value);
  const entry = parseFloat(document.getElementById("calcEntry").value);
  const sl = parseFloat(document.getElementById("calcSl").value);
  const box = document.getElementById("calcResult");
  if (!entry || !sl || entry === sl) {
    box.className = "calc-result empty";
    box.textContent = "Nhập giá vào & SL để tính";
    return;
  }
  try {
    const res = await fetch(`${API}/api/position-size`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ equity, entry, sl, risk_pct }),
    });
    const r = await res.json();
    if (r.error) { box.className = "calc-result empty"; box.textContent = r.error; return; }
    box.className = "calc-result ready";
    box.innerHTML = `
      <span class="big">$${r.khoi_luong_toi_da_usd.toLocaleString()}</span>
      <div class="row"><span>Chiều</span><b>${r.direction}</b></div>
      <div class="row"><span>Khoảng SL</span><b>${r.sl_khoang_cach_pct}%</b></div>
      <div class="row"><span>Mất tối đa nếu SL</span><b>$${r.so_tien_cho_phep_mat_usd.toLocaleString()}</b></div>
      <div class="row"><span>Ví dụ vào 30%</span><b>$${r.vi_du_vao_30_phan_tram.toLocaleString()}</b></div>`;
  } catch (e) { /* bo qua loi tam thoi khi dang go */ }
}

// ------------------------------------------------------------- journal --
async function loadJournal() {
  const res = await fetch(`${API}/api/journal`);
  const data = await res.json();
  renderStats(data.stats);
  renderTrades(data.trades);
}
function renderStats(s) {
  document.getElementById("journalStats").innerHTML = `
    <div class="stat-tile"><div class="label">Tổng số lệnh</div><div class="value">${s.tong_so_lenh}</div></div>
    <div class="stat-tile"><div class="label">Đang mở</div><div class="value">${s.dang_mo}</div></div>
    <div class="stat-tile"><div class="label">Winrate (đã đóng)</div><div class="value">${s.winrate_pct ?? "—"}${s.winrate_pct != null ? "%" : ""}</div></div>
    <div class="stat-tile"><div class="label">Tổng P&amp;L</div><div class="value" style="color:${s.tong_pnl_usd >= 0 ? "var(--up)" : "var(--down)"}">$${s.tong_pnl_usd.toLocaleString()}</div></div>`;
}
function renderTrades(trades) {
  const el = document.getElementById("tradeList");
  if (!trades.length) { el.innerHTML = `<div class="empty-state">Chưa có lệnh nào — bấm "Thêm lệnh mới" phía trên.</div>`; return; }
  el.innerHTML = trades.map(t => `
    <div class="trade-card" data-id="${t.id}">
      <div class="who">${t.symbol} · ${t.khung_choi}<span class="huong ${t.huong}">${t.huong}</span></div>
      <div class="nums">Entry ${t.entry_price ?? "—"} → SL ${t.sl_price ?? "—"} · KL ${t.khoi_luong_usd ?? "—"}</div>
      <div class="reason">${t.ly_do || ""}</div>
      <select class="ket-qua-select">
        ${["dang_mo", "thang", "thua", "hoa"].map(v => `<option value="${v}" ${v === t.ket_qua ? "selected" : ""}>${v}</option>`).join("")}
      </select>
      <button class="icon-btn del-btn" aria-label="Xoá lệnh">${ICONS.trash}</button>
    </div>`).join("");

  el.querySelectorAll(".ket-qua-select").forEach(sel => sel.addEventListener("change", async e => {
    const id = e.target.closest(".trade-card").dataset.id;
    await fetch(`${API}/api/journal/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ket_qua: e.target.value }),
    });
    loadJournal();
  }));
  el.querySelectorAll(".del-btn").forEach(btn => btn.addEventListener("click", async e => {
    const id = e.target.closest(".trade-card").dataset.id;
    await fetch(`${API}/api/journal/${id}`, { method: "DELETE" });
    loadJournal();
  }));
}

document.getElementById("newTradeBtn").addEventListener("click", () => {
  document.getElementById("tradeForm").classList.toggle("hidden");
});
document.getElementById("cancelTradeBtn").addEventListener("click", () => {
  document.getElementById("tradeForm").classList.add("hidden");
});
document.getElementById("fillContextBtn").addEventListener("click", () => {
  if (!lastSnap) return;
  const r = lastSnap.readings;
  const txt = ORDER.filter(tf => r[tf]).map(tf => {
    const x = r[tf];
    return `${tf}: ${x.above_45 ? "lên" : "xuống"} (RSI ${x.rsi.toFixed(1)}, lực ${x.muc_luc}${x.active_trap ? ", trap " + (x.active_trap === "up" ? "lên" : "xuống") : ""})`;
  }).join(" · ");
  document.querySelector('#tradeForm textarea[name="boi_canh_da_khung"]').value = txt;
});
document.getElementById("tradeForm").addEventListener("submit", async e => {
  e.preventDefault();
  const payload = Object.fromEntries(new FormData(e.target).entries());
  ["entry_price", "sl_price", "khoi_luong_usd"].forEach(k => {
    payload[k] = payload[k] ? parseFloat(payload[k]) : null;
  });
  await fetch(`${API}/api/journal`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  e.target.reset(); e.target.classList.add("hidden");
  loadJournal();
});

// --------------------------------------------------------------- process
const PROCESS_STEPS = [
  "Đọc bối cảnh đa khung (W → 3D → D → H12 → H4): khung nào lên/xuống, mới đi hay đã xa, mức lực 1-6.",
  "Chọn khung để chơi, suy ra khung vào và khung ra (bố–con–cháu).",
  "Chờ tín hiệu vào (RSI cắt lên vàng & đỏ, hoặc form buy 1-2-3); đợi đóng nến; vùng vào là khoảng tương đối.",
  "Xác định điểm vào → định SL (đáy gần nhất hoặc đường gần nhất).",
  "Tính khối lượng tối đa = (2% số dư) ÷ (% khoảng SL). Chia lệnh tuỳ gu.",
  "Gồng theo khung, không đặt TP; cân nhắc dời SL về hoà khi tính chất đổi. Không bao giờ nới SL.",
  "Thoát khi lý do vào không còn (RSI cắt xuống WMA45 / form sell ở khung tương ứng).",
  "Giữ kỷ luật, nhất quán với gu rủi ro của mình — ghi lại vào Nhật ký.",
];
const todayKey = () => "lsteven-process-" + new Date().toISOString().slice(0, 10);
function renderProcess() {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(todayKey()) || "{}"); } catch (e) { saved = {}; }
  const el = document.getElementById("processList");
  el.innerHTML = PROCESS_STEPS.map((step, i) => `
    <li class="process-item ${saved[i] ? "done" : ""}" data-i="${i}">
      <input type="checkbox" ${saved[i] ? "checked" : ""} aria-label="Bước ${i + 1}">
      <span class="step-no">${String(i + 1).padStart(2, "0")}</span>
      <span class="step-text">${step}</span>
    </li>`).join("");
  el.querySelectorAll('input[type=checkbox]').forEach(cb => cb.addEventListener("change", () => {
    const li = cb.closest(".process-item");
    li.classList.toggle("done", cb.checked);
    try {
      const s = JSON.parse(localStorage.getItem(todayKey()) || "{}");
      s[li.dataset.i] = cb.checked;
      localStorage.setItem(todayKey(), JSON.stringify(s));
    } catch (e) { /* localStorage co the bi chan */ }
  }));
}

// ------------------------------------------------------------------ init
function fillTimeframeSelects() {
  const opts = ORDER.map(tf => `<option value="${tf}" ${tf === "D" ? "selected" : ""}>${tf}</option>`).join("");
  document.getElementById("signalTf").innerHTML = opts;
  document.getElementById("tradeKhung").innerHTML = opts;
  document.getElementById("signalTf").addEventListener("change", loadSignals);
}
fillTimeframeSelects();
loadSnapshot();
loadJournal();
renderProcess();

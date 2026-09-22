// LSteven Cockpit — vanilla JS, no build step.
"use strict";

const API = "";

// ---------------------------------------------------------------- icons --
const ICONS = {
  trendUp: `<svg viewBox="0 0 24 24" fill="none"><path d="M3 17l6-6 4 4 8-8M21 7v6M21 7h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  trendDown: `<svg viewBox="0 0 24 24" fill="none"><path d="M3 7l6 6 4-4 8 8M21 17v-6M21 17h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  warning: `<svg viewBox="0 0 24 24" fill="none"><path d="M12 9v4m0 4h.01M10.3 3.86L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.86a2 2 0 00-3.4 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  clock: `<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/><path d="M12 7v5l3 3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,
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
function lucColor(v6) {
  return v6 <= 2 ? "var(--down)" : v6 === 3 || v6 === 4 ? "var(--warn)" : "var(--up)";
}
function radialGauge(value, max, size) {
  const v = Math.max(0, Math.min(1, value / max));
  const cx = size / 2, cy = size * 0.56, r = size * 0.40, sw = size * 0.12;
  const bg = gaugeArcPath(cx, cy, r, 180, 0);
  const fg = gaugeArcPath(cx, cy, r, 180, 180 - 180 * v);
  const color = lucColor(value);
  return `<svg viewBox="0 0 ${size} ${size * 0.62}" class="gauge" role="img" aria-label="Mức lực ${value}/${max}">
      <path d="${bg}" fill="none" stroke="var(--surface-3)" stroke-width="${sw}" stroke-linecap="round"/>
      <path d="${fg}" fill="none" stroke="${color}" stroke-width="${sw}" stroke-linecap="round"/>
      <text x="${cx}" y="${cy - 1}" text-anchor="middle" class="gauge-num" fill="${color}">${value}</text>
    </svg>`;
}
function sparkline(rsiArr, ema9Arr, wma45Arr, w, h) {
  if (!rsiArr || rsiArr.length < 2) return "";
  const all = [...rsiArr, ...ema9Arr, ...wma45Arr];
  const min = Math.min(...all), max = Math.max(...all), range = (max - min) || 1;
  const pts = arr => arr.map((v, i) => {
    const x = (i / (arr.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return `<svg viewBox="0 0 ${w} ${h}" class="spark" preserveAspectRatio="none" aria-hidden="true">
      <polyline points="${pts(wma45Arr)}" fill="none" stroke="var(--wma)" stroke-width="1.5" opacity=".8"/>
      <polyline points="${pts(ema9Arr)}" fill="none" stroke="var(--warn)" stroke-width="1.5" opacity=".85"/>
      <polyline points="${pts(rsiArr)}" fill="none" stroke="currentColor" stroke-width="2"/>
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
  document.getElementById("serverClock").textContent =
    new Date().toISOString().slice(11, 19) + " UTC";
}
setInterval(tickClock, 1000); tickClock();

// ------------------------------------------------------- countdown ------
const TF_LABEL = { M: "Tháng", W: "Tuần", "3D": "3 Ngày", D: "Ngày", H12: "12h", H4: "4h", H1: "1h" };
const ORDER = ["M", "W", "3D", "D", "H12", "H4", "H1"];

function fmtCountdown(iso) {
  const ms = new Date(iso) - new Date();
  if (ms <= 0) return "đang đóng…";
  const s = Math.floor(ms / 1000);
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}n ${h}g`;
  if (h > 0) return `${h}g ${m}p`;
  return `${m}p ${s % 60}s`;
}

let countdownTimers = {}; // tf -> iso
function startCountdownTicker() {
  setInterval(() => {
    for (const tf in countdownTimers) {
      const el = document.getElementById(`cd-${tf}`);
      if (el) el.textContent = fmtCountdown(countdownTimers[tf]);
    }
  }, 1000);
}
startCountdownTicker();

// ------------------------------------------------------------ snapshot --
let lastFetch = 0;
async function loadSnapshot() {
  const symbol = document.getElementById("symbolInput").value.trim().toUpperCase() || "BTCUSDT";
  const btn = document.getElementById("refreshBtn");
  btn.classList.add("spinning");
  try {
    const res = await fetch(`${API}/api/snapshot?symbol=${encodeURIComponent(symbol)}`);
    const snap = await res.json();
    renderSnapshot(snap);
    lastFetch = Date.now();
    loadSignals();
  } catch (e) {
    document.getElementById("summaryBanner").innerHTML =
      `<span style="color:var(--down)">Lỗi lấy dữ liệu: ${e}</span>`;
  } finally {
    btn.classList.remove("spinning");
  }
}

function renderSnapshot(snap) {
  const readings = snap.readings || {};
  countdownTimers = {};

  // --- hero ---
  const d = readings.D;
  if (d) {
    document.getElementById("heroSymbolLabel").textContent = `${snap.symbol} · Daily`;
    document.getElementById("heroPrice").textContent = "$" + d.price.toLocaleString(undefined, { maximumFractionDigits: 2 });
    const chgPct = ((d.price - d.open_price) / d.open_price) * 100;
    const chgEl = document.getElementById("heroChange");
    chgEl.innerHTML = `${chgPct >= 0 ? ICONS.trendUp : ICONS.trendDown}<span>${chgPct >= 0 ? "+" : ""}${chgPct.toFixed(2)}% hôm nay</span>`;
    chgEl.className = "hero-change " + (chgPct >= 0 ? "up" : "down");
    document.getElementById("heroGauge").innerHTML = radialGauge(d.muc_luc, 6, 148);
  }

  // --- summary sentence ---
  const up = ORDER.filter(tf => readings[tf]?.above_45);
  const down = ORDER.filter(tf => readings[tf] && !readings[tf].above_45);
  const traps = ORDER.filter(tf => readings[tf]?.active_trap);
  let html = "";
  if (up.length === ORDER.filter(tf => readings[tf]).length) {
    html += `<span class="pill up">${ICONS.trendUp}LÊN</span>Tất cả các khung đang đọc <b>lên</b> (RSI trên 45).`;
  } else if (down.length === ORDER.filter(tf => readings[tf]).length) {
    html += `<span class="pill down">${ICONS.trendDown}XUỐNG</span>Tất cả các khung đang đọc <b>xuống</b> (RSI dưới 45).`;
  } else {
    html += `<span class="pill mixed">${ICONS.warning}MÂU THUẪN</span>Lên: <b>${up.join(", ") || "—"}</b> · Xuống: <b>${down.join(", ") || "—"}</b> — đọc kỹ Bài 6/9 trước khi vào.`;
  }
  if (traps.length) {
    const chi = traps.map(tf => `${tf} (${readings[tf].active_trap === "up" ? "lên" : "xuống"})`).join(", ");
    html += `<br><span class="pill mixed" style="margin-top:8px">${ICONS.warning}TRAP</span>Đang có Trap chưa giải quyết ở <b>${chi}</b> — đọc theo chiều trap, chưa vội kết luận đảo chiều.`;
  }
  document.getElementById("summaryBanner").innerHTML = html;

  // --- tf strip ---
  const strip = document.getElementById("tfStrip");
  strip.innerHTML = "";
  let prevAbove = null;
  ORDER.forEach((tf, i) => {
    const r = readings[tf];
    if (i > 0) {
      const connector = document.createElement("div");
      const ok = r && prevAbove !== null && r.above_45 === prevAbove;
      connector.className = "tf-connector " + (r ? (ok ? "dong-thuan" : "lech") : "");
      strip.appendChild(connector);
    }
    const cell = document.createElement("div");
    cell.className = "tf-cell";
    cell.style.animationDelay = `${i * 40}ms`;
    if (!r) {
      cell.innerHTML = `<div class="tf-head"><span class="tf-name">${tf}</span></div><span style="color:var(--down);font-size:12px">lỗi dữ liệu</span>`;
      strip.appendChild(cell);
      return;
    }
    prevAbove = r.above_45;
    const trendCls = r.above_45 ? "up" : "down";
    const trapHtml = r.active_trap
      ? `<div class="tf-trap">${ICONS.warning}TRAP ${r.active_trap === "up" ? "LÊN" : "XUỐNG"}</div>`
      : `<div class="tf-trap ghost">&nbsp;</div>`;
    countdownTimers[tf] = r.next_close;
    cell.classList.add(trendCls === "up" ? "tone-up" : "tone-down");
    cell.innerHTML = `
      <div class="tf-head">
        <div>
          <span class="tf-name">${tf}</span>
          <span class="tf-label">${TF_LABEL[tf]}</span>
        </div>
        ${radialGauge(r.muc_luc, 6, 52)}
      </div>
      <span class="tf-rsi">${r.rsi.toFixed(1)}<small> RSI</small></span>
      <div class="tf-spark ${trendCls}">${sparkline(r.rsi_series, r.ema9_series, r.wma45_series, 140, 34)}</div>
      ${trapHtml}
      <span class="tf-countdown" id="cd-wrap-${tf}">${ICONS.clock}<span id="cd-${tf}">${fmtCountdown(r.next_close)}</span></span>
    `;
    strip.appendChild(cell);
  });

  // --- calc default entry price = D close ---
  const entryField = document.getElementById("calcEntry");
  if (!entryField.dataset.touched && readings.D) {
    entryField.value = readings.D.price;
  }
  runCalc();
  updateAgoLabel();
}

function updateAgoLabel() {
  const el = document.getElementById("updatedAgo");
  const secs = Math.floor((Date.now() - lastFetch) / 1000);
  el.textContent = lastFetch ? `cập nhật ${secs}s trước` : "—";
}
setInterval(updateAgoLabel, 1000);

document.getElementById("refreshBtn").addEventListener("click", loadSnapshot);
document.getElementById("symbolInput").addEventListener("keydown", e => { if (e.key === "Enter") loadSnapshot(); });

// auto-refresh every 30s — dung de hien thi tuoi, KHONG phai tick gia; tin
// hieu that chi doi khi nen dong (xem dem nguoc tung khung o tren)
setInterval(loadSnapshot, 30000);

// -------------------------------------------------------------- signals -
async function loadSignals() {
  const symbol = document.getElementById("symbolInput").value.trim().toUpperCase() || "BTCUSDT";
  const tf = document.getElementById("signalTf").value;
  try {
    const res = await fetch(`${API}/api/signals?symbol=${symbol}&timeframe=${tf}`);
    const data = await res.json();
    renderTimeline("formList", data.forms, f =>
      `<span class="dot ${f.direction === "buy" ? "up" : "down"}"></span>Form ${f.direction === "buy" ? "BUY" : "SELL"} · RSI ${f.diem3_rsi}<time>${f.diem3_time.slice(0, 16).replace("T", " ")}</time>`
    );
    renderTimeline("trapList", data.traps, t =>
      `<span class="dot ${t.direction === "down" ? "down" : "up"}"></span>${t.direction === "down" ? "Xuống" : "Lên"} · ${t.status.replace(/_/g, " ")}<time>${t.start_time.slice(0, 10)}</time>`
    );
  } catch (e) { /* silent — non-critical panel */ }
}
function renderTimeline(id, items, formatter) {
  const el = document.getElementById(id);
  if (!items || !items.length) { el.innerHTML = `<li class="empty">Chưa có dữ liệu</li>`; return; }
  el.innerHTML = items.map(it => `<li>${formatter(it)}</li>`).join("");
}
document.getElementById("signalTf").addEventListener("change", loadSignals);

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
      <div class="row"><span>Ví dụ vào 30%</span><b>$${r.vi_du_vao_30_phan_tram.toLocaleString()}</b></div>
    `;
  } catch (e) { /* ignore transient errors while typing */ }
}

// ------------------------------------------------------------- journal --
async function loadJournal() {
  const res = await fetch(`${API}/api/journal`);
  const data = await res.json();
  renderStats(data.stats);
  renderTrades(data.trades);
}

function renderStats(s) {
  const el = document.getElementById("journalStats");
  el.innerHTML = `
    <div class="stat-tile"><div class="label">Tổng số lệnh</div><div class="value">${s.tong_so_lenh}</div></div>
    <div class="stat-tile"><div class="label">Đang mở</div><div class="value">${s.dang_mo}</div></div>
    <div class="stat-tile"><div class="label">Winrate (đã đóng)</div><div class="value">${s.winrate_pct ?? "—"}${s.winrate_pct != null ? "%" : ""}</div></div>
    <div class="stat-tile"><div class="label">Tổng P&amp;L</div><div class="value" style="color:${s.tong_pnl_usd >= 0 ? "var(--up)" : "var(--down)"}">$${s.tong_pnl_usd.toLocaleString()}</div></div>
  `;
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
    </div>
  `).join("");

  el.querySelectorAll(".ket-qua-select").forEach(sel => {
    sel.addEventListener("change", async e => {
      const id = e.target.closest(".trade-card").dataset.id;
      await fetch(`${API}/api/journal/${id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ket_qua: e.target.value }),
      });
      loadJournal();
    });
  });
  el.querySelectorAll(".del-btn").forEach(btn => {
    btn.addEventListener("click", async e => {
      const id = e.target.closest(".trade-card").dataset.id;
      await fetch(`${API}/api/journal/${id}`, { method: "DELETE" });
      loadJournal();
    });
  });
}

document.getElementById("newTradeBtn").addEventListener("click", () => {
  document.getElementById("tradeForm").classList.toggle("hidden");
});
document.getElementById("cancelTradeBtn").addEventListener("click", () => {
  document.getElementById("tradeForm").classList.add("hidden");
});
document.getElementById("tradeForm").addEventListener("submit", async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = Object.fromEntries(fd.entries());
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
  "Thoát khi lý do vào không còn (RSI cắt xuống 45 / form sell ở khung tương ứng).",
  "Giữ kỷ luật, nhất quán với gu rủi ro của mình — ghi lại vào Nhật ký.",
];

function todayKey() { return "lsteven-process-" + new Date().toISOString().slice(0, 10); }
function renderProcess() {
  const saved = JSON.parse(localStorage.getItem(todayKey()) || "{}");
  const el = document.getElementById("processList");
  el.innerHTML = PROCESS_STEPS.map((step, i) => `
    <li class="process-item ${saved[i] ? "done" : ""}" data-i="${i}">
      <input type="checkbox" ${saved[i] ? "checked" : ""} aria-label="Bước ${i + 1}">
      <span class="step-no">${String(i + 1).padStart(2, "0")}</span>
      <span class="step-text">${step}</span>
    </li>
  `).join("");
  el.querySelectorAll('input[type=checkbox]').forEach(cb => {
    cb.addEventListener("change", () => {
      const li = cb.closest(".process-item");
      li.classList.toggle("done", cb.checked);
      const s = JSON.parse(localStorage.getItem(todayKey()) || "{}");
      s[li.dataset.i] = cb.checked;
      localStorage.setItem(todayKey(), JSON.stringify(s));
    });
  });
}

// ------------------------------------------------------------------ init
loadSnapshot();
loadJournal();
renderProcess();

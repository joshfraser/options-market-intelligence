/**
 * Crypto Derivatives Market Intelligence Dashboard
 *
 * Reads DASHBOARD_DATA from data.js and renders all charts and tables.
 */

// ── Color palette ──────────────────────────────────────────────────
const COLORS = {
    "Hyperliquid": "#77E0B5",
    "Lighter": "#FFD700",
    "dYdX": "#6966FF",
    "GMX": "#4690D6",
    "Vertex": "#8B5CF6",
    "Jupiter Perps": "#C4A0FF",
    "Drift": "#34D399",
    "Kwenta": "#F59E0B",
    "ApeX": "#EF4444",
    "Gains Network": "#22D3EE",
    "Synthetix": "#2563EB",
    "Aevo": "#F97316",
    "Bluefin": "#3B82F6",
    "RabbitX": "#EC4899",
    "Deribit": "#13C684",
    "Lyra": "#A78BFA",
    "Hegic": "#F472B6",
    "Premia": "#FB923C",
    "Thetanuts": "#38BDF8",
    "Opyn": "#FDE047",
    "Derive": "#C084FC",
    "Moby": "#67E8F9",
    "Ithaca": "#FCA5A5",
    "Stryke": "#BEF264",
    "Typus": "#FDA4AF",
    "Zeta Markets": "#93C5FD",
    "Polymarket": "#2C5BF4",
    "Kalshi": "#FF6B35",
    "Others": "#6B7280",
};

const FALLBACK_COLORS = [
    "#4a8eff", "#34d399", "#fbbf24", "#f87171", "#a78bfa",
    "#22d3ee", "#fb923c", "#f472b6", "#818cf8", "#2dd4bf",
    "#e879f9", "#84cc16", "#facc15", "#38bdf8", "#c084fc",
];

function getColor(name, idx) {
    return COLORS[name] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
}

// ── Formatters ─────────────────────────────────────────────────────
function fmtUSD(val) {
    if (val === null || val === undefined) return "—";
    const abs = Math.abs(val);
    if (abs >= 1e12) return "$" + (val / 1e12).toFixed(2) + "T";
    if (abs >= 1e9) return "$" + (val / 1e9).toFixed(2) + "B";
    if (abs >= 1e6) return "$" + (val / 1e6).toFixed(2) + "M";
    if (abs >= 1e3) return "$" + (val / 1e3).toFixed(1) + "K";
    return "$" + val.toFixed(0);
}

function fmtNum(val) {
    if (val === null || val === undefined) return "—";
    return val.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function fmtPct(val) {
    if (val === null || val === undefined) return "—";
    const sign = val > 0 ? "+" : "";
    return sign + val.toFixed(1) + "%";
}

// ── Chart defaults ─────────────────────────────────────────────────
Chart.defaults.color = "#8b8fa3";
Chart.defaults.borderColor = "#2a2d3e";
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyleWidth = 8;
Chart.defaults.plugins.legend.labels.padding = 16;
Chart.defaults.plugins.tooltip.backgroundColor = "#1e2130";
Chart.defaults.plugins.tooltip.borderColor = "#2a2d3e";
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.titleColor = "#e4e6f0";
Chart.defaults.plugins.tooltip.bodyColor = "#8b8fa3";
Chart.defaults.plugins.tooltip.padding = 12;

// ── Chart registry (for time filter updates) ──────────────────────
const chartInstances = {};
const chartDataStore = {};

// ── CSV Export ──────────────────────────────────────────────────────
function exportTimeseriesCSV(chartId, filename) {
    const store = chartDataStore[chartId];
    if (!store) return;
    const { dates, series } = store;
    const names = Object.keys(series);
    const header = ["Date", ...names].join(",");
    const rows = dates.map((d, i) =>
        [d, ...names.map(n => series[n][i] ?? "")].join(",")
    );
    downloadCSV([header, ...rows].join("\n"), filename);
}

function exportTableCSV(tableId, filename) {
    const table = document.querySelector(`#${tableId} table`);
    if (!table) return;
    const rows = [];
    table.querySelectorAll("tr").forEach(tr => {
        const cells = [];
        tr.querySelectorAll("th, td").forEach(td => cells.push('"' + td.textContent.trim().replace(/"/g, '""') + '"'));
        rows.push(cells.join(","));
    });
    downloadCSV(rows.join("\n"), filename);
}

function downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
}

// ── Tab navigation ─────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
});

// ── Time filters ───────────────────────────────────────────────────
document.querySelectorAll(".time-filter").forEach(filterGroup => {
    filterGroup.querySelectorAll(".tf-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            filterGroup.querySelectorAll(".tf-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const chartId = filterGroup.dataset.chart;
            const range = parseInt(btn.dataset.range);
            applyTimeFilter(chartId, range);
        });
    });
});

function applyTimeFilter(chartId, days) {
    const chart = chartInstances[chartId];
    const store = chartDataStore[chartId];
    if (!chart || !store) return;

    let { dates, series } = store;
    if (days > 0) {
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - days);
        const cutoffStr = cutoff.toISOString().split("T")[0];
        const startIdx = dates.findIndex(d => d >= cutoffStr);
        if (startIdx > 0) {
            dates = dates.slice(startIdx);
            series = {};
            for (const [name, vals] of Object.entries(store.series)) {
                series[name] = vals.slice(startIdx);
            }
        }
    }

    chart.data.labels = dates;
    chart.data.datasets.forEach(ds => {
        if (series[ds.label]) {
            ds.data = series[ds.label];
        }
    });
    chart.update("none");
}

// ── Chart builders ─────────────────────────────────────────────────
function buildStackedArea(canvasId, timeseries, title, defaultRange) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !timeseries || !timeseries.dates || timeseries.dates.length === 0) return;

    // Store full data for time filtering
    chartDataStore[canvasId] = timeseries;

    // Apply default range
    let { dates, series } = timeseries;
    if (defaultRange > 0) {
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - defaultRange);
        const cutoffStr = cutoff.toISOString().split("T")[0];
        const startIdx = dates.findIndex(d => d >= cutoffStr);
        if (startIdx > 0) {
            dates = dates.slice(startIdx);
            series = {};
            for (const [name, vals] of Object.entries(timeseries.series)) {
                series[name] = vals.slice(startIdx);
            }
        }
    }

    const datasets = Object.entries(series).map(([name, vals], idx) => ({
        label: name,
        data: vals,
        backgroundColor: getColor(name, idx) + "CC",
        borderColor: getColor(name, idx),
        borderWidth: 1,
        fill: true,
        pointRadius: 0,
        pointHitRadius: 8,
        tension: 0.3,
    }));

    chartInstances[canvasId] = new Chart(ctx, {
        type: "line",
        data: { labels: dates, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            scales: {
                x: {
                    type: "time",
                    time: { unit: "month", tooltipFormat: "MMM d, yyyy" },
                    grid: { display: false },
                    ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 12 },
                },
                y: {
                    stacked: true,
                    grid: { color: "#2a2d3e44" },
                    ticks: {
                        callback: v => fmtUSD(v),
                    },
                },
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: ctx => ctx.dataset.label + ": " + fmtUSD(ctx.parsed.y),
                        footer: items => {
                            const total = items.reduce((sum, item) => sum + (item.parsed.y || 0), 0);
                            return "Total: " + fmtUSD(total);
                        },
                    },
                    footerFont: { weight: "bold" },
                    footerColor: "#e4e6f0",
                },
                legend: {
                    position: "bottom",
                },
            },
        },
    });
}

function buildDoughnut(canvasId, shareData, title) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !shareData || Object.keys(shareData).length === 0) return;

    const labels = Object.keys(shareData);
    const values = Object.values(shareData);
    const colors = labels.map((name, idx) => getColor(name, idx));

    chartInstances[canvasId] = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderColor: "#1e2130",
                borderWidth: 2,
                hoverOffset: 6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "60%",
            plugins: {
                legend: {
                    position: "right",
                    labels: { font: { size: 11 } },
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ctx.label + ": " + ctx.parsed.toFixed(1) + "%",
                    },
                },
            },
        },
    });
}

function buildDoubleDoughnut(canvasId, data1, label1, data2, label2) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    chartInstances[canvasId] = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: [label1 + " (Polymarket)", "Other (Polymarket)", label1 + " (Kalshi)", "Other (Kalshi)"],
            datasets: [{
                label: "Polymarket",
                data: [data1, 100 - data1],
                backgroundColor: ["#2C5BF4", "#2C5BF422"],
                borderColor: "#1e2130",
                borderWidth: 2,
            }, {
                label: "Kalshi",
                data: [data2, 100 - data2],
                backgroundColor: ["#FF6B35", "#FF6B3522"],
                borderColor: "#1e2130",
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "40%",
            plugins: {
                legend: {
                    display: true,
                    position: "bottom",
                    labels: {
                        generateLabels: function(chart) {
                            return [
                                { text: "Polymarket — " + data1.toFixed(1) + "% price", fillStyle: "#2C5BF4", strokeStyle: "#1e2130" },
                                { text: "Kalshi — " + data2.toFixed(1) + "% price", fillStyle: "#FF6B35", strokeStyle: "#1e2130" },
                            ];
                        },
                    },
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ctx.parsed.toFixed(1) + "%",
                    },
                },
            },
        },
    });
}

// ── Metric cards builder ───────────────────────────────────────────
function renderMetricCards(containerId, metrics) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = metrics.map(m => `
        <div class="metric-card">
            <div class="label">${m.label}</div>
            <div class="value">${m.value}</div>
            ${m.change !== undefined ? `<div class="change ${m.change >= 0 ? 'positive' : 'negative'}">${fmtPct(m.change)} 24h</div>` : ""}
        </div>
    `).join("");
}

// ── Table builders ─────────────────────────────────────────────────
function renderPerpsTable(containerId, protocols) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const rows = Object.values(protocols)
        .filter(p => (p.volume24h || 0) > 0 || (p.fees24h || 0) > 0)
        .sort((a, b) => (b.volume24h || 0) - (a.volume24h || 0));

    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Protocol</th>
                    <th class="num">24h Volume</th>
                    <th class="num">7d Volume</th>
                    <th class="num">24h Fees</th>
                    <th class="num">TVL</th>
                    <th class="num">Vol Δ 1d</th>
                </tr>
            </thead>
            <tbody>
                ${rows.map(p => `
                    <tr>
                        <td>${p.displayName}</td>
                        <td class="num">${fmtUSD(p.volume24h)}</td>
                        <td class="num">${fmtUSD(p.volume7d)}</td>
                        <td class="num">${fmtUSD(p.fees24h)}</td>
                        <td class="num">${fmtUSD(p.currentTvl)}</td>
                        <td class="num ${(p.volumeChange1d || 0) >= 0 ? 'positive' : 'negative'}">${p.volumeChange1d != null ? fmtPct(p.volumeChange1d) : '—'}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

function renderOptionsTable(containerId, protocols) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const rows = Object.values(protocols)
        .filter(p => (p.volume24h || 0) > 0 || (p.notionalVolume24h || 0) > 0)
        .sort((a, b) => (b.volume24h || 0) - (a.volume24h || 0));

    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Protocol</th>
                    <th class="num">24h Volume</th>
                    <th class="num">Notional Vol</th>
                    <th class="num">Premium Vol</th>
                    <th class="num">24h Fees</th>
                </tr>
            </thead>
            <tbody>
                ${rows.map(p => `
                    <tr>
                        <td>${p.displayName}</td>
                        <td class="num">${fmtUSD(p.volume24h)}</td>
                        <td class="num">${fmtUSD(p.notionalVolume24h)}</td>
                        <td class="num">${fmtUSD(p.premiumVolume24h)}</td>
                        <td class="num">${fmtUSD(p.fees24h)}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

function renderPredictionTable(containerId, markets, isKalshi) {
    const container = document.getElementById(containerId);
    if (!container || !markets || markets.length === 0) {
        if (container) container.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">No crypto markets found</p>';
        return;
    }

    const header = isKalshi
        ? "<th>Market</th><th class='num'>Volume</th><th class='num'>24h Vol</th><th class='num'>OI</th>"
        : "<th>Market</th><th class='num'>Volume</th><th class='num'>24h Vol</th><th class='num'>Liquidity</th>";

    const rows = markets.map(m => {
        const title = isKalshi ? (m.title + (m.subtitle ? " — " + m.subtitle : "")) : m.question;
        if (isKalshi) {
            return `<tr>
                <td title="${title}">${title.length > 60 ? title.substring(0, 57) + "..." : title}</td>
                <td class="num">${fmtNum(m.volume)}</td>
                <td class="num">${fmtNum(m.volume24h)}</td>
                <td class="num">${fmtNum(m.openInterest)}</td>
            </tr>`;
        }
        return `<tr>
            <td title="${title}">${title.length > 60 ? title.substring(0, 57) + "..." : title}</td>
            <td class="num">${fmtUSD(m.volume)}</td>
            <td class="num">${fmtUSD(m.volume24h)}</td>
            <td class="num">${fmtUSD(m.liquidity)}</td>
        </tr>`;
    }).join("");

    container.innerHTML = `
        <table class="data-table">
            <thead><tr>${header}</tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

// ── Prediction breakdown bars ──────────────────────────────────────
function renderPredictionBars(containerId, poly, kalshi) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const polyTotal = poly.totalVolume || 0;
    const polyCrypto = poly.cryptoVolume || 0;
    const polyPct = polyTotal > 0 ? (polyCrypto / polyTotal * 100) : 0;
    const kalshiTotal = kalshi.totalContracts || 0;
    const kalshiCrypto = kalshi.cryptoContracts || 0;
    const kalshiPct = kalshiTotal > 0 ? (kalshiCrypto / kalshiTotal * 100) : 0;

    container.innerHTML = `
        <div class="pred-bar-row">
            <div class="pred-bar-label">
                <span class="pred-bar-platform" style="color:#2C5BF4">Polymarket</span>
                <span class="pred-bar-vals">${fmtUSD(polyCrypto)} crypto / ${fmtUSD(polyTotal)} total</span>
            </div>
            <div class="pred-bar-track">
                <div class="pred-bar-fill" style="width:${polyPct}%;background:#2C5BF4"></div>
            </div>
            <span class="pred-bar-pct">${polyPct.toFixed(1)}%</span>
        </div>
        <div class="pred-bar-row">
            <div class="pred-bar-label">
                <span class="pred-bar-platform" style="color:#FF6B35">Kalshi</span>
                <span class="pred-bar-vals">${fmtNum(kalshiCrypto)} crypto / ${fmtNum(kalshiTotal)} total contracts</span>
            </div>
            <div class="pred-bar-track">
                <div class="pred-bar-fill" style="width:${kalshiPct}%;background:#FF6B35"></div>
            </div>
            <span class="pred-bar-pct">${kalshiPct.toFixed(1)}%</span>
        </div>
    `;
}

// ── Prediction history chart ───────────────────────────────────────
function buildPredictionHistory(canvasId, history) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !history || history.length === 0) return;

    const dates = history.map(h => h.date);
    const polyVol = history.map(h => h.polymarket?.totalVolume || 0);
    const polyCrypto = history.map(h => h.polymarket?.cryptoVolume || 0);
    const kalshiVol = history.map(h => h.kalshi?.totalContracts || 0);
    const kalshiCrypto = history.map(h => h.kalshi?.cryptoContracts || 0);

    chartInstances[canvasId] = new Chart(ctx, {
        type: "bar",
        data: {
            labels: dates,
            datasets: [
                {
                    label: "Polymarket — Total",
                    data: polyVol,
                    backgroundColor: "#2C5BF4AA",
                    borderColor: "#2C5BF4",
                    borderWidth: 1,
                    yAxisID: "y",
                },
                {
                    label: "Polymarket — Crypto",
                    data: polyCrypto,
                    backgroundColor: "#2C5BF444",
                    borderColor: "#2C5BF4",
                    borderWidth: 1,
                    borderDash: [4, 4],
                    yAxisID: "y",
                },
                {
                    label: "Kalshi — Total (contracts)",
                    data: kalshiVol,
                    backgroundColor: "#FF6B35AA",
                    borderColor: "#FF6B35",
                    borderWidth: 1,
                    yAxisID: "y1",
                },
                {
                    label: "Kalshi — Crypto (contracts)",
                    data: kalshiCrypto,
                    backgroundColor: "#FF6B3544",
                    borderColor: "#FF6B35",
                    borderWidth: 1,
                    borderDash: [4, 4],
                    yAxisID: "y1",
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            scales: {
                x: {
                    type: "time",
                    time: { unit: "day", tooltipFormat: "MMM d, yyyy" },
                    grid: { display: false },
                },
                y: {
                    position: "left",
                    title: { display: true, text: "Polymarket ($)", color: "#2C5BF4" },
                    grid: { color: "#2a2d3e44" },
                    ticks: { callback: v => fmtUSD(v) },
                },
                y1: {
                    position: "right",
                    title: { display: true, text: "Kalshi (contracts)", color: "#FF6B35" },
                    grid: { display: false },
                    ticks: { callback: v => fmtNum(v) },
                },
            },
            plugins: {
                legend: { position: "bottom" },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            if (ctx.dataset.yAxisID === "y1") return ctx.dataset.label + ": " + fmtNum(ctx.parsed.y);
                            return ctx.dataset.label + ": " + fmtUSD(ctx.parsed.y);
                        },
                    },
                },
            },
        },
    });
}

// ── Main render function ───────────────────────────────────────────
function render() {
    if (typeof DASHBOARD_DATA === "undefined") {
        document.querySelector("main").innerHTML = `
            <div style="text-align:center;padding:4rem 2rem;color:var(--text-muted);">
                <h2>No Data Available</h2>
                <p>Run <code>python update_data.py</code> to fetch data and generate the dashboard.</p>
            </div>
        `;
        return;
    }

    const D = DASHBOARD_DATA;

    // Last updated + stale warning
    if (D.lastUpdated) {
        const dt = new Date(D.lastUpdated);
        document.getElementById("lastUpdated").textContent =
            "Last updated: " + dt.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
        const hoursOld = (Date.now() - dt.getTime()) / (1000 * 60 * 60);
        if (hoursOld > 24) {
            const banner = document.getElementById("staleBanner");
            if (banner) banner.style.display = "block";
        }
    }

    // ── Overview tab ───────────────────────────────────────────────
    const perpsM = D.perps?.metrics || {};
    const optionsM = D.options?.metrics || {};
    renderMetricCards("overviewCards", [
        { label: "Perps 24h Volume", value: fmtUSD(perpsM.volume24h) },
        { label: "Options 24h Volume", value: fmtUSD(optionsM.volume24h) },
        { label: "Perps 24h Fees", value: fmtUSD(perpsM.fees24h) },
        { label: "Options 24h Fees", value: fmtUSD(optionsM.fees24h) },
        { label: "Perps TVL", value: fmtUSD(perpsM.tvl) },
        { label: "Polymarket Volume", value: fmtUSD(D.predictions?.polymarket?.totalVolume) },
    ]);

    renderInsights("insightsPanel", D);

    buildStackedArea("overviewPerpsVolume", D.perps?.volumeTimeseries, "Perps Volume", 365);
    buildStackedArea("overviewOptionsVolume", D.options?.volumeTimeseries, "Options Volume", 365);
    buildDoughnut("overviewPerpsShare", D.perps?.marketShare);
    buildDoughnut("overviewOptionsShare", D.options?.marketShare);

    // ── Perps tab ──────────────────────────────────────────────────
    renderMetricCards("perpsCards", [
        { label: "24h Volume", value: fmtUSD(perpsM.volume24h) },
        { label: "24h Fees", value: fmtUSD(perpsM.fees24h) },
        { label: "24h Revenue", value: fmtUSD(perpsM.revenue24h) },
        { label: "Total TVL", value: fmtUSD(perpsM.tvl) },
    ]);

    buildStackedArea("perpsVolume", D.perps?.volumeTimeseries, "Volume", 365);
    buildStackedArea("perpsFees", D.perps?.feesTimeseries, "Fees", 365);
    buildStackedArea("perpsRevenue", D.perps?.revenueTimeseries, "Revenue", 365);
    buildStackedArea("perpsTvl", D.perps?.tvlTimeseries, "TVL", 365);
    buildDoughnut("perpsShareChart", D.perps?.marketShare);
    renderPerpsTable("perpsTable", D.perps?.protocols || {});

    // ── Options tab ────────────────────────────────────────────────
    renderMetricCards("optionsCards", [
        { label: "24h Volume", value: fmtUSD(optionsM.volume24h) },
        { label: "24h Fees", value: fmtUSD(optionsM.fees24h) },
        { label: "24h Revenue", value: fmtUSD(optionsM.revenue24h) },
    ]);

    buildStackedArea("optionsVolume", D.options?.volumeTimeseries, "Volume", 365);
    buildStackedArea("optionsFees", D.options?.feesTimeseries, "Fees", 365);
    buildStackedArea("optionsRevenue", D.options?.revenueTimeseries, "Revenue", 365);
    buildDoughnut("optionsShareChart", D.options?.marketShare);
    renderOptionsTable("optionsTable", D.options?.protocols || {});

    // ── Prediction Markets tab ─────────────────────────────────────
    const poly = D.predictions?.polymarket || {};
    const kalshi = D.predictions?.kalshi || {};

    renderMetricCards("predictionsCards", [
        { label: "Polymarket Total Volume", value: fmtUSD(poly.totalVolume) },
        { label: "Polymarket Crypto Volume", value: fmtUSD(poly.cryptoVolume) },
        { label: "Polymarket Crypto %", value: (poly.pricePredictionPct || 0).toFixed(1) + "%" },
        { label: "Kalshi Total Contracts", value: fmtNum(kalshi.totalContracts) },
        { label: "Kalshi Crypto %", value: (kalshi.cryptoPct || 0).toFixed(1) + "%" },
        { label: "Kalshi Price Pred %", value: (kalshi.pricePredictionPct || 0).toFixed(1) + "%" },
    ]);

    // Volume breakdown bars
    renderPredictionBars("predictionBars", poly, kalshi);

    buildDoughnut("predShareChart", D.predictionMarketShare);

    // Price prediction percentage chart
    buildDoubleDoughnut(
        "predPricePct",
        poly.pricePredictionPct || 0, "Price Predictions",
        kalshi.pricePredictionPct || 0, "Price Predictions"
    );

    // Prediction history
    buildPredictionHistory("predHistory", D.predictionHistory || []);

    // Tables
    renderPredictionTable("polymarketTable", poly.topCryptoMarkets, false);
    renderPredictionTable("kalshiTable", kalshi.topCryptoMarkets, true);
}

// ── Key Insights Generator ──────────────────────────────────────────
function generateInsights(D) {
    const insights = [];
    const perps = D.perps || {};
    const options = D.options || {};
    const pred = D.predictions || {};

    // Top perps protocol by market share
    if (perps.marketShare) {
        const top = Object.entries(perps.marketShare).sort((a, b) => b[1] - a[1])[0];
        if (top) insights.push({ icon: "chart", text: `<strong>${top[0]}</strong> leads perps with ${top[1].toFixed(1)}% market share by 24h volume` });
    }

    // Top options protocol
    if (options.marketShare) {
        const top = Object.entries(options.marketShare).sort((a, b) => b[1] - a[1])[0];
        if (top) insights.push({ icon: "chart", text: `<strong>${top[0]}</strong> dominates options with ${top[1].toFixed(1)}% market share` });
    }

    // Perps vs options volume ratio
    const perpsVol = perps.metrics?.volume24h;
    const optionsVol = options.metrics?.volume24h;
    if (perpsVol && optionsVol && optionsVol > 0) {
        const ratio = perpsVol / optionsVol;
        insights.push({ icon: "scale", text: `Perps volume is <strong>${ratio.toFixed(0)}x</strong> options volume (${fmtUSD(perpsVol)} vs ${fmtUSD(optionsVol)})` });
    }

    // Prediction market crypto percentage
    const polyPct = pred.polymarket?.pricePredictionPct;
    const kalshiPct = pred.kalshi?.pricePredictionPct;
    if (polyPct != null) {
        insights.push({ icon: "trend", text: `Crypto price predictions are <strong>${polyPct.toFixed(1)}%</strong> of Polymarket volume` });
    }
    if (kalshiPct != null) {
        insights.push({ icon: "trend", text: `Crypto price predictions are <strong>${kalshiPct.toFixed(1)}%</strong> of Kalshi volume` });
    }

    // Fee/volume ratio (take rate) for perps
    const perpsFees = perps.metrics?.fees24h;
    if (perpsFees && perpsVol && perpsVol > 0) {
        const takeRate = (perpsFees / perpsVol) * 100;
        insights.push({ icon: "fee", text: `Perps average take rate: <strong>${takeRate.toFixed(3)}%</strong> (${fmtUSD(perpsFees)} fees on ${fmtUSD(perpsVol)} volume)` });
    }

    // Volume trend (30d vs prior 30d from timeseries)
    if (perps.volumeTimeseries?.dates?.length > 60) {
        const ts = perps.volumeTimeseries;
        const len = ts.dates.length;
        const sumRange = (start, end) => {
            let total = 0;
            for (const vals of Object.values(ts.series)) {
                for (let i = start; i < end; i++) total += (vals[i] || 0);
            }
            return total;
        };
        const recent = sumRange(len - 30, len);
        const prior = sumRange(len - 60, len - 30);
        if (prior > 0) {
            const growth = ((recent - prior) / prior) * 100;
            const dir = growth >= 0 ? "up" : "down";
            insights.push({ icon: dir === "up" ? "up" : "down", text: `Perps 30d volume <strong>${dir} ${Math.abs(growth).toFixed(1)}%</strong> vs prior 30 days` });
        }
    }

    return insights;
}

function renderInsights(containerId, D) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const insights = generateInsights(D);
    if (insights.length === 0) return;

    const iconMap = { chart: "&#x25C9;", scale: "&#x2696;", trend: "&#x2197;", fee: "&#x25B3;", up: "&#x25B2;", down: "&#x25BC;" };
    container.innerHTML = `
        <h3 class="insights-title">Key Insights</h3>
        <div class="insights-grid">
            ${insights.map(i => `
                <div class="insight-item">
                    <span class="insight-icon">${iconMap[i.icon] || "&#x25CF;"}</span>
                    <span>${i.text}</span>
                </div>
            `).join("")}
        </div>
    `;
}

// ── Export buttons ──────────────────────────────────────────────────
function addExportButtons() {
    const chartExports = [
        { chart: "perpsVolume", label: "Perps Volume", file: "perps_volume.csv" },
        { chart: "perpsFees", label: "Perps Fees", file: "perps_fees.csv" },
        { chart: "perpsRevenue", label: "Perps Revenue", file: "perps_revenue.csv" },
        { chart: "perpsTvl", label: "Perps TVL", file: "perps_tvl.csv" },
        { chart: "optionsVolume", label: "Options Volume", file: "options_volume.csv" },
        { chart: "optionsFees", label: "Options Fees", file: "options_fees.csv" },
        { chart: "optionsRevenue", label: "Options Revenue", file: "options_revenue.csv" },
    ];

    chartExports.forEach(({ chart, file }) => {
        const canvas = document.getElementById(chart);
        if (!canvas) return;
        const card = canvas.closest(".chart-card");
        if (!card) return;
        const btn = document.createElement("button");
        btn.className = "export-btn";
        btn.textContent = "CSV";
        btn.title = "Export data as CSV";
        btn.addEventListener("click", () => exportTimeseriesCSV(chart, file));
        card.appendChild(btn);
    });

    const tableExports = [
        { table: "perpsTable", file: "perps_protocols.csv" },
        { table: "optionsTable", file: "options_protocols.csv" },
        { table: "polymarketTable", file: "polymarket_crypto.csv" },
        { table: "kalshiTable", file: "kalshi_crypto.csv" },
    ];

    tableExports.forEach(({ table, file }) => {
        const container = document.getElementById(table);
        if (!container) return;
        const card = container.closest(".chart-card");
        if (!card) return;
        const btn = document.createElement("button");
        btn.className = "export-btn";
        btn.textContent = "CSV";
        btn.title = "Export table as CSV";
        btn.addEventListener("click", () => exportTableCSV(table, file));
        card.appendChild(btn);
    });
}

// ── Initialize ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    render();
    addExportButtons();
});

/* Search Intelligence Analyzer
   Main app logic:
   - Load CSV data
   - Store and query data with sql.js (SQLite in browser)
   - Compute KPI metrics
   - Render charts
   - Generate insights and PM recommendations
*/

let SQL;
let db;
let rawRows = [];
let charts = {
  failed: null,
  ctr: null,
  trends: null
};

const PREBUILT_QUERIES = {
  // Queries with zero results and no clicks suggest catalog or matching issues.
  zeroResults: `
    SELECT query, COUNT(*) AS searches
    FROM search_logs
    WHERE results_count = 0
    GROUP BY query
    ORDER BY searches DESC
    LIMIT 20;
  `,
  // Low CTR despite results often indicates ranking quality or intent mismatch.
  lowCtr: `
    SELECT
      query,
      ROUND(AVG(CASE WHEN results_count > 0 THEN clicks * 1.0 / results_count ELSE 0 END), 3) AS avg_ctr,
      COUNT(*) AS searches
    FROM search_logs
    GROUP BY query
    HAVING searches >= 2 AND avg_ctr < 0.08
    ORDER BY avg_ctr ASC, searches DESC
    LIMIT 20;
  `,
  // Frequently searched terms show what users care about most.
  mostSearched: `
    SELECT query, COUNT(*) AS searches
    FROM search_logs
    GROUP BY query
    ORDER BY searches DESC
    LIMIT 20;
  `,
  // Approximate reformulations: same day, same user intent chain (simulated via timestamps and similar prefix).
  reformulations: `
    SELECT a.query AS original_query, b.query AS reformulated_query, COUNT(*) AS occurrences
    FROM search_logs a
    JOIN search_logs b
      ON DATE(a.timestamp) = DATE(b.timestamp)
     AND a.query != b.query
     AND SUBSTR(a.query, 1, 3) = SUBSTR(b.query, 1, 3)
    GROUP BY original_query, reformulated_query
    HAVING occurrences >= 2
    ORDER BY occurrences DESC
    LIMIT 20;
  `
};

document.addEventListener("DOMContentLoaded", async () => {
  await initSqlJsEngine();
  wireEvents();
});

async function initSqlJsEngine() {
  try {
    SQL = await initSqlJs({
      // sql.js loads WebAssembly runtime from this CDN location.
      locateFile: (file) =>
        `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${file}`
    });
    db = new SQL.Database();
    setStatus("SQL engine loaded. Upload CSV to start.");
  } catch (error) {
    setStatus("Failed to load SQL engine. Check internet connection.");
    console.error(error);
  }
}

function wireEvents() {
  document.getElementById("csvFileInput").addEventListener("change", handleCsvUpload);
  document.getElementById("loadSampleBtn").addEventListener("click", loadSampleData);

  document.querySelectorAll(".query-btn").forEach((button) => {
    button.addEventListener("click", () => runPrebuiltQuery(button.dataset.query));
  });
}

async function handleCsvUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const text = await file.text();
  parseAndLoadCsv(text);
}

async function loadSampleData() {
  try {
    const response = await fetch("./data/sample.csv");
    const text = await response.text();
    parseAndLoadCsv(text);
  } catch (error) {
    setStatus("Could not load sample CSV. Verify file path data/sample.csv.");
    console.error(error);
  }
}

function parseAndLoadCsv(csvText) {
  const rows = parseCsv(csvText);
  if (!rows.length) {
    setStatus("CSV is empty or invalid.");
    return;
  }

  const requiredColumns = ["query", "results_count", "clicks", "timestamp"];
  const headerKeys = Object.keys(rows[0]);
  const missing = requiredColumns.filter((c) => !headerKeys.includes(c));
  if (missing.length) {
    setStatus(`Missing required columns: ${missing.join(", ")}`);
    return;
  }

  rawRows = rows.map((row) => ({
    query: String(row.query || "").trim().toLowerCase(),
    results_count: Number(row.results_count) || 0,
    clicks: Number(row.clicks) || 0,
    timestamp: String(row.timestamp || "").trim()
  }));

  rebuildDatabase(rawRows);
  renderKpis(rawRows);
  renderCharts(rawRows);
  renderInsights(rawRows);
  runPrebuiltQuery("zeroResults");
  setStatus(`Loaded ${rawRows.length} rows successfully.`);
}

function parseCsv(text) {
  const lines = text
    .trim()
    .split(/\r?\n/)
    .filter(Boolean);

  if (lines.length < 2) return [];

  const headers = lines[0].split(",").map((h) => h.trim());
  const records = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(",").map((v) => v.trim());
    if (values.length !== headers.length) continue;
    const row = {};
    headers.forEach((h, idx) => {
      row[h] = values[idx];
    });
    records.push(row);
  }

  return records;
}

function rebuildDatabase(rows) {
  // Re-create database each load to keep data in sync with latest upload.
  db = new SQL.Database();
  db.run(`
    CREATE TABLE search_logs (
      query TEXT,
      results_count INTEGER,
      clicks INTEGER,
      timestamp TEXT
    );
  `);

  const stmt = db.prepare(
    "INSERT INTO search_logs (query, results_count, clicks, timestamp) VALUES (?, ?, ?, ?)"
  );

  db.run("BEGIN TRANSACTION;");
  rows.forEach((row) => {
    stmt.run([row.query, row.results_count, row.clicks, row.timestamp]);
  });
  db.run("COMMIT;");
  stmt.free();
}

function runPrebuiltQuery(queryKey) {
  if (!db || !PREBUILT_QUERIES[queryKey]) return;
  const result = db.exec(PREBUILT_QUERIES[queryKey]);
  renderSqlResult(result);
}

function renderSqlResult(result) {
  const thead = document.querySelector("#queryTable thead");
  const tbody = document.querySelector("#queryTable tbody");
  thead.innerHTML = "";
  tbody.innerHTML = "";

  if (!result.length) {
    thead.innerHTML = "<tr><th>Result</th></tr>";
    tbody.innerHTML = "<tr><td>No rows found.</td></tr>";
    return;
  }

  const cols = result[0].columns;
  const values = result[0].values;

  thead.innerHTML = `<tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr>`;
  tbody.innerHTML = values
    .map((row) => `<tr>${row.map((v) => `<td>${v}</td>`).join("")}</tr>`)
    .join("");
}

function renderKpis(rows) {
  const total = rows.length || 1;
  const zeroResultCount = rows.filter((r) => r.results_count === 0).length;
  const abandonedCount = rows.filter((r) => r.clicks === 0).length;

  const ctrValues = rows.map((r) =>
    r.results_count > 0 ? r.clicks / r.results_count : 0
  );
  const avgCtr = ctrValues.reduce((sum, value) => sum + value, 0) / total;

  document.getElementById("zeroResultRate").textContent = `${toPercent(
    zeroResultCount / total
  )}`;
  document.getElementById("averageCtr").textContent = `${toPercent(avgCtr)}`;
  document.getElementById("abandonmentRate").textContent = `${toPercent(
    abandonedCount / total
  )}`;
}

function renderCharts(rows) {
  renderFailedQueriesChart(rows);
  renderCtrDistributionChart(rows);
  renderSearchTrendsChart(rows);
}

function renderFailedQueriesChart(rows) {
  const failedMap = new Map();
  rows
    .filter((r) => r.results_count === 0)
    .forEach((r) => failedMap.set(r.query, (failedMap.get(r.query) || 0) + 1));

  const top = [...failedMap.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const labels = top.map((item) => item[0]);
  const data = top.map((item) => item[1]);

  if (charts.failed) charts.failed.destroy();
  charts.failed = new Chart(document.getElementById("failedQueriesChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Zero-result searches",
          data,
          backgroundColor: "rgba(251, 113, 133, 0.75)"
        }
      ]
    },
    options: baseChartOptions()
  });
}

function renderCtrDistributionChart(rows) {
  const buckets = {
    "0-5%": 0,
    "5-15%": 0,
    "15-30%": 0,
    "30%+": 0
  };

  rows.forEach((r) => {
    const ctr = r.results_count > 0 ? r.clicks / r.results_count : 0;
    if (ctr < 0.05) buckets["0-5%"] += 1;
    else if (ctr < 0.15) buckets["5-15%"] += 1;
    else if (ctr < 0.3) buckets["15-30%"] += 1;
    else buckets["30%+"] += 1;
  });

  if (charts.ctr) charts.ctr.destroy();
  charts.ctr = new Chart(document.getElementById("ctrDistributionChart"), {
    type: "doughnut",
    data: {
      labels: Object.keys(buckets),
      datasets: [
        {
          label: "Query count",
          data: Object.values(buckets),
          backgroundColor: ["#f43f5e", "#f59e0b", "#60a5fa", "#4ade80"]
        }
      ]
    },
    options: baseChartOptions()
  });
}

function renderSearchTrendsChart(rows) {
  const dayMap = new Map();
  rows.forEach((r) => {
    const day = r.timestamp.slice(0, 10);
    dayMap.set(day, (dayMap.get(day) || 0) + 1);
  });

  const sortedDays = [...dayMap.keys()].sort();
  const series = sortedDays.map((day) => dayMap.get(day));

  if (charts.trends) charts.trends.destroy();
  charts.trends = new Chart(document.getElementById("searchTrendsChart"), {
    type: "line",
    data: {
      labels: sortedDays,
      datasets: [
        {
          label: "Searches per day",
          data: series,
          borderColor: "#6ea8fe",
          backgroundColor: "rgba(110, 168, 254, 0.2)",
          fill: true,
          tension: 0.25
        }
      ]
    },
    options: baseChartOptions()
  });
}

function renderInsights(rows) {
  // Insight categories are heuristic and can be expanded for real systems.
  const groups = {
    misspellings: detectMisspellings(rows),
    brandMismatch: detectBrandMismatch(rows),
    outOfStock: detectOutOfStock(rows)
  };

  const insightContainer = document.getElementById("insightGroups");
  insightContainer.innerHTML = "";

  const issueConfig = [
    {
      key: "misspellings",
      title: "Misspellings / query quality issues",
      items: groups.misspellings
    },
    {
      key: "brandMismatch",
      title: "Brand mismatch",
      items: groups.brandMismatch
    },
    {
      key: "outOfStock",
      title: "Out-of-stock intent",
      items: groups.outOfStock
    }
  ];

  issueConfig.forEach((group) => {
    const card = document.createElement("article");
    card.className = "issue-card";
    const listHtml = group.items.length
      ? `<ul class="issue-list">${group.items
          .slice(0, 6)
          .map((item) => `<li>${item}</li>`)
          .join("")}</ul>`
      : '<p class="issue-list">No major patterns detected.</p>';
    card.innerHTML = `<h4>${group.title}</h4>${listHtml}`;
    insightContainer.appendChild(card);
  });

  renderRecommendations(groups);
}

function detectMisspellings(rows) {
  const typoTokens = ["iphon", "nikke", "samsng", "hedfone", "nikonn"];
  const flagged = rows
    .filter((r) => typoTokens.some((token) => r.query.includes(token)))
    .map((r) => `${r.query} (searches: ${countQuery(rows, r.query)})`);
  return [...new Set(flagged)];
}

function detectBrandMismatch(rows) {
  const brands = ["nike", "adidas", "apple", "samsung", "sony"];
  const mismatches = rows
    .filter((r) => {
      const hasBrand = brands.some((brand) => r.query.includes(brand));
      return hasBrand && r.results_count > 0 && r.clicks === 0;
    })
    .map((r) => `${r.query} (results shown but no clicks)`);
  return [...new Set(mismatches)];
}

function detectOutOfStock(rows) {
  const stockTerms = ["out of stock", "restock", "unavailable"];
  const outStock = rows
    .filter(
      (r) =>
        stockTerms.some((term) => r.query.includes(term)) ||
        (r.results_count === 0 && r.query.includes("size"))
    )
    .map((r) => `${r.query} (results: ${r.results_count})`);
  return [...new Set(outStock)];
}

function renderRecommendations(groups) {
  const recommendationList = document.getElementById("recommendationList");
  recommendationList.innerHTML = "";

  const recommendations = [];

  if (groups.misspellings.length) {
    recommendations.push({
      title: "Add synonym mapping and typo tolerance",
      detail:
        "Configure search dictionary for common misspellings and near-match terms to improve recall.",
      impact: "+8% to +12% CTR on typo traffic"
    });
  }

  if (groups.brandMismatch.length) {
    recommendations.push({
      title: "Improve catalog tagging and brand ranking",
      detail:
        "Audit product metadata and ranking rules so branded queries show exact-brand products first.",
      impact: "+6% to +10% CTR on branded queries"
    });
  }

  if (groups.outOfStock.length) {
    recommendations.push({
      title: "Introduce in-stock filters and alternatives",
      detail:
        "Surface in-stock alternatives, notify users about restock, and expose availability facets in search.",
      impact: "-7% abandonment, +5% conversion"
    });
  }

  if (!recommendations.length) {
    recommendations.push({
      title: "No critical issues detected",
      detail:
        "Current dataset looks healthy. Expand dataset size for stronger confidence in findings.",
      impact: "Baseline maintained"
    });
  }

  recommendations.forEach((rec) => {
    const card = document.createElement("article");
    card.className = "recommendation-card";
    card.innerHTML = `
      <h4>${rec.title}</h4>
      <p>${rec.detail}</p>
      <p class="impact">Estimated impact: ${rec.impact}</p>
    `;
    recommendationList.appendChild(card);
  });
}

function countQuery(rows, query) {
  return rows.filter((r) => r.query === query).length;
}

function toPercent(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function setStatus(message) {
  document.getElementById("uploadStatus").textContent = message;
}

function baseChartOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: "#dbe7ff"
        }
      }
    },
    scales: {
      x: {
        ticks: { color: "#aac0ea" },
        grid: { color: "rgba(180, 198, 237, 0.08)" }
      },
      y: {
        ticks: { color: "#aac0ea" },
        grid: { color: "rgba(180, 198, 237, 0.08)" }
      }
    }
  };
}

# Search Intelligence Analyzer - E-commerce Product Analytics Tool

This is a web-based PM + product-engineering portfolio project that analyzes search behavior to understand why users search but do not click.

It runs fully in the browser (no backend).

## Tech Stack

- HTML, CSS, JavaScript (no frameworks)
- sql.js (SQLite in the browser)
- Chart.js for charts
- CSV file as input data

## Project File Structure

- `index.html`  
  Main UI layout: upload section, KPI cards, SQL query controls, chart containers, insights and recommendation sections.

- `style.css`  
  Dashboard styling with a dark analytics theme, responsive grid layout, table/card styles.

- `script.js`  
  App logic:
  - CSV parsing
  - In-browser SQLite table creation with sql.js
  - Pre-built SQL query execution
  - KPI calculations
  - Chart.js rendering
  - Insight detection (misspellings, brand mismatch, out-of-stock intent)
  - PM recommendation generation with estimated impact

- `data/sample.csv`  
  Mock search logs with columns:
  `query,results_count,clicks,timestamp`

## How to Create This Project (Beginner Friendly)

You can do this using Notepad (Windows), TextEdit (Mac in plain text mode), or online editors like Replit.

1. Create a folder named `Search-Intelligence-Analyzer`.
2. Inside it, create these files:
   - `index.html`
   - `style.css`
   - `script.js`
3. Create a subfolder named `data`.
4. Inside `data`, create `sample.csv`.
5. Copy/paste the code from each file into the matching file.
6. Save all files.

## How to Run in Browser

Because this app fetches `data/sample.csv`, use a simple local server (recommended).

### Option A: Browser-based editor (easiest)

- Upload the folder to Replit or CodeSandbox.
- Click "Run".
- Open the preview URL.

### Option B: Python local server (if Python is installed)

1. Open terminal/command prompt in the project folder.
2. Run:
   - `python -m http.server 8000`
3. Open browser and go to:
   - `http://localhost:8000`

### Option C: Open file directly

- You can open `index.html` directly, but sample CSV auto-load might not work in some browsers due to local file security.
- In that case, use the Upload button and select `data/sample.csv` manually.

## Using the App

1. Click **Load Sample Data** (or upload your own CSV).
2. View KPI cards:
   - Zero Result Rate
   - Average CTR
   - Abandonment Rate
3. Run built-in SQL queries:
   - Zero result queries
   - Low CTR queries
   - Most searched queries
   - Query reformulations
4. Review charts for failed terms, CTR spread, and search trends.
5. Read auto-generated insight groups + PM recommendations.

## GitHub Deployment (No Git Commands Required)

### Step 1: Create GitHub Repository

1. Go to [https://github.com](https://github.com) and log in.
2. Click **New repository**.
3. Repository name: `search-intelligence-analyzer`
4. Set to **Public**.
5. Click **Create repository**.

### Step 2: Upload Project Files Manually

1. In your new repo page, click **uploading an existing file**.
2. Drag and drop:
   - `index.html`
   - `style.css`
   - `script.js`
   - `README.md`
   - `data` folder (with `sample.csv`)
3. Add commit message: `Initial portfolio project`.
4. Click **Commit changes**.

### Step 3: Enable GitHub Pages

1. Open repository **Settings**.
2. In left menu, click **Pages**.
3. Under **Build and deployment**:
   - Source: `Deploy from a branch`
   - Branch: `main` and folder `/ (root)`
4. Click **Save**.

### Step 4: Get Live URL

After 1-3 minutes, GitHub shows your live link:

`https://your-username.github.io/search-intelligence-analyzer/`

Use this link in your resume, LinkedIn, and portfolio.

## Portfolio Positioning Tip

In your portfolio description, mention:

- "Built a front-end analytics app to diagnose search-to-click drop-offs"
- "Used in-browser SQL and rule-based insights to simulate PM decision workflows"
- "Generated actionable recommendations with estimated KPI impact"

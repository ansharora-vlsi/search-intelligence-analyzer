# Search Intelligence Analyzer - E-commerce Product Analytics Tool

Search Intelligence Analyzer is a Python/Dash portfolio project that diagnoses why e-commerce users search but fail to click or add items to cart.

The app ingests simulated search logs, segments performance by category and device, compares pre-launch vs post-launch behavior, and maps low-performing queries to product hypotheses a PM can act on.

## Resume-Ready Highlights

- Computes `CTR`, `Search-to-Cart Ratio`, `Zero Result Rate`, and `Query Reformulation Rate`
- Supports interactive filtering by `date range`, `category`, `device type`, and `launch cohort`
- Includes a root-cause analysis module for low-performing queries
- Compares `pre_launch` vs `post_launch` cohorts with simple statistical significance testing
- Optional **Google Gemini** narrative summaries over the currently filtered slice (API key via environment variable)
- Built in `Python`, `Dash`, `Pandas`, and `Plotly`

## Tech Stack

- Python
- Dash
- Pandas
- Plotly
- CSV as the underlying mock event dataset

## Project Structure

- `app.py`  
  Main Dash entrypoint. Defines layout, upload flow, filters, KPI cards, charts, tables, and callbacks.

- `analytics.py`  
  Analytics logic for filtering, KPI calculation, cohort summaries, root-cause analysis, and pre/post launch significance testing.

- `assets/style.css`  
  Styling for the Dash app with a premium dark dashboard theme.

- `data/sample.csv`  
  Enriched mock search-event dataset with:
  - `session_id`
  - `timestamp`
  - `query`
  - `query_group`
  - `category`
  - `brand`
  - `device_type`
  - `results_count`
  - `clicks`
  - `adds_to_cart`
  - `feature_flag`

- `requirements.txt`  
  Python dependencies needed to run the app.

- `gemini_insights.py`  
  Optional Gemini summarization helper. If `GEMINI_API_KEY` is not set, the UI falls back to an offline template.

## What the Dashboard Shows

### KPI Cards

- CTR
- Search-to-Cart Ratio
- Zero Result Rate
- Reformulation Rate

### Interactive Filters

- Date range
- Category
- Device type
- Launch cohort (`pre_launch`, `post_launch`)

### Visual Analytics

- Metric trend over time
- CTR by device
- Search-to-cart ratio by category
- Root-cause issue summary

### Root-Cause Analysis

The app detects and groups issues such as:

- Zero-result queries
- Misspelling friction
- Inventory mismatch
- Low engagement despite available results

It also maps each issue to:

- a likely product hypothesis
- a PM-style recommendation

### Feature-Impact Testing

When both `pre_launch` and `post_launch` data are selected, the app runs a simple two-proportion z-test to compare:

- Click-through rate
- Search-to-cart ratio

This helps support claims about whether post-launch improvements are directionally meaningful.

### Gemini Weekly Insight Layer

The dashboard includes a **Generate AI summary** button.

- If `GEMINI_API_KEY` is configured, the app calls Google Gemini to draft a PM-style weekly narrative in Markdown.
- If the key is missing, the panel shows an offline template and explains how to enable Gemini.

## How to Run Locally

### Step 1: Install Python

If Python is not installed yet:

1. Go to [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Download Python 3
3. Install it

### Step 2: Open terminal in the project folder

Go into the project folder where `app.py` exists.

### Step 3: Install dependencies

Run:

```bash
pip install -r requirements.txt
```

### Step 3b: (Optional) Enable Gemini locally

1. Create a Gemini API key in Google AI Studio.
2. Export it in your terminal session (do not paste it into GitHub files):

```bash
export GEMINI_API_KEY="YOUR_KEY_HERE"
# optional override:
export GEMINI_MODEL="gemini-2.0-flash"
```

### Step 4: Start the dashboard

Run:

```bash
python app.py
```

### Step 5: Open in browser

Open:

`http://127.0.0.1:8050`

## How to Use the Dashboard

1. Run the app locally or on a hosted link(https://search-intelligence-analyzer.onrender.com).
2. Use the bundled sample dataset or upload a CSV with the same schema.
3. Adjust filters for date, category, device, or launch cohort.
4. Review KPI changes across cohorts.
5. Use the low-performing query table and root-cause analysis module to identify issues.
6. Check the feature-impact section to compare pre-launch and post-launch performance.

## Notes

- The dataset is simulated, but structured to resemble real search-event logs.
- The significance testing is intentionally lightweight and educational, not a substitute for a production experimentation platform.
- Never commit API keys. Use host environment variables instead.
nking and implementation skills in one project.

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
  Main UI layout: upload section, KPI cards, SQL query controls, chart containers, insights, and recommendation sections.

- `style.css`  
  Dashboard styling with a dark analytics theme, responsive grid layout, and table/card styles.

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

## Live Demo

[Search Intelligence Analyzer](https://ansharora-vlsi.github.io/search-intelligence-analyzer/)

## Problem

E-commerce users often search but don’t click. This project analyzes search logs to identify why product discovery fails.

## What I Built

- CSV-based search log ingestion
- In-browser SQL engine using SQL.js
- KPI dashboard (Zero Result Rate, Average CTR, Abandonment Rate)
- Chart.js visualizations for failure patterns and trends
- Rule-based insight detection (misspellings, brand mismatch, out-of-stock intent)
- PM recommendation engine with estimated impact

## How to Run

1. Open the live demo link, or run locally with a simple server.
2. Click **Load Sample Data** (or upload your own CSV).
3. Use SQL query buttons to inspect zero-result, low-CTR, and reformulation patterns.
4. Review charts, detected issues, and PM recommendations.

## Outcome

A portfolio-ready analytics tool that demonstrates product thinking and implementation skills in one project.

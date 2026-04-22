"""Analytics helpers for the Dash-based Search Intelligence Analyzer.

This module keeps the product logic separate from the UI layer so the
dashboard remains easier to reason about and extend.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt
from pathlib import Path
from typing import Iterable

import pandas as pd


DATA_PATH = Path(__file__).parent / "data" / "sample.csv"


@dataclass
class TestResult:
    metric_name: str
    baseline_label: str
    variant_label: str
    baseline_rate: float
    variant_rate: float
    lift_pct: float
    p_value: float
    significant: bool
    baseline_n: int
    variant_n: int


def load_search_data(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Load the CSV and normalize types used across the dashboard."""
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date.astype(str)
    df["had_click"] = (df["clicks"] > 0).astype(int)
    df["had_cart"] = (df["adds_to_cart"] > 0).astype(int)
    df["is_zero_result"] = (df["results_count"] == 0).astype(int)
    df["query_length"] = df["query"].str.split().str.len()
    return df


def filter_data(
    df: pd.DataFrame,
    start_date: str | None = None,
    end_date: str | None = None,
    categories: Iterable[str] | None = None,
    devices: Iterable[str] | None = None,
    feature_flags: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Apply UI filters and return a dashboard-ready slice."""
    filtered = df.copy()

    if start_date:
        filtered = filtered[filtered["timestamp"] >= pd.to_datetime(start_date)]
    if end_date:
        filtered = filtered[
            filtered["timestamp"]
            <= pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        ]
    if categories:
        filtered = filtered[filtered["category"].isin(categories)]
    if devices:
        filtered = filtered[filtered["device_type"].isin(devices)]
    if feature_flags:
        filtered = filtered[filtered["feature_flag"].isin(feature_flags)]

    return filtered.reset_index(drop=True)


def compute_kpis(df: pd.DataFrame) -> dict[str, float]:
    """Compute top-level KPI values shown on scorecards."""
    if df.empty:
        return {
            "searches": 0,
            "ctr": 0.0,
            "search_to_cart": 0.0,
            "zero_result_rate": 0.0,
            "reformulation_rate": 0.0,
        }

    searches = len(df)
    ctr = df["had_click"].mean()
    search_to_cart = df["had_cart"].mean()
    zero_result_rate = df["is_zero_result"].mean()

    # Reformulations are proxied by repeated query_group activity per day,
    # which is realistic for search journeys in an event-style dataset.
    group_counts = (
        df.groupby(["date", "query_group"])
        .size()
        .reset_index(name="search_count")
    )
    reformulations = (group_counts["search_count"] > 1).mean() if not group_counts.empty else 0.0

    return {
        "searches": searches,
        "ctr": float(ctr),
        "search_to_cart": float(search_to_cart),
        "zero_result_rate": float(zero_result_rate),
        "reformulation_rate": float(reformulations),
    }


def metric_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    """Daily trend table used by the line chart."""
    if df.empty:
        return pd.DataFrame(columns=["date", "ctr", "search_to_cart", "zero_result_rate"])

    return (
        df.groupby("date")
        .agg(
            searches=("query", "size"),
            ctr=("had_click", "mean"),
            search_to_cart=("had_cart", "mean"),
            zero_result_rate=("is_zero_result", "mean"),
        )
        .reset_index()
    )


def cohort_breakdown(df: pd.DataFrame, group_by: str) -> pd.DataFrame:
    """Summaries for device/category cohort analysis."""
    if df.empty:
        return pd.DataFrame(columns=[group_by, "searches", "ctr", "search_to_cart", "zero_result_rate"])

    return (
        df.groupby(group_by)
        .agg(
            searches=("query", "size"),
            ctr=("had_click", "mean"),
            search_to_cart=("had_cart", "mean"),
            zero_result_rate=("is_zero_result", "mean"),
        )
        .reset_index()
        .sort_values("searches", ascending=False)
    )


def top_queries(df: pd.DataFrame, limit: int = 12) -> pd.DataFrame:
    """Identify highest-volume low-performing queries."""
    if df.empty:
        return pd.DataFrame(columns=["query", "category", "searches", "ctr", "search_to_cart", "zero_result_rate"])

    grouped = (
        df.groupby(["query", "category"])
        .agg(
            searches=("query", "size"),
            ctr=("had_click", "mean"),
            search_to_cart=("had_cart", "mean"),
            zero_result_rate=("is_zero_result", "mean"),
        )
        .reset_index()
    )

    ranked = grouped.sort_values(
        by=["zero_result_rate", "ctr", "search_to_cart", "searches"],
        ascending=[False, True, True, False],
    )
    return ranked.head(limit)


def root_cause_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Map poor-performing queries to PM-style problem hypotheses."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "query",
                "category",
                "device_type",
                "searches",
                "issue_type",
                "hypothesis",
                "recommendation",
            ]
        )

    grouped = (
        df.groupby(["query", "category", "device_type"])
        .agg(
            searches=("query", "size"),
            ctr=("had_click", "mean"),
            search_to_cart=("had_cart", "mean"),
            zero_result_rate=("is_zero_result", "mean"),
        )
        .reset_index()
    )

    rows = []
    for _, row in grouped.iterrows():
        issue_type = None
        hypothesis = None
        recommendation = None
        query = str(row["query"])

        if row["zero_result_rate"] >= 0.5:
            issue_type = "Zero results"
            hypothesis = "Catalog indexing or synonym coverage is missing for this search intent."
            recommendation = "Expand synonym rules, spelling tolerance, or inventory coverage."
        elif any(token in query for token in ["iphon", "samsng", "hedfone", "hoddie", "watc", "mause", "stnd", "nikonn", "cofee"]):
            issue_type = "Misspelling friction"
            hypothesis = "Users are expressing intent with typo variants that search cannot recover."
            recommendation = "Add typo tolerance and query rewrite mappings."
        elif "restock" in query or "out of stock" in query:
            issue_type = "Inventory mismatch"
            hypothesis = "User demand exists, but availability is blocking downstream engagement."
            recommendation = "Surface back-in-stock alternatives and alert experiences."
        elif row["ctr"] < 0.35 and row["zero_result_rate"] < 0.2:
            issue_type = "Low engagement"
            hypothesis = "Results exist, but ranking or product relevance is not matching user intent."
            recommendation = "Re-rank exact matches, improve tagging, and review top SKUs."

        if issue_type:
            rows.append(
                {
                    "query": row["query"],
                    "category": row["category"],
                    "device_type": row["device_type"],
                    "searches": int(row["searches"]),
                    "issue_type": issue_type,
                    "hypothesis": hypothesis,
                    "recommendation": recommendation,
                }
            )

    return (
        pd.DataFrame(rows)
        .sort_values(["searches", "issue_type"], ascending=[False, True])
        .head(15)
    )


def issue_summary(rca_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate issue types into an executive summary."""
    if rca_df.empty:
        return pd.DataFrame(columns=["issue_type", "affected_queries"])

    return (
        rca_df.groupby("issue_type")
        .size()
        .reset_index(name="affected_queries")
        .sort_values("affected_queries", ascending=False)
    )


def feature_impact_tests(df: pd.DataFrame) -> list[TestResult]:
    """Compare pre/post launch performance using two-proportion z-tests."""
    if df.empty or set(df["feature_flag"].unique()) != {"pre_launch", "post_launch"}:
        return []

    pre = df[df["feature_flag"] == "pre_launch"]
    post = df[df["feature_flag"] == "post_launch"]

    tests = [
        run_two_proportion_test(
            metric_name="Click-through rate",
            baseline_label="Pre-launch",
            variant_label="Post-launch",
            baseline_successes=int(pre["had_click"].sum()),
            baseline_total=len(pre),
            variant_successes=int(post["had_click"].sum()),
            variant_total=len(post),
        ),
        run_two_proportion_test(
            metric_name="Search-to-cart ratio",
            baseline_label="Pre-launch",
            variant_label="Post-launch",
            baseline_successes=int(pre["had_cart"].sum()),
            baseline_total=len(pre),
            variant_successes=int(post["had_cart"].sum()),
            variant_total=len(post),
        ),
    ]
    return tests


def run_two_proportion_test(
    metric_name: str,
    baseline_label: str,
    variant_label: str,
    baseline_successes: int,
    baseline_total: int,
    variant_successes: int,
    variant_total: int,
) -> TestResult:
    """Two-sided z-test for rate comparisons without external stats deps."""
    if baseline_total == 0 or variant_total == 0:
        return TestResult(
            metric_name=metric_name,
            baseline_label=baseline_label,
            variant_label=variant_label,
            baseline_rate=0.0,
            variant_rate=0.0,
            lift_pct=0.0,
            p_value=1.0,
            significant=False,
            baseline_n=baseline_total,
            variant_n=variant_total,
        )

    p1 = baseline_successes / baseline_total
    p2 = variant_successes / variant_total
    pooled = (baseline_successes + variant_successes) / (baseline_total + variant_total)
    variance = pooled * (1 - pooled) * ((1 / baseline_total) + (1 / variant_total))

    if variance <= 0:
        p_value = 1.0
    else:
        z_score = (p2 - p1) / sqrt(variance)
        p_value = 2 * (1 - normal_cdf(abs(z_score)))

    lift_pct = ((p2 - p1) / p1 * 100) if p1 > 0 else 0.0
    return TestResult(
        metric_name=metric_name,
        baseline_label=baseline_label,
        variant_label=variant_label,
        baseline_rate=p1,
        variant_rate=p2,
        lift_pct=lift_pct,
        p_value=p_value,
        significant=p_value < 0.05,
        baseline_n=baseline_total,
        variant_n=variant_total,
    )


def normal_cdf(value: float) -> float:
    """Standard normal CDF via the error function."""
    return 0.5 * (1 + erf(value / sqrt(2)))


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


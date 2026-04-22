"""Dash application entrypoint for Search Intelligence Analyzer."""

from __future__ import annotations

import base64
import io
from dataclasses import asdict

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, State, dash_table, dcc, html, no_update

from analytics import (
    cohort_breakdown,
    compute_kpis,
    feature_impact_tests,
    filter_data,
    format_percent,
    issue_summary,
    load_search_data,
    metric_timeseries,
    root_cause_analysis,
    top_queries,
)

from gemini_insights import generate_weekly_summary


COLOR_SEQUENCE = ["#d4af37", "#86b3d1", "#77c18d", "#d06772", "#c6a664"]
BASE_DF = load_search_data()
MIN_DATE = BASE_DF["timestamp"].min().date().isoformat()
MAX_DATE = BASE_DF["timestamp"].max().date().isoformat()


app = Dash(__name__)
server = app.server
app.title = "Search Intelligence Analyzer"


def make_kpi_card(title: str, kpi_id: str, helper_id: str) -> html.Div:
    return html.Div(
        className="kpi-card",
        children=[
            html.P(title, className="kpi-label"),
            html.H2("--", id=kpi_id, className="kpi-value"),
            html.P("", id=helper_id, className="kpi-helper"),
        ],
    )


def parse_uploaded_csv(contents: str | None, filename: str | None) -> pd.DataFrame:
    """Parse a user-uploaded CSV file into the richer analytics schema."""
    if not contents:
        return BASE_DF.copy()

    _, content_string = contents.split(",", 1)
    decoded = base64.b64decode(content_string)
    uploaded = pd.read_csv(io.StringIO(decoded.decode("utf-8")))

    required = {
        "session_id",
        "timestamp",
        "query",
        "query_group",
        "category",
        "brand",
        "device_type",
        "results_count",
        "clicks",
        "adds_to_cart",
        "feature_flag",
    }
    missing = required.difference(uploaded.columns)
    if missing:
        raise ValueError(
            f"{filename or 'Uploaded CSV'} is missing required columns: {', '.join(sorted(missing))}"
        )

    temp_buffer = io.StringIO()
    uploaded.to_csv(temp_buffer, index=False)
    temp_buffer.seek(0)
    return load_search_data(temp_buffer)


def build_timeseries_figure(trend_df: pd.DataFrame):
    if trend_df.empty:
        return px.line(title="No data available for current filters")

    melted = trend_df.melt(
        id_vars=["date"],
        value_vars=["ctr", "search_to_cart", "zero_result_rate"],
        var_name="metric",
        value_name="value",
    )
    label_map = {
        "ctr": "CTR",
        "search_to_cart": "Search-to-Cart",
        "zero_result_rate": "Zero Result Rate",
    }
    melted["metric"] = melted["metric"].map(label_map)
    fig = px.line(
        melted,
        x="date",
        y="value",
        color="metric",
        markers=True,
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="Metric",
        margin=dict(l=20, r=20, t=30, b=20),
        hovermode="x unified",
        yaxis_tickformat=".0%",
    )
    return fig


def build_bar_figure(df: pd.DataFrame, x: str, y: str, title: str, color: str):
    if df.empty:
        return px.bar(title="No data available for current filters")

    fig = px.bar(df, x=x, y=y, title=title, color_discrete_sequence=[color])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=50, b=20),
        yaxis_tickformat=".0%" if "rate" in y or y in {"ctr", "search_to_cart"} else None,
    )
    return fig


def serialize_impact_tests(tests):
    """Convert dataclass test results into JSON-serializable dicts."""
    serialized = []
    for test in tests:
        payload = asdict(test)
        payload["baseline_rate"] = float(payload["baseline_rate"])
        payload["variant_rate"] = float(payload["variant_rate"])
        payload["lift_pct"] = float(payload["lift_pct"])
        payload["p_value"] = float(payload["p_value"])
        serialized.append(payload)
    return serialized


app.layout = html.Div(
    className="page-shell",
    children=[
        dcc.Store(id="data-store"),
        dcc.Store(id="dashboard-context-store"),
        html.Header(
            className="topbar",
            children=[
                html.Div(
                    [
                        html.H1("Search Intelligence Analyzer"),
                        html.P(
                            "Interactive Python/Dash dashboard for diagnosing e-commerce search friction.",
                            className="subtitle",
                        ),
                    ]
                ),
                html.Div("Python / Dash Portfolio Project", className="badge"),
            ],
        ),
        html.Main(
            className="container",
            children=[
                html.Section(
                    className="panel hero-panel",
                    children=[
                        html.Div(
                            className="hero-copy",
                            children=[
                                html.H2("Search health dashboard"),
                                html.P(
                                    "Analyze simulated search logs across device, category, and launch cohorts to uncover why users search but fail to click or add to cart.",
                                    className="muted",
                                ),
                            ],
                        ),
                        html.Div(
                            className="hero-actions",
                            children=[
                                dcc.Upload(
                                    id="csv-upload",
                                    className="upload-box",
                                    children=html.Div(
                                        [
                                            html.Strong("Upload enriched CSV"),
                                            html.Span(" or use the bundled sample dataset"),
                                        ]
                                    ),
                                ),
                                html.Div(
                                    id="upload-status",
                                    className="status",
                                    children="Using bundled sample dataset.",
                                ),
                            ],
                        ),
                    ],
                ),
                html.Section(
                    className="panel filter-panel",
                    children=[
                        html.Div(
                            className="filter-grid",
                            children=[
                                html.Div(
                                    className="filter-card",
                                    children=[
                                        html.Label("Date range"),
                                        dcc.DatePickerRange(
                                            id="date-range",
                                            min_date_allowed=MIN_DATE,
                                            max_date_allowed=MAX_DATE,
                                            start_date=MIN_DATE,
                                            end_date=MAX_DATE,
                                            display_format="YYYY-MM-DD",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="filter-card",
                                    children=[
                                        html.Label("Category"),
                                        dcc.Dropdown(
                                            id="category-filter",
                                            options=[
                                                {"label": value, "value": value}
                                                for value in sorted(BASE_DF["category"].unique())
                                            ],
                                            multi=True,
                                            placeholder="All categories",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="filter-card",
                                    children=[
                                        html.Label("Device type"),
                                        dcc.Dropdown(
                                            id="device-filter",
                                            options=[
                                                {"label": value.title(), "value": value}
                                                for value in sorted(BASE_DF["device_type"].unique())
                                            ],
                                            multi=True,
                                            placeholder="All devices",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="filter-card",
                                    children=[
                                        html.Label("Launch cohort"),
                                        dcc.Dropdown(
                                            id="feature-filter",
                                            options=[
                                                {"label": "Pre-launch", "value": "pre_launch"},
                                                {"label": "Post-launch", "value": "post_launch"},
                                            ],
                                            multi=True,
                                            placeholder="Pre and post-launch",
                                        ),
                                    ],
                                ),
                            ],
                        )
                    ],
                ),
                html.Section(
                    className="kpi-grid",
                    children=[
                        make_kpi_card("CTR", "ctr-kpi", "ctr-helper"),
                        make_kpi_card("Search-to-Cart Ratio", "cart-kpi", "cart-helper"),
                        make_kpi_card("Zero Result Rate", "zero-kpi", "zero-helper"),
                        make_kpi_card("Reformulation Rate", "reform-kpi", "reform-helper"),
                    ],
                ),
                html.Section(
                    className="chart-grid",
                    children=[
                        html.Article(
                            className="panel chart-panel span-2",
                            children=[
                                html.Div(
                                    className="section-head",
                                    children=[
                                        html.H2("Metric trend over time"),
                                        html.P(
                                            "Tracks search quality across the selected cohort.",
                                            className="muted",
                                        ),
                                    ],
                                ),
                                dcc.Graph(id="trend-chart", config={"displayModeBar": False}),
                            ],
                        ),
                        html.Article(
                            className="panel chart-panel",
                            children=[
                                html.Div(
                                    className="section-head",
                                    children=[
                                        html.H2("CTR by device"),
                                        html.P("Segmented cohort performance by device.", className="muted"),
                                    ],
                                ),
                                dcc.Graph(id="device-chart", config={"displayModeBar": False}),
                            ],
                        ),
                        html.Article(
                            className="panel chart-panel",
                            children=[
                                html.Div(
                                    className="section-head",
                                    children=[
                                        html.H2("Search-to-cart by category"),
                                        html.P("Highlights high-intent product spaces.", className="muted"),
                                    ],
                                ),
                                dcc.Graph(id="category-chart", config={"displayModeBar": False}),
                            ],
                        ),
                    ],
                ),
                html.Section(
                    className="grid-2",
                    children=[
                        html.Article(
                            className="panel",
                            children=[
                                html.Div(
                                    className="section-head",
                                    children=[
                                        html.H2("Low-performing queries"),
                                        html.P(
                                            "Highest-volume queries ranked by zero-result and engagement problems.",
                                            className="muted",
                                        ),
                                    ],
                                ),
                                dash_table.DataTable(
                                    id="top-query-table",
                                    columns=[],
                                    data=[],
                                    style_table={"overflowX": "auto"},
                                    style_cell={"textAlign": "left"},
                                ),
                            ],
                        ),
                        html.Article(
                            className="panel",
                            children=[
                                html.Div(
                                    className="section-head",
                                    children=[
                                        html.H2("Root-cause issue summary"),
                                        html.P(
                                            "Counts of diagnostic issue types detected in the selected cohort.",
                                            className="muted",
                                        ),
                                    ],
                                ),
                                dcc.Graph(id="issue-chart", config={"displayModeBar": False}),
                                html.Div(id="impact-summary", className="impact-summary"),
                            ],
                        ),
                    ],
                ),
                html.Section(
                    className="panel",
                    children=[
                        html.Div(
                            className="section-head",
                            children=[
                                html.H2("Root-cause analysis module"),
                                html.P(
                                    "Maps poor-performing queries to product hypotheses and next-step recommendations.",
                                    className="muted",
                                ),
                            ],
                        ),
                        dash_table.DataTable(
                            id="rca-table",
                            columns=[],
                            data=[],
                            page_size=10,
                            style_table={"overflowX": "auto"},
                            style_cell={"textAlign": "left", "whiteSpace": "normal", "height": "auto"},
                        ),
                    ],
                ),
                html.Section(
                    className="panel",
                    children=[
                        html.Div(
                            className="section-head",
                            children=[
                                html.H2("Gemini weekly insight layer"),
                                html.P(
                                    "Optional Google Gemini summarization over the currently filtered slice. "
                                    "Configure `GEMINI_API_KEY` in your environment (never commit keys to GitHub).",
                                    className="muted",
                                ),
                            ],
                        ),
                        html.Div(
                            className="gemini-actions",
                            children=[
                                html.Button("Generate AI summary", id="gemini-generate", className="secondary"),
                                html.Span("", id="gemini-status", className="gemini-status"),
                            ],
                        ),
                        dcc.Markdown(
                            id="gemini-summary",
                            className="gemini-markdown",
                            children="_Click **Generate AI summary** to draft a PM-style weekly narrative._",
                        ),
                    ],
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("data-store", "data"),
    Output("upload-status", "children"),
    Input("csv-upload", "contents"),
    State("csv-upload", "filename"),
    prevent_initial_call=False,
)
def update_data_store(contents, filename):
    try:
        df = parse_uploaded_csv(contents, filename)
        message = (
            f"Loaded {filename} with {len(df)} rows."
            if contents
            else f"Using bundled sample dataset with {len(df)} rows."
        )
        return df.to_json(date_format="iso", orient="split"), message
    except Exception as error:  # pragma: no cover - UI fallback
        return BASE_DF.to_json(date_format="iso", orient="split"), f"Upload failed: {error}"


@app.callback(
    Output("ctr-kpi", "children"),
    Output("ctr-helper", "children"),
    Output("cart-kpi", "children"),
    Output("cart-helper", "children"),
    Output("zero-kpi", "children"),
    Output("zero-helper", "children"),
    Output("reform-kpi", "children"),
    Output("reform-helper", "children"),
    Output("trend-chart", "figure"),
    Output("device-chart", "figure"),
    Output("category-chart", "figure"),
    Output("issue-chart", "figure"),
    Output("top-query-table", "columns"),
    Output("top-query-table", "data"),
    Output("rca-table", "columns"),
    Output("rca-table", "data"),
    Output("impact-summary", "children"),
    Output("dashboard-context-store", "data"),
    Input("data-store", "data"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("category-filter", "value"),
    Input("device-filter", "value"),
    Input("feature-filter", "value"),
)
def refresh_dashboard(data_json, start_date, end_date, categories, devices, feature_flags):
    df = pd.read_json(io.StringIO(data_json), orient="split")
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    filtered = filter_data(
        df,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        devices=devices,
        feature_flags=feature_flags,
    )

    kpis = compute_kpis(filtered)
    trend_df = metric_timeseries(filtered)
    device_df = cohort_breakdown(filtered, "device_type")
    category_df = cohort_breakdown(filtered, "category")
    top_df = top_queries(filtered)
    rca_df = root_cause_analysis(filtered)
    issue_df = issue_summary(rca_df)
    impact_tests = feature_impact_tests(filtered)

    device_fig = build_bar_figure(device_df, "device_type", "ctr", "CTR by device", "#86b3d1")
    category_fig = build_bar_figure(
        category_df,
        "category",
        "search_to_cart",
        "Search-to-cart ratio by category",
        "#77c18d",
    )
    issue_fig = build_bar_figure(issue_df, "issue_type", "affected_queries", "Issue count", "#d06772")

    top_display = top_df.copy()
    for column in ["ctr", "search_to_cart", "zero_result_rate"]:
        if column in top_display:
            top_display[column] = top_display[column].map(format_percent)

    rca_display = rca_df.copy()

    impact_cards = []
    if impact_tests:
        for test in impact_tests:
            status = "Statistically significant" if test.significant else "Not statistically significant"
            impact_cards.append(
                html.Div(
                    className="impact-card",
                    children=[
                        html.H4(test.metric_name),
                        html.P(
                            f"{test.baseline_label}: {format_percent(test.baseline_rate)} -> "
                            f"{test.variant_label}: {format_percent(test.variant_rate)}"
                        ),
                        html.P(f"Lift: {test.lift_pct:.1f}%"),
                        html.P(f"p-value: {test.p_value:.4f}"),
                        html.Span(status, className="impact-badge"),
                    ],
                )
            )
    else:
        impact_cards.append(
            html.Div(
                className="impact-card",
                children=[
                    html.H4("Feature impact"),
                    html.P("Select both pre-launch and post-launch data to view significance testing."),
                ],
            )
        )

    top_columns = [{"name": name.replace("_", " ").title(), "id": name} for name in top_display.columns]
    rca_columns = [{"name": name.replace("_", " ").title(), "id": name} for name in rca_display.columns]

    dashboard_context = {
        "kpis": {key: float(value) for key, value in kpis.items()},
        "issue_summary": issue_df.to_dict("records"),
        "impact_tests": serialize_impact_tests(impact_tests),
    }

    return (
        format_percent(kpis["ctr"]),
        f"{kpis['searches']} searches in scope",
        format_percent(kpis["search_to_cart"]),
        "Share of searches that led to at least one add-to-cart",
        format_percent(kpis["zero_result_rate"]),
        "Share of searches with no matching results",
        format_percent(kpis["reformulation_rate"]),
        "Proxy rate for repeated query-group searches per day",
        build_timeseries_figure(trend_df),
        device_fig,
        category_fig,
        issue_fig,
        top_columns,
        top_display.to_dict("records"),
        rca_columns,
        rca_display.to_dict("records"),
        impact_cards,
        dashboard_context,
    )


@app.callback(
    Output("gemini-summary", "children"),
    Output("gemini-status", "children"),
    Input("gemini-generate", "n_clicks"),
    State("dashboard-context-store", "data"),
    prevent_initial_call=True,
)
def generate_gemini_summary(n_clicks, context):
    if not n_clicks or not context:
        return no_update, no_update

    from analytics import TestResult

    kpis = context.get("kpis", {})
    issue_rows = context.get("issue_summary", [])
    tests_payload = context.get("impact_tests", [])

    tests = [
        TestResult(
            metric_name=item["metric_name"],
            baseline_label=item["baseline_label"],
            variant_label=item["variant_label"],
            baseline_rate=item["baseline_rate"],
            variant_rate=item["variant_rate"],
            lift_pct=item["lift_pct"],
            p_value=item["p_value"],
            significant=item["significant"],
            baseline_n=item["baseline_n"],
            variant_n=item["variant_n"],
        )
        for item in tests_payload
    ]

    summary, status = generate_weekly_summary(kpis=kpis, issue_rows=issue_rows, impact_tests=tests)
    return summary, status


if __name__ == "__main__":
    app.run(debug=True)

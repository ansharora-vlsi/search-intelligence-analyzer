"""Optional Gemini-powered narrative summaries for the dashboard.

This module is intentionally isolated so the rest of the analytics code stays
deterministic and easy to test without network access.

Security note:
- Never commit API keys. Configure `GEMINI_API_KEY` in your environment
  (local shell, Render dashboard, etc.).
"""

from __future__ import annotations

import json
import os
from typing import Any

from analytics import TestResult, format_percent


def _build_prompt_payload(
    kpis: dict[str, float],
    issue_rows: list[dict[str, Any]],
    impact_tests: list[TestResult],
) -> str:
    """Serialize the current dashboard slice into a compact JSON prompt."""
    tests_payload = [
        {
            "metric": t.metric_name,
            "baseline": format_percent(t.baseline_rate),
            "variant": format_percent(t.variant_rate),
            "lift_pct": round(t.lift_pct, 2),
            "p_value": round(t.p_value, 6),
            "significant": t.significant,
        }
        for t in impact_tests
    ]
    payload = {
        "role": "You are a senior PM + analytics lead at an e-commerce company.",
        "task": (
            "Write a concise weekly executive summary (6-10 bullet points) explaining "
            "search health, the biggest problems, likely root causes, and prioritized "
            "next actions. Tie recommendations to the metrics provided."
        ),
        "kpis": {k: (format_percent(v) if "rate" in k or k in {"ctr", "search_to_cart", "reformulation_rate"} else v) for k, v in kpis.items()},
        "top_issue_types": issue_rows[:8],
        "feature_impact_tests": tests_payload,
        "constraints": [
            "Be explicit that the dataset is simulated.",
            "Do not invent numbers not present in the payload.",
            "Use clear PM language, not marketing fluff.",
        ],
    }
    return json.dumps(payload, indent=2)


def generate_weekly_summary(
    kpis: dict[str, float],
    issue_rows: list[dict[str, Any]],
    impact_tests: list[TestResult],
) -> tuple[str, str]:
    """Return (summary_text, status_message).

    If `GEMINI_API_KEY` is missing, returns a deterministic template instead of
    calling the API.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

    prompt = _build_prompt_payload(kpis, issue_rows, impact_tests)

    if not api_key:
        fallback = (
            "### Weekly summary (offline mode)\n\n"
            "- Gemini API key is not configured.\n"
            "- Set the environment variable `GEMINI_API_KEY` locally or in your host "
            "(Render/Railway) to enable AI-generated narratives.\n"
            "- Until then, use the KPI cards, charts, and root-cause tables below as "
            "your primary evidence.\n\n"
            f"**Snapshot (from current filters)**\n\n```json\n{prompt}\n```"
        )
        return fallback, "Gemini disabled: set GEMINI_API_KEY to enable AI summaries."

    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            [
                "You output Markdown only.",
                "Keep it tight: 6-10 bullets, each one actionable.",
                prompt,
            ]
        )
        text = (response.text or "").strip()
        if not text:
            return (
                "_Gemini returned an empty response. Try again or check model access._",
                "Gemini error: empty response.",
            )
        return text, f"Gemini summary generated with model `{model_name}`."
    except Exception as error:  # pragma: no cover - network/runtime dependent
        return (
            f"_Gemini call failed._\n\n```\n{error}\n```\n\n"
            "Tip: verify your API key, billing/quota, and model name (`GEMINI_MODEL`).",
            "Gemini error: see summary panel for details.",
        )

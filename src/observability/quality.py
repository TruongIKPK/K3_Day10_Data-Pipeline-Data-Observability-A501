from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """TODO(student): tao bo data quality checks.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    checks: list[dict[str, Any]] = []

    def add_check(name: str, dimension: str, expectation: str, observed: Any, success: bool, affected_rows: int = 0) -> None:
        checks.append(
            {
                "name": name,
                "dimension": dimension,
                "expectation": expectation,
                "observed": observed,
                "success": bool(success),
                "affected_rows": int(affected_rows),
            }
        )

    total_rows = int(len(df))
    add_check(
        "row_count",
        "completeness",
        "at least four rows",
        total_rows,
        total_rows >= 4,
        0 if total_rows >= 4 else total_rows,
    )

    paper_ids = df["paper_id"] if "paper_id" in df.columns else pd.Series(dtype="object")
    missing_ids = int(paper_ids.isna().sum() + paper_ids.astype(str).str.strip().eq("").sum())
    duplicate_ids = int(paper_ids.astype(str).duplicated(keep=False).sum())
    add_check("paper_id_not_null", "completeness", "paper_id is present", missing_ids, missing_ids == 0, missing_ids)
    add_check("paper_id_unique", "uniqueness", "paper_id values are unique", duplicate_ids, duplicate_ids == 0, duplicate_ids)

    title_values = df["title"] if "title" in df.columns else pd.Series(dtype="object")
    missing_titles = int(title_values.isna().sum() + title_values.astype(str).str.strip().eq("").sum())
    short_titles = int(title_values.astype(str).str.strip().str.len().lt(8).sum())
    add_check("title_present", "completeness", "title is not blank", missing_titles, missing_titles == 0, missing_titles)
    add_check("title_not_truncated", "validity", "title has at least eight characters", short_titles, short_titles == 0, short_titles)

    summary_values = df["summary"] if "summary" in df.columns else pd.Series(dtype="object")
    missing_summaries = int(summary_values.isna().sum() + summary_values.astype(str).str.strip().eq("").sum())
    add_check("summary_present", "completeness", "summary is not blank", missing_summaries, missing_summaries == 0, missing_summaries)

    embedding_values = df["text_for_embedding"] if "text_for_embedding" in df.columns else pd.Series(dtype="object")
    missing_embeddings = int(embedding_values.isna().sum() + embedding_values.astype(str).str.strip().eq("").sum())
    add_check("embedding_text_present", "completeness", "text_for_embedding is not blank", missing_embeddings, missing_embeddings == 0, missing_embeddings)

    if "published" in df.columns:
        parsed_dates = pd.to_datetime(df["published"], errors="coerce")
        invalid_dates = int(parsed_dates.isna().sum())
    else:
        invalid_dates = total_rows
    add_check("published_parseable", "validity", "published is parseable", invalid_dates, invalid_dates == 0, invalid_dates)

    if "age_days" in df.columns:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        stale_mask = ages.isna() | (ages < 0) | (ages > settings.freshness_threshold_days)
        stale_rows = int(stale_mask.sum())
    else:
        stale_rows = total_rows
    add_check(
        "freshness_threshold",
        "freshness",
        f"age_days is between 0 and {settings.freshness_threshold_days}",
        stale_rows,
        stale_rows == 0,
        stale_rows,
    )

    passed = sum(1 for check in checks if check["success"])
    payload = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "total_rows": total_rows,
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": len(checks) - passed,
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"quality_{report_name}.json", payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """TODO(student): tong hop freshness report.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    total_rows = int(len(df))
    if "published" in df.columns:
        parsed_dates = pd.to_datetime(df["published"], errors="coerce")
        valid_dates = parsed_dates.dropna()
        latest_published = valid_dates.max().date().isoformat() if not valid_dates.empty else None
        oldest_published = valid_dates.min().date().isoformat() if not valid_dates.empty else None
    else:
        latest_published = None
        oldest_published = None
    if "age_days" in df.columns:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int((ages.isna() | (ages < 0) | (ages > settings.freshness_threshold_days)).sum())
    else:
        stale_rows = total_rows
    payload = {
        "generated_at": now_utc().isoformat(),
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_rows / total_rows if total_rows else 1.0,
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": bool(total_rows > 0 and stale_rows == 0),
    }
    write_json(report_path, payload)
    return payload

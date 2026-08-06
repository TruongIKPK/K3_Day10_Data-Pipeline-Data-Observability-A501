from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report cho baseline phase.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    metric_rows = "\n".join(
        f"| `{key}` | {value} |"
        for key, value in (
            ("retrieval_hit_rate", metrics.get("retrieval_hit_rate", "N/A")),
            ("mean_token_f1", metrics.get("mean_token_f1", "N/A")),
            ("judge_accuracy", metrics.get("judge_accuracy", "N/A")),
            ("mean_judge_score", metrics.get("mean_judge_score", "N/A")),
        )
    )
    checks = quality.get("checks", [])
    quality_rows = "\n".join(
        f"| {check.get('name')} | {check.get('dimension')} | {check.get('observed')} | {'PASS' if check.get('success') else 'FAIL'} |"
        for check in checks
    )
    ragas = metrics.get("ragas", {})
    ragas_status = "skipped" if isinstance(ragas, dict) and "skipped" in ragas else ragas
    text = f"""# Baseline Pipeline Report

## Run summary

| Field | Value |
| --- | --- |
| Source | {source_summary.get('source', 'Crossref REST API')} |
| Query | {source_summary.get('query', '')} |
| Filter | {source_summary.get('filter', '')} |
| Records fetched | {source_summary.get('records_fetched', 'N/A')} |
| Clean rows | {source_summary.get('clean_rows', 'N/A')} |
| Run date | {source_summary.get('run_date', 'N/A')} |

## Evaluation metrics

| Metric | Value |
| --- | ---: |
{metric_rows}
| `ragas` | {ragas_status} |

## Data quality

| Check | Dimension | Observed | Status |
| --- | --- | ---: | --- |
{quality_rows}

Overall quality status: **{quality.get('status', 'UNKNOWN')}**.

## Freshness

| Field | Value |
| Latest published | {freshness.get('latest_published', 'N/A')} |
| Oldest published | {freshness.get('oldest_published', 'N/A')} |
| Stale rows | {freshness.get('stale_rows', 'N/A')} |
| Threshold days | {freshness.get('threshold_days', 'N/A')} |
| Freshness status | {'FRESH' if freshness.get('is_fresh') else 'STALE/UNKNOWN'} |

## Interpretation

This report is generated from the baseline artifacts. Claims about retrieval or answer quality must be supported by the metrics and answer JSON produced in the same run.
"""
    write_text(report_path, text)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")

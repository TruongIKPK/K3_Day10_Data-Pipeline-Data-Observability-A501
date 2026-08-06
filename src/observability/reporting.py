from __future__ import annotations

import math
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate a Markdown report for the baseline phase.

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
    """Generate a Markdown comparison of baseline, corrupted, and repaired states."""

    metric_specs = (
        ("retrieval_hit_rate", "Retrieval hit rate"),
        ("mean_token_f1", "Mean token F1"),
        ("judge_accuracy", "Judge accuracy"),
        ("mean_judge_score", "Mean judge score"),
    )

    def as_number(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def format_number(value: float | None, *, signed: bool = False) -> str:
        if value is None:
            return "N/A"
        prefix = "+" if signed and value > 0 else ""
        return f"{prefix}{value:.4f}".rstrip("0").rstrip(".")

    def metric_value(payload: dict[str, Any], key: str) -> float | None:
        return as_number(payload.get(key))

    def recovery_status(baseline: float | None, corrupted: float | None, repaired: float | None) -> str:
        if baseline is None or corrupted is None or repaired is None:
            return "Unknown"
        tolerance = 1e-9
        if corrupted >= baseline - tolerance:
            return "No observed degradation" if repaired >= baseline - tolerance else "Below baseline after repair"
        if repaired >= baseline - tolerance:
            return "Recovered to baseline"
        if repaired > corrupted + tolerance:
            return "Partially recovered"
        return "Not recovered"

    metric_rows: list[str] = []
    degraded_metrics: list[str] = []
    recovered_metrics: list[str] = []
    for key, label in metric_specs:
        baseline = metric_value(baseline_metrics, key)
        corrupted = metric_value(corrupted_metrics, key)
        repaired = metric_value(repaired_metrics, key)
        corruption_delta = corrupted - baseline if corrupted is not None and baseline is not None else None
        repair_delta = repaired - corrupted if repaired is not None and corrupted is not None else None
        baseline_gap = repaired - baseline if repaired is not None and baseline is not None else None
        status = recovery_status(baseline, corrupted, repaired)
        if corruption_delta is not None and corruption_delta < -1e-9:
            degraded_metrics.append(label)
            if baseline_gap is not None and baseline_gap >= -1e-9:
                recovered_metrics.append(label)
        metric_rows.append(
            "| "
            + " | ".join(
                (
                    f"`{key}`",
                    format_number(baseline),
                    format_number(corrupted),
                    format_number(corruption_delta, signed=True),
                    format_number(repaired),
                    format_number(repair_delta, signed=True),
                    format_number(baseline_gap, signed=True),
                    status,
                )
            )
            + " |"
        )

    def ragas_status(payload: dict[str, Any]) -> str:
        ragas = payload.get("ragas")
        if isinstance(ragas, dict) and "skipped" in ragas:
            return "Skipped"
        if ragas in (None, {}):
            return "N/A"
        return "Available"

    def quality_summary(payload: dict[str, Any]) -> tuple[str, str, str, str]:
        checks = payload.get("checks", [])
        if not isinstance(checks, list):
            checks = []
        failed_checks = [str(check.get("name", "unnamed")) for check in checks if not check.get("success")]
        passed = payload.get("checks_passed", sum(1 for check in checks if check.get("success")))
        total = payload.get("checks_total", len(checks))
        return (
            str(payload.get("total_rows", "N/A")),
            f"{passed}/{total}",
            str(payload.get("status", "UNKNOWN")),
            ", ".join(failed_checks) if failed_checks else "None",
        )

    corrupted_rows, corrupted_checks, corrupted_status, corrupted_failures = quality_summary(corrupted_quality)
    repaired_rows, repaired_checks, repaired_status, repaired_failures = quality_summary(repaired_quality)

    def freshness_status(payload: dict[str, Any]) -> str:
        return "FRESH" if payload.get("is_fresh") else "STALE/UNKNOWN"

    def format_ratio(value: Any) -> str:
        return format_number(as_number(value))

    if degraded_metrics:
        metric_impact = f"Corruption degraded {len(degraded_metrics)} metric(s): {', '.join(degraded_metrics)}."
        metric_recovery = f"Repair restored {len(recovered_metrics)}/{len(degraded_metrics)} degraded metric(s) to baseline."
    else:
        metric_impact = "No supported evaluation metric decreased after corruption."
        metric_recovery = "There was no measured metric regression to recover."

    text = f"""# Corruption and Repair Comparison Report

## Run summary

| State | Evaluation samples | Quality status | Freshness status |
| --- | ---: | --- | --- |
| Baseline | {baseline_metrics.get('samples', 'N/A')} | See Phase 1 quality artifact | See Phase 1 freshness artifact |
| Corrupted | {corrupted_metrics.get('samples', 'N/A')} | {corrupted_status} | {freshness_status(corrupted_freshness)} |
| Repaired | {repaired_metrics.get('samples', 'N/A')} | {repaired_status} | {freshness_status(repaired_freshness)} |

## Evaluation metrics

| Metric | Baseline | Corrupted | Corruption delta | Repaired | Repair delta | Gap to baseline | Recovery status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(metric_rows)}

All evaluation metrics are higher-is-better. Corruption delta is `corrupted - baseline`, repair delta is `repaired - corrupted`, and gap to baseline is `repaired - baseline`.

### Ragas availability

| Baseline | Corrupted | Repaired |
| --- | --- | --- |
| {ragas_status(baseline_metrics)} | {ragas_status(corrupted_metrics)} | {ragas_status(repaired_metrics)} |

## Data quality comparison

| State | Rows | Checks passed | Overall status | Failed checks |
| --- | ---: | ---: | --- | --- |
| Corrupted | {corrupted_rows} | {corrupted_checks} | {corrupted_status} | {corrupted_failures} |
| Repaired | {repaired_rows} | {repaired_checks} | {repaired_status} | {repaired_failures} |

Baseline quality details remain in the Phase 1 quality artifact; this comparison function receives corrupted and repaired quality payloads.

## Freshness comparison

| State | Latest published | Oldest published | Stale rows | Stale ratio | Threshold days | Status |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Corrupted | {corrupted_freshness.get('latest_published', 'N/A')} | {corrupted_freshness.get('oldest_published', 'N/A')} | {corrupted_freshness.get('stale_rows', 'N/A')} | {format_ratio(corrupted_freshness.get('stale_ratio'))} | {corrupted_freshness.get('threshold_days', 'N/A')} | {freshness_status(corrupted_freshness)} |
| Repaired | {repaired_freshness.get('latest_published', 'N/A')} | {repaired_freshness.get('oldest_published', 'N/A')} | {repaired_freshness.get('stale_rows', 'N/A')} | {format_ratio(repaired_freshness.get('stale_ratio'))} | {repaired_freshness.get('threshold_days', 'N/A')} | {freshness_status(repaired_freshness)} |

## Interpretation

- {metric_impact}
- {metric_recovery}
- Corrupted data quality status: **{corrupted_status}**; failed checks: {corrupted_failures}.
- Repaired data quality status: **{repaired_status}**; failed checks: {repaired_failures}.
- Freshness changed from **{freshness_status(corrupted_freshness)}** in the corrupted state to **{freshness_status(repaired_freshness)}** after repair.

## Reproducibility notes

- Baseline, corrupted, and repaired metrics must be produced from the same evaluation set.
- Claims in this report are derived from the metrics, quality, and freshness payloads passed by the corruption flow.
- A skipped Ragas pass or fallback judge should be treated as an evaluation limitation, not as evidence of production LLM quality.
"""
    write_text(report_path, text)

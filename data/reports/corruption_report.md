# Corruption and Repair Comparison Report

## Run summary

| State | Evaluation samples | Quality status | Freshness status |
| --- | ---: | --- | --- |
| Baseline | 16 | See Phase 1 quality artifact | See Phase 1 freshness artifact |
| Corrupted | 16 | FAIL | STALE/UNKNOWN |
| Repaired | 16 | PASS | FRESH |

## Evaluation metrics

| Metric | Baseline | Corrupted | Corruption delta | Repaired | Repair delta | Gap to baseline | Recovery status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1 | 0.5 | -0.5 | 1 | +0.5 | 0 | Recovered to baseline |
| `mean_token_f1` | 0.75 | 0.3902 | -0.3598 | 0.75 | +0.3598 | 0 | Recovered to baseline |
| `judge_accuracy` | 0.75 | 0.375 | -0.375 | 0.75 | +0.375 | 0 | Recovered to baseline |
| `mean_judge_score` | 4 | 2.5 | -1.5 | 4 | +1.5 | 0 | Recovered to baseline |

All evaluation metrics are higher-is-better. Corruption delta is `corrupted - baseline`, repair delta is `repaired - corrupted`, and gap to baseline is `repaired - baseline`.

### Ragas availability

| Baseline | Corrupted | Repaired |
| --- | --- | --- |
| Skipped | Skipped | Skipped |

## Data quality comparison

| State | Rows | Checks passed | Overall status | Failed checks |
| --- | ---: | ---: | --- | --- |
| Corrupted | 24 | 5/9 | FAIL | paper_id_unique, title_not_truncated, summary_present, freshness_threshold |
| Repaired | 24 | 9/9 | PASS | None |

Baseline quality details remain in the Phase 1 quality artifact; this comparison function receives corrupted and repaired quality payloads.

## Freshness comparison

| State | Latest published | Oldest published | Stale rows | Stale ratio | Threshold days | Status |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Corrupted | 2026-07-13 | 2016-08-08 | 2 | 0.0833 | 180 | STALE/UNKNOWN |
| Repaired | 2026-08-01 | 2026-02-12 | 0 | 0 | 180 | FRESH |

## Interpretation

- Corruption degraded 4 metric(s): Retrieval hit rate, Mean token F1, Judge accuracy, Mean judge score.
- Repair restored 4/4 degraded metric(s) to baseline.
- Corrupted data quality status: **FAIL**; failed checks: paper_id_unique, title_not_truncated, summary_present, freshness_threshold.
- Repaired data quality status: **PASS**; failed checks: None.
- Freshness changed from **STALE/UNKNOWN** in the corrupted state to **FRESH** after repair.

## Reproducibility notes

- Baseline, corrupted, and repaired metrics must be produced from the same evaluation set.
- Claims in this report are derived from the metrics, quality, and freshness payloads passed by the corruption flow.
- A skipped Ragas pass or fallback judge should be treated as an evaluation limitation, not as evidence of production LLM quality.

# Baseline Pipeline Report

## Run summary

| Field | Value |
| --- | --- |
| Source | https://api.crossref.org/works |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-02-07,has-abstract:true |
| Records fetched | 24 |
| Clean rows | 24 |
| Run date | 2026-08-06T03:21:42.846499+00:00 |

## Evaluation metrics

| Metric | Value |
| --- | ---: |
| `retrieval_hit_rate` | 1.0 |
| `mean_token_f1` | 1.0 |
| `judge_accuracy` | 1.0 |
| `mean_judge_score` | 5 |
| `ragas` | skipped |

## Data quality

| Check | Dimension | Observed | Status |
| --- | --- | ---: | --- |
| row_count | completeness | 24 | PASS |
| paper_id_not_null | completeness | 0 | PASS |
| paper_id_unique | uniqueness | 0 | PASS |
| title_present | completeness | 0 | PASS |
| title_not_truncated | validity | 0 | PASS |
| summary_present | completeness | 0 | PASS |
| embedding_text_present | completeness | 0 | PASS |
| published_parseable | validity | 0 | PASS |
| freshness_threshold | freshness | 0 | PASS |

Overall quality status: **PASS**.

## Freshness

| Field | Value |
| Latest published | 2026-08-01 |
| Oldest published | 2026-02-12 |
| Stale rows | 0 |
| Threshold days | 180 |
| Freshness status | FRESH |

## Interpretation

This report is generated from the baseline artifacts. Claims about retrieval or answer quality must be supported by the metrics and answer JSON produced in the same run.

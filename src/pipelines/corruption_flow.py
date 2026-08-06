from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Build the corruption -> evaluate -> repair -> compare flow.

    Pseudo-code:
    1. Load baseline metrics va clean dataset.
    2. Tao corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index va evaluate.
    5. Run quality checks/freshness tren corrupted data.
    6. Repair lai tu raw records.
    7. Evaluate repaired dataset.
    8. Tao comparison report.
    """
    settings = load_settings()
    paths = settings.paths

    if not paths.baseline_metrics.exists() or not paths.clean_json.exists():
        raise RuntimeError("Baseline artifacts are missing; run script/run_phase1.py first.")
    baseline_metrics = read_json(paths.baseline_metrics)
    clean_df = pd.DataFrame(read_json(paths.clean_json))

    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=paths.corrupted_embeddings_json,
    )
    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings=settings, report_name="corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings=settings,
        report_path=paths.quality_dir / "freshness_corrupted.json",
    )

    records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(records, run_date=now_utc())
    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=paths.repaired_embeddings_json,
    )
    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings=settings, report_name="repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings=settings,
        report_path=paths.quality_dir / "freshness_repaired.json",
    )

    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print(
        f"Corrupted: {len(corrupted_df)} rows, quality={corrupted_quality['status']}, "
        f"hit_rate={corrupted_evaluation.summary['retrieval_hit_rate']:.3f}"
    )
    print(
        f"Repaired: {len(repaired_df)} rows, quality={repaired_quality['status']}, "
        f"hit_rate={repaired_evaluation.summary['retrieval_hit_rate']:.3f}"
    )
    print(f"Comparison report: {paths.comparison_report}")


if __name__ == "__main__":
    main()

from __future__ import annotations

from core.config import load_settings, normalized_provider, require_llm_credentials
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

def main() -> None:
    """Run the baseline ingestion, indexing, evaluation and observability flow.

    Pseudo-code:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    settings = load_settings()
    paths = settings.paths
    run_date = now_utc()

    should_fetch = settings.refresh_source or not paths.raw_records_json.exists()
    if should_fetch:
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(paths.raw_records_json)
    if len(records) < 4:
        raise RuntimeError(f"Baseline requires at least four usable records; found {len(records)}.")

    clean_df = build_clean_dataframe(records, run_date=run_date)
    if len(clean_df) < 4:
        raise RuntimeError(f"Baseline cleaning produced fewer than four rows: {len(clean_df)}.")
    write_csv(clean_df, paths.clean_csv)
    write_json(paths.clean_json, clean_df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=paths.embeddings_json,
    )

    if settings.refresh_test_set or not paths.eval_testset.exists():
        test_set = build_test_set(clean_df, paths.eval_testset)
    else:
        test_set = read_json(paths.eval_testset)
    valid_ids = set(clean_df["paper_id"].astype(str))
    missing_ids = sorted(
        {
            doc_id
            for item in test_set
            for doc_id in item.get("ground_truth_doc_ids", [])
            if doc_id not in valid_ids
        }
    )
    if missing_ids:
        raise RuntimeError(f"Evaluation set references missing baseline documents: {missing_ids}")

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings=settings, report_name="baseline")
    freshness = build_freshness_report(clean_df, settings=settings, report_path=paths.freshness_report)

    source_summary = {
        "source": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "records_fetched": len(records),
        "clean_rows": len(clean_df),
        "run_date": run_date.isoformat(),
        "refreshed_source": should_fetch,
        "embedding_model": settings.embedding_model,
        "collection_name": settings.baseline_collection_name,
        "top_k": settings.top_k,
    }
    generate_phase1_report(
        report_path=paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    demo_payload: list[dict] = []
    try:
        require_llm_credentials(settings)
        agent = build_agent(settings=settings, index=index)
        demo_questions = [test_set[0]["question"], test_set[1]["question"]]
        for question in demo_questions:
            demo_payload.append({"question": question, "answer": run_agent_question(agent, question)})
    except Exception as exc:
        demo_payload = [{
            "status": "skipped",
            "provider": normalized_provider(settings),
            "reason": str(exc),
        }]
    write_json(paths.demo_answers, demo_payload)

    print(f"Baseline completed: {len(clean_df)} clean rows, {evaluation.summary['samples']} evaluation samples")
    print(f"Metrics: {paths.baseline_metrics}")
    print(f"Quality: {paths.quality_dir / 'quality_baseline.json'}")
    print(f"Report: {paths.baseline_report}")

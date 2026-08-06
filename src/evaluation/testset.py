from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """TODO(student): tao bo evaluation set tu cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    required = {"paper_id", "title", "summary", "authors_joined", "categories_joined", "published"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Cannot build test set; clean dataframe is missing: {sorted(missing)}")
    candidates = df[
        df["paper_id"].notna()
        & df["title"].astype(str).str.strip().ne("")
        & df["summary"].astype(str).str.strip().ne("")
        & df["authors_joined"].astype(str).str.strip().ne("")
        & df["categories_joined"].astype(str).str.strip().ne("")
        & df["published"].astype(str).str.strip().ne("")
    ].head(4)
    if len(candidates) < 4:
        raise ValueError("At least four complete documents are required to build the evaluation set.")

    samples: list[dict[str, Any]] = []
    for row in candidates.to_dict(orient="records"):
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        title_for_question = title.replace("'", "?")
        prefix = f"the paper '{title_for_question}' (paper_id: {paper_id})"
        specs = [
            ("summary", f"What is the summary of {prefix}?", first_sentence(str(row["summary"]))),
            ("authors", f"Who authored {prefix}?", str(row["authors_joined"])),
            ("date", f"When was {prefix} published?", str(row["published"])),
            ("categories", f"What categories does {prefix} have?", str(row["categories_joined"])),
        ]
        for question_type, question, ground_truth in specs:
            samples.append(
                {
                    "id": f"{paper_id}::{question_type}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
    write_json(output_path, samples)
    return samples

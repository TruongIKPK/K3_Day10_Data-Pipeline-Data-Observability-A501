from __future__ import annotations

import random
from datetime import timedelta

import pandas as pd

from core.utils import normalize_whitespace, now_utc, write_json

_SEED = 42
_NOISE_SUFFIX = " ##CORRUPTION-NOISE## xk39qz!!"
_TITLE_TRUNCATE_LEN = 5
_STALE_AGE_DAYS = 3650


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    parts = [
        f"Title: {row['title']}",
        f"Authors: {row['authors_joined']}" if row.get("authors_joined") else "",
        f"Categories: {row['categories_joined']}" if row.get("categories_joined") else "",
        f"Published: {row['published']}",
        f"Summary: {row['summary']}",
    ]
    return normalize_whitespace("\n".join(part for part in parts if part))


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate several realistic data-corruption scenarios on a clean dataframe.

    Pseudo-code:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    rng = random.Random(_SEED)
    actions: list[dict] = []

    if df.empty:
        write_json(
            output_log_path,
            {"generated_at": now_utc().isoformat(), "seed": _SEED, "source_rows": 0, "corrupted_rows": 0, "actions": actions},
        )
        return df.copy()

    def sample_indices(pool: list[int], fraction: float) -> list[int]:
        if not pool:
            return []
        count = min(len(pool), max(1, round(len(pool) * fraction)))
        return rng.sample(pool, count)

    def record_action(action_type: str, frame: pd.DataFrame, idx: list[int]) -> None:
        actions.append(
            {
                "type": action_type,
                "count": len(idx),
                "paper_ids": frame.loc[idx, "paper_id"].astype(str).tolist() if idx else [],
            }
        )

    corrupted = df.copy().reset_index(drop=True)

    # 1. Drop the most recently published records, biasing the remaining set stale.
    max_droppable = max(len(corrupted) - 4, 0)
    n_drop = min(max_droppable, max(1, round(len(corrupted) * 0.1))) if max_droppable else 0
    drop_idx = list(corrupted.sort_values("published", ascending=False).index[:n_drop])
    record_action("drop_latest_records", corrupted, drop_idx)
    corrupted = corrupted.drop(index=drop_idx).reset_index(drop=True)

    pool = list(corrupted.index)

    # 2. Blank the summary on a few rows.
    blank_idx = sample_indices(pool, 0.1)
    corrupted.loc[blank_idx, "summary"] = ""
    record_action("blank_summary", corrupted, blank_idx)

    # 3. Inject noise into the summary text of a few (still non-blank) rows.
    noise_pool = [idx for idx in pool if str(corrupted.at[idx, "summary"]).strip()]
    noise_idx = sample_indices(noise_pool, 0.1)
    for idx in noise_idx:
        corrupted.at[idx, "summary"] = normalize_whitespace(str(corrupted.at[idx, "summary"]) + _NOISE_SUFFIX)
    record_action("inject_noise", corrupted, noise_idx)

    # 4. Truncate the title so it falls below the quality-check minimum length.
    truncate_idx = sample_indices(pool, 0.1)
    for idx in truncate_idx:
        corrupted.at[idx, "title"] = str(corrupted.at[idx, "title"])[:_TITLE_TRUNCATE_LEN]
    record_action("truncate_title", corrupted, truncate_idx)

    # 5. Age a few records well past the freshness threshold.
    stale_idx = sample_indices(pool, 0.1)
    stale_date = (now_utc() - timedelta(days=_STALE_AGE_DAYS)).date().isoformat()
    for idx in stale_idx:
        corrupted.at[idx, "published"] = stale_date
        corrupted.at[idx, "age_days"] = _STALE_AGE_DAYS
    record_action("stale_published_date", corrupted, stale_idx)

    # 6. Duplicate a few rows to break paper_id uniqueness.
    dup_idx = sample_indices(pool, 0.1)
    record_action("duplicate_rows", corrupted, dup_idx)
    if dup_idx:
        corrupted = pd.concat([corrupted, corrupted.loc[dup_idx]], ignore_index=True)

    # 7. Rebuild derived text/columns so they reflect the corrupted fields above.
    corrupted["text_for_embedding"] = corrupted.apply(_rebuild_text_for_embedding, axis=1)
    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()

    write_json(
        output_log_path,
        {
            "generated_at": now_utc().isoformat(),
            "seed": _SEED,
            "source_rows": int(len(df)),
            "corrupted_rows": int(len(corrupted)),
            "actions": actions,
        },
    )
    return corrupted

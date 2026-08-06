from __future__ import annotations

from datetime import datetime
import html
import re

import pandas as pd

from ingestion.crossref import PaperRecord
from core.utils import compact_join, normalize_whitespace


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """TODO(student): clean raw records thanh dataframe san sang de embed.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    rows: list[dict] = []
    run_day = pd.Timestamp(run_date).date()

    def clean_text(value: object) -> str:
        text = html.unescape(str(value or ""))
        text = re.sub(r"<[^>]+>", " ", text)
        return normalize_whitespace(text)

    def clean_list(values: object) -> list[str]:
        if not isinstance(values, (list, tuple)):
            return []
        result = [clean_text(value) for value in values]
        return list(dict.fromkeys(value for value in result if value))

    for record in records:
        paper_id = clean_text(record.paper_id).lower()
        title = clean_text(record.title)
        summary = clean_text(record.summary)
        published = clean_text(record.published)
        if not paper_id or not title or not summary or not published:
            continue
        parsed_published = pd.to_datetime(published, errors="coerce")
        if pd.isna(parsed_published):
            continue
        published = parsed_published.date().isoformat()
        age_days = (run_day - parsed_published.date()).days
        authors = clean_list(record.authors)
        categories = clean_list(record.categories)
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        text_for_embedding = normalize_whitespace(
            "\n".join(
                part
                for part in (
                    f"Title: {title}",
                    f"Authors: {authors_joined}" if authors_joined else "",
                    f"Categories: {categories_joined}" if categories_joined else "",
                    f"Published: {published}",
                    f"Summary: {summary}",
                )
                if part
            )
        )
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": clean_text(record.primary_category),
                "published": published,
                "updated": clean_text(record.updated),
                "abs_url": clean_text(record.abs_url),
                "pdf_url": clean_text(record.pdf_url),
                "comment": clean_text(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": int(age_days),
                "text_for_embedding": text_for_embedding,
            }
        )

    columns = [
        "paper_id", "title", "summary", "authors", "categories", "primary_category",
        "published", "updated", "abs_url", "pdf_url", "comment", "authors_joined",
        "categories_joined", "summary_chars", "age_days", "text_for_embedding",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows, columns=columns)
    frame = frame.drop_duplicates(subset=["paper_id"], keep="first")
    frame = frame.sort_values(["published", "paper_id"], ascending=[False, True], kind="stable")
    return frame.reset_index(drop=True)

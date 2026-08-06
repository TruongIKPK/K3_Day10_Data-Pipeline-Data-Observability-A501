from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
import html
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """TODO(student): parse Crossref payload thanh list PaperRecord.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    message = payload.get("message") if isinstance(payload, dict) else None
    items = message.get("items", []) if isinstance(message, dict) else []
    parsed: list[PaperRecord] = []

    def clean_text(value: object) -> str:
        text = html.unescape(str(value or ""))
        text = re.sub(r"<[^>]+>", " ", text)
        return normalize_whitespace(text)

    def parse_date(value: object) -> str:
        if not isinstance(value, dict):
            return ""
        parts = value.get("date-parts")
        if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
            return ""
        values = parts[0]
        if not values or not isinstance(values[0], int):
            return ""
        try:
            year = values[0]
            month = int(values[1]) if len(values) > 1 else 1
            day = int(values[2]) if len(values) > 2 else 1
            return date(year, month, day).isoformat()
        except (TypeError, ValueError):
            return ""

    def parse_timestamp(value: object) -> str:
        if not isinstance(value, str) or not value:
            return ""
        try:
            parsed_date = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed_date.date().isoformat()
        except ValueError:
            return ""

    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        paper_id = normalize_whitespace(str(item.get("DOI") or "")).lower()
        title_values = item.get("title") or []
        title = clean_text(title_values[0] if isinstance(title_values, list) and title_values else "")
        abstract = clean_text(item.get("abstract", ""))
        if not paper_id or not title or not abstract:
            continue

        authors: list[str] = []
        for author in item.get("author") or []:
            if not isinstance(author, dict):
                continue
            given = clean_text(author.get("given", ""))
            family = clean_text(author.get("family", ""))
            name = compact_join([given, family], sep=" ")
            if name:
                authors.append(name)

        categories = [
            clean_text(subject)
            for subject in item.get("subject") or []
            if clean_text(subject)
        ]
        deduped_categories = list(dict.fromkeys(categories))
        published = ""
        for key in ("published-print", "published-online", "issued", "created"):
            published = parse_date(item.get(key))
            if published:
                break
        if not published:
            continue

        updated = parse_timestamp((item.get("indexed") or {}).get("date-time"))
        links = item.get("link") or []
        pdf_url = ""
        for link in links:
            if not isinstance(link, dict):
                continue
            candidate = str(link.get("URL") or "")
            content_type = str(link.get("content-type") or "").lower()
            if "pdf" in content_type or candidate.lower().split("?")[0].endswith(".pdf"):
                pdf_url = candidate
                break

        container = item.get("container-title") or []
        container_name = clean_text(container[0] if isinstance(container, list) and container else "")
        publisher = clean_text(item.get("publisher", ""))
        parsed.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=abstract,
                authors=list(dict.fromkeys(authors)),
                categories=deduped_categories,
                primary_category=deduped_categories[0] if deduped_categories else "",
                published=published,
                updated=updated,
                abs_url=str(item.get("URL") or f"https://doi.org/{paper_id}"),
                pdf_url=pdf_url,
                comment=compact_join([container_name, publisher], sep=" ? "),
            )
        )

    unique: dict[str, PaperRecord] = {}
    for record in parsed:
        unique.setdefault(record.paper_id, record)
    return list(unique.values())


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """TODO(student): goi source API, luu raw response, parse thanh records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "day10-data-observability-lab/0.1 (Crossref metadata ingestion)",
    }
    last_error: Exception | None = None
    payload: dict | None = None
    for attempt in range(4):
        try:
            response = requests.get(settings.source_api, params=params, headers=headers, timeout=30)
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(min(delay, 8.0))
                continue
            response.raise_for_status()
            payload = response.json()
            break
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(min(2**attempt, 8.0))
                continue
            raise RuntimeError(f"Crossref request failed after retries: {exc}") from exc
    if payload is None:
        raise RuntimeError(f"Crossref request failed after retries: {last_error}")

    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    if not records:
        raise RuntimeError("Crossref returned no usable records after parsing.")
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """TODO(student): doc JSON snapshot va map thanh `PaperRecord`."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw records at {path} must be a JSON list.")
    records: list[PaperRecord] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record {index} at {path} is not an object.")
        try:
            records.append(
                PaperRecord(
                    paper_id=str(item["paper_id"]),
                    title=str(item["title"]),
                    summary=str(item["summary"]),
                    authors=[str(value) for value in item.get("authors", [])],
                    categories=[str(value) for value in item.get("categories", [])],
                    primary_category=str(item.get("primary_category", "")),
                    published=str(item["published"]),
                    updated=str(item.get("updated", "")),
                    abs_url=str(item.get("abs_url", "")),
                    pdf_url=str(item.get("pdf_url", "")),
                    comment=str(item.get("comment", "")),
                )
            )
        except KeyError as exc:
            raise ValueError(f"Raw record {index} at {path} is missing {exc.args[0]!r}.") from exc
    return records

#!/usr/bin/env python3
"""Remove DBLP homonym suffixes from existing TVCG data."""

import csv
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paperlib.crawlers.dblp import (
    AUTHOR_NAME_NORMALIZATION_NOTE,
    normalize_dblp_author_name,
)


def normalize_authors(value):
    if isinstance(value, list):
        return [normalize_dblp_author_name(name) for name in value]
    if isinstance(value, str):
        return "; ".join(
            normalize_dblp_author_name(name) for name in value.split(";")
        )
    return value


def is_tvcg_row(row):
    return (
        str(row.get("dblp_key", row.get("id", ""))).startswith("journals/tvcg/")
        or str(row.get("conference", "")).casefold().startswith("tvcg")
    )


def update_jsonl(path):
    changed = 0
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if is_tvcg_row(row) and "authors" in row:
            cleaned = normalize_authors(row["authors"])
            if cleaned != row["authors"]:
                row["authors"] = cleaned
                changed += 1
        rows.append(row)
    if changed:
        content = "".join(
            json.dumps(row, ensure_ascii=False) + "\n" for row in rows
        )
        _replace_text(path, content, bom=False)
    return changed


def update_delimited(path):
    delimiter = "\t" if path.suffix.casefold() == ".tsv" else ","
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames or "authors" not in fieldnames:
        return 0

    changed = 0
    for row in rows:
        if is_tvcg_row(row):
            cleaned = normalize_authors(row["authors"])
            if cleaned != row["authors"]:
                row["authors"] = cleaned
                changed += 1
    if not changed:
        return 0

    temporary = path.with_name(path.name + ".tmp")
    encoding = "utf-8-sig" if bom else "utf-8"
    with temporary.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    return changed


def update_summaries(data_dir):
    changed = 0
    for path in sorted((data_dir / "raw").glob("tvcg*/summary.json")):
        summary = json.loads(path.read_text(encoding="utf-8"))
        if summary.get("author_name_normalization") == AUTHOR_NAME_NORMALIZATION_NOTE:
            continue
        summary["author_name_normalization"] = AUTHOR_NAME_NORMALIZATION_NOTE
        _replace_text(
            path,
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            bom=False,
        )
        changed += 1
    return changed


def update_database(path):
    changed = 0
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """
            select id, authors, raw_json
            from papers
            where id like 'journals/tvcg/%' or lower(conference) like 'tvcg%'
            """
        ).fetchall()
        for paper_id, authors, raw_json in rows:
            cleaned_authors = normalize_authors(authors)
            cleaned_raw_json = raw_json
            try:
                raw = json.loads(raw_json or "{}")
            except json.JSONDecodeError:
                raw = None
            if isinstance(raw, dict) and "authors" in raw:
                cleaned = normalize_authors(raw["authors"])
                if cleaned != raw["authors"]:
                    raw["authors"] = cleaned
                    cleaned_raw_json = json.dumps(raw, ensure_ascii=False)
            if cleaned_authors == authors and cleaned_raw_json == raw_json:
                continue
            conn.execute(
                """
                update papers
                set authors = ?, raw_json = ?, updated_at = ?
                where id = ?
                """,
                (cleaned_authors, cleaned_raw_json, now, paper_id),
            )
            changed += 1
    return changed


def _replace_text(path, content, bom):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        content,
        encoding="utf-8-sig" if bom else "utf-8",
        newline="",
    )
    temporary.replace(path)


def main():
    data_dir = ROOT / "data"
    results = {}
    for path in sorted((data_dir / "raw").rglob("*.jsonl")):
        count = update_jsonl(path)
        if count:
            results[str(path.relative_to(ROOT))] = count
    for pattern in ("*.csv", "*.tsv"):
        for path in sorted(data_dir.rglob(pattern)):
            count = update_delimited(path)
            if count:
                results[str(path.relative_to(ROOT))] = count
    results["data/raw/tvcg*/summary.json"] = update_summaries(data_dir)
    results["data/papers.sqlite"] = update_database(data_dir / "papers.sqlite")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

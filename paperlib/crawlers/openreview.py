import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


API_BASE = "https://api2.openreview.net/notes"
LIMIT = 1000


@dataclass(frozen=True)
class OutputPaths:
    jsonl: Path
    csv: Path
    summary: Path


def output_paths(data_dir, conference_key):
    raw_dir = Path(data_dir) / "raw" / conference_key
    return OutputPaths(
        jsonl=raw_dir / "accepted_papers.jsonl",
        csv=raw_dir / "accepted_papers.csv",
        summary=raw_dir / "summary.json",
    )


def get_value(content, key, default=None):
    value = content.get(key, {})
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return default


def normalize_note(note):
    content = note.get("content", {})
    venue = get_value(content, "venue", "")
    authors = get_value(content, "authors", [])
    authorids = get_value(content, "authorids", [])
    if not isinstance(authors, list):
        authors = []
    if not isinstance(authorids, list):
        authorids = []
    forum = note.get("forum", note.get("id", ""))
    return {
        "openreview_id": note.get("id", ""),
        "forum": forum,
        "number": note.get("number", ""),
        "venue": venue,
        "title": get_value(content, "title", ""),
        "authors": authors,
        "authorids": authorids,
        "abstract": get_value(content, "abstract", ""),
        "primary_area": get_value(content, "primary_area", ""),
        "keywords": get_value(content, "keywords", []),
        "tldr": get_value(content, "TLDR", ""),
        "pdf": get_value(content, "pdf", ""),
        "url": f"https://openreview.net/forum?id={forum}",
    }


def normalize_fallback_row(row, venue):
    paper_id = row.get("id", "")
    return {
        "openreview_id": paper_id,
        "forum": paper_id,
        "number": row.get("number", ""),
        "venue": venue,
        "title": row.get("title", "") or "",
        "authors": _split_semicolon(row.get("author", "")),
        "authorids": _split_semicolon(row.get("authorids", "")),
        "abstract": row.get("abstract", "") or "",
        "primary_area": row.get("primary_area", "") or "",
        "keywords": _split_semicolon(row.get("keywords", "")),
        "tldr": row.get("tldr", "") or "",
        "pdf": row.get("pdf", "") or "",
        "url": row.get("site", "") or f"https://openreview.net/forum?id={paper_id}",
    }


def fetch_page(api_base, invitation, venue, limit, offset):
    params = {
        "invitation": invitation,
        "content.venue": venue,
        "limit": str(limit),
        "offset": str(offset),
    }
    url = f"{api_base}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_venue(config, venue, limit=LIMIT):
    notes = []
    offset = 0
    while True:
        payload = fetch_page(API_BASE, config.invitation, venue, limit, offset)
        page = payload.get("notes", [])
        if not page:
            break
        notes.extend(page)
        if len(page) < limit:
            break
        offset += limit
        time.sleep(0.2)
    return notes


def fetch_by_venueid(config, limit=LIMIT):
    if not config.venueid:
        return []
    notes = []
    offset = 0
    while True:
        params = {
            "invitation": config.invitation,
            "content.venueid": config.venueid,
            "limit": str(limit),
            "offset": str(offset),
        }
        url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        page = payload.get("notes", [])
        if not page:
            break
        notes.extend(page)
        if len(page) < limit:
            break
        offset += limit
        time.sleep(0.2)
    return notes


def fetch_conference(config, data_dir):
    seen = {}
    counts_by_query = {}
    try:
        for venue in config.venues:
            notes = fetch_venue(config, venue)
            counts_by_query[venue] = len(notes)
            for note in notes:
                paper = normalize_note(note)
                seen[paper["openreview_id"]] = paper
    except urllib.error.HTTPError as error:
        if error.code != 403 or not config.fallback_jsonl_url:
            raise
        return fetch_conference_from_fallback_jsonl(config, data_dir, error)

    papers = sorted(
        seen.values(),
        key=lambda item: (
            item.get("venue", ""),
            str(item.get("title", "")).casefold(),
            item.get("openreview_id", ""),
        ),
    )
    paths = output_paths(data_dir, config.key)
    summary = build_summary(config, papers, counts_by_query, paths)
    if config.venueid:
        venueid_notes = fetch_by_venueid(config)
        venueid_ids = {note.get("id", "") for note in venueid_notes}
        queried_ids = set(seen.keys())
        summary["venueid_crosscheck"] = {
            "venueid": config.venueid,
            "total": len(venueid_ids),
            "matches_queried_venues": venueid_ids == queried_ids,
            "missing_from_queried_venues": sorted(venueid_ids - queried_ids),
            "extra_from_queried_venues": sorted(queried_ids - venueid_ids),
        }
    write_outputs(papers, paths, summary)
    return summary


def fetch_conference_from_fallback_jsonl(config, data_dir, source_error=None):
    status_venues = dict(config.fallback_status_venues)
    seen = {}
    counts_by_query = {venue: 0 for venue in status_venues.values()}
    with urllib.request.urlopen(config.fallback_jsonl_url, timeout=120) as response:
        for raw in response:
            if not raw.strip():
                continue
            row = json.loads(raw)
            venue = status_venues.get(row.get("status", ""))
            if not venue:
                continue
            paper = normalize_fallback_row(row, venue)
            seen[paper["openreview_id"]] = paper
            counts_by_query[venue] += 1

    papers = sorted(
        seen.values(),
        key=lambda item: (
            item.get("venue", ""),
            str(item.get("title", "")).casefold(),
            item.get("openreview_id", ""),
        ),
    )
    paths = output_paths(data_dir, config.key)
    summary = build_summary(config, papers, counts_by_query, paths)
    summary["fallback_source"] = config.fallback_jsonl_url
    if source_error is not None:
        summary["fallback_reason"] = f"OpenReview API returned HTTP {source_error.code}"
    write_outputs(papers, paths, summary)
    return summary


def build_summary(config, papers, counts_by_query, paths):
    missing = {
        "title": sum(1 for paper in papers if not paper["title"]),
        "authors": sum(1 for paper in papers if not paper["authors"]),
        "abstract": sum(1 for paper in papers if not paper["abstract"]),
    }
    counts_by_venue = {}
    for paper in papers:
        counts_by_venue[paper["venue"]] = counts_by_venue.get(paper["venue"], 0) + 1
    return {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_api": API_BASE,
        "invitation": config.invitation,
        "queried_venues": list(config.venues),
        "counts_by_query": counts_by_query,
        "counts_by_venue": counts_by_venue,
        "total_unique_papers": len(papers),
        "missing_required_fields": missing,
        "outputs": {
            "jsonl": str(paths.jsonl),
            "csv": str(paths.csv),
        },
    }


def write_outputs(papers, paths, summary):
    paths.jsonl.parent.mkdir(parents=True, exist_ok=True)
    with paths.jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for paper in papers:
            handle.write(json.dumps(paper, ensure_ascii=False) + "\n")

    fieldnames = [
        "openreview_id",
        "forum",
        "number",
        "venue",
        "title",
        "authors",
        "authorids",
        "abstract",
        "primary_area",
        "keywords",
        "tldr",
        "pdf",
        "url",
    ]
    with paths.csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for paper in papers:
            row = dict(paper)
            row["authors"] = "; ".join(paper["authors"])
            row["authorids"] = "; ".join(paper["authorids"])
            row["keywords"] = (
                "; ".join(paper["keywords"])
                if isinstance(paper["keywords"], list)
                else ""
            )
            writer.writerow(row)

    paths.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _split_semicolon(value):
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [item.strip() for item in str(value or "").split(";") if item.strip()]

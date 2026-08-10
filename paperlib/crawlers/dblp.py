import csv
import json
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from paperlib.crawlers.openreview import output_paths


USER_AGENT = "paperlib-dblp-crawler/1.0 (metadata research)"
TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 3


class DblpCompletenessError(RuntimeError):
    """Raised when DBLP's two volume representations do not agree."""


class _DblpEntryCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.article_count = 0

    def handle_starttag(self, tag, attrs):
        if tag.casefold() != "li":
            return
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())
        if {"entry", "article"}.issubset(classes):
            self.article_count += 1


@dataclass(frozen=True)
class DblpVolumePayload:
    xml: bytes
    html: str


def download(url, timeout=TIMEOUT_SECONDS, max_attempts=MAX_ATTEMPTS):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt == max_attempts:
                raise
            time.sleep(0.5 * (2 ** (attempt - 1)))
    raise AssertionError("unreachable")


def fetch_volume_payload(config):
    xml = download(config.xml_url)
    # Keep the two requests polite while still validating against DBLP only.
    time.sleep(0.25)
    html = download(config.html_url).decode("utf-8")
    return DblpVolumePayload(xml=xml, html=html)


def parse_dblp_xml(xml, expected_year, expected_volume):
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise DblpCompletenessError(f"DBLP returned invalid XML: {error}") from error

    articles = []
    seen_keys = set()
    # DBLP volume exports use a <bht> wrapper with records nested below
    # <dblpcites><r>; accepting descendants also keeps plain <dblp> fixtures
    # and older exports compatible.
    for element in root.findall(".//article"):
        paper = _normalize_article(element)
        key = paper["dblp_key"]
        if not key:
            raise DblpCompletenessError("DBLP article is missing its record key")
        if key in seen_keys:
            raise DblpCompletenessError(f"Duplicate DBLP record key: {key}")
        seen_keys.add(key)
        articles.append(paper)

    if not articles:
        raise DblpCompletenessError("DBLP volume contains no article records")

    wrong_scope = [
        paper["dblp_key"]
        for paper in articles
        if paper["year"] != expected_year or paper["volume"] != str(expected_volume)
    ]
    if wrong_scope:
        sample = ", ".join(wrong_scope[:5])
        raise DblpCompletenessError(
            f"DBLP volume contains {len(wrong_scope)} out-of-scope records: {sample}"
        )

    return sorted(
        articles,
        key=lambda paper: (
            _issue_sort_key(paper["issue"]),
            _pages_sort_key(paper["pages"]),
            paper["title"].casefold(),
            paper["dblp_key"],
        ),
    )


def count_html_articles(html):
    parser = _DblpEntryCounter()
    parser.feed(html)
    parser.close()
    return parser.article_count


def validate_completeness(papers, html_article_count, expected_issues=()):
    if html_article_count <= 0:
        raise DblpCompletenessError(
            "DBLP HTML volume page contains no li.entry.article records"
        )
    if len(papers) != html_article_count:
        raise DblpCompletenessError(
            "DBLP representations disagree: "
            f"XML has {len(papers)} articles, HTML has {html_article_count}"
        )
    actual_issues = {paper["issue"] for paper in papers if paper["issue"]}
    required_issues = set(expected_issues)
    if not required_issues:
        numeric_issues = []
        for issue in actual_issues:
            try:
                numeric_issues.append(int(issue))
            except ValueError as error:
                raise DblpCompletenessError(
                    f"DBLP volume has a non-numeric issue number: {issue}"
                ) from error
        if not numeric_issues:
            raise DblpCompletenessError("DBLP volume has no issue numbers")
        required_issues = {str(issue) for issue in range(1, max(numeric_issues) + 1)}
    missing_issues = required_issues - actual_issues
    if missing_issues:
        missing = ", ".join(sorted(missing_issues, key=_issue_sort_key))
        raise DblpCompletenessError(f"DBLP volume is missing expected issues: {missing}")


def fetch_journal_volume(config, data_dir):
    payload = fetch_volume_payload(config)
    papers = parse_dblp_xml(payload.xml, config.year, config.volume)
    html_article_count = count_html_articles(payload.html)
    validate_completeness(papers, html_article_count, config.expected_issues)

    paths = output_paths(data_dir, config.key)
    summary = build_summary(config, papers, html_article_count, paths)
    write_outputs(papers, paths, summary)
    return summary


def build_summary(config, papers, html_article_count, paths):
    counts_by_issue = {}
    for paper in papers:
        issue = paper["issue"] or "(missing)"
        counts_by_issue[issue] = counts_by_issue.get(issue, 0) + 1

    doi_counts = {}
    for paper in papers:
        if paper["doi"]:
            doi_counts[paper["doi"]] = doi_counts.get(paper["doi"], 0) + 1
    duplicate_dois = sorted(doi for doi, count in doi_counts.items() if count > 1)

    return {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "DBLP only",
        "source_xml": config.xml_url,
        "source_html": config.html_url,
        "year": config.year,
        "volume": config.volume,
        "expected_issues": list(config.expected_issues),
        "issue_validation": (
            "configured_complete_year"
            if config.expected_issues
            else "contiguous_through_latest_dblp_issue"
        ),
        "validated_issues": sorted(counts_by_issue, key=_issue_sort_key),
        "xml_article_count": len(papers),
        "html_article_count": html_article_count,
        "representations_match": len(papers) == html_article_count,
        "total_unique_papers": len(papers),
        "counts_by_issue": dict(
            sorted(counts_by_issue.items(), key=lambda item: _issue_sort_key(item[0]))
        ),
        "missing_required_fields": {
            "title": sum(1 for paper in papers if not paper["title"]),
            "authors": sum(1 for paper in papers if not paper["authors"]),
            "doi": sum(1 for paper in papers if not paper["doi"]),
            "issue": sum(1 for paper in papers if not paper["issue"]),
            "pages": sum(1 for paper in papers if not paper["pages"]),
        },
        "duplicate_dois": duplicate_dois,
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
        "id",
        "dblp_key",
        "title",
        "authors",
        "author_pids",
        "year",
        "volume",
        "issue",
        "pages",
        "journal",
        "doi",
        "url",
        "electronic_edition_urls",
        "abstract",
    ]
    with paths.csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for paper in papers:
            row = {field: paper.get(field, "") for field in fieldnames}
            row["authors"] = "; ".join(paper["authors"])
            row["author_pids"] = "; ".join(paper["author_pids"])
            row["electronic_edition_urls"] = "; ".join(
                paper["electronic_edition_urls"]
            )
            writer.writerow(row)

    paths.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _normalize_article(element):
    key = element.get("key", "").strip()
    authors = []
    author_pids = []
    for author in element.findall("author"):
        authors.append(_text(author))
        author_pids.append(author.get("pid", "").strip())

    electronic_editions = [
        _text(node) for node in element.findall("ee") if _text(node)
    ]
    doi = ""
    for url in electronic_editions:
        lowered = url.casefold()
        marker = "doi.org/"
        if marker in lowered:
            doi = url[lowered.index(marker) + len(marker) :].strip().casefold()
            break

    return {
        "id": key,
        "dblp_key": key,
        "title": _text(element.find("title")).removesuffix("."),
        "authors": authors,
        "author_pids": author_pids,
        "year": _integer_text(element.find("year")),
        "volume": _text(element.find("volume")),
        "issue": _text(element.find("number")),
        "pages": _text(element.find("pages")),
        "journal": _text(element.find("journal")),
        "doi": doi,
        "url": f"https://dblp.org/rec/{key}",
        "electronic_edition_urls": electronic_editions,
        # DBLP does not publish abstracts; keep the common app schema explicit.
        "abstract": "",
    }


def _text(element):
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _integer_text(element):
    value = _text(element)
    try:
        return int(value)
    except ValueError:
        return 0


def _issue_sort_key(value):
    first = str(value).split("-", 1)[0]
    try:
        return (0, int(first), str(value))
    except ValueError:
        return (1, 0, str(value))


def _pages_sort_key(value):
    first = str(value).split("-", 1)[0]
    try:
        return (0, int(first), str(value))
    except ValueError:
        return (1, 0, str(value))

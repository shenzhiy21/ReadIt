import pytest

from paperlib.crawlers.conferences import get_conference
from paperlib.crawlers.openreview import (
    build_summary,
    normalize_fallback_row,
    normalize_note,
    output_paths,
)


def test_get_conference_returns_icml2026_config():
    config = get_conference("icml2026")

    assert config.key == "icml2026"
    assert config.invitation == "ICML.cc/2026/Conference/-/Submission"
    assert "ICML 2026 regular" in config.venues
    assert config.venueid == "ICML.cc/2026/Conference"


def test_get_conference_returns_iclr2026_config():
    config = get_conference("iclr2026")

    assert config.key == "iclr2026"
    assert config.name == "ICLR 2026"
    assert config.invitation == "ICLR.cc/2026/Conference/-/Submission"
    assert "ICLR 2026 Poster" in config.venues
    assert config.venueid == "ICLR.cc/2026/Conference"


def test_iclr2026_fallback_includes_all_main_accepted_statuses():
    config = get_conference("iclr2026")

    assert ("Poster", "ICLR 2026 Poster") in config.fallback_status_venues
    assert ("SPOT", "ICLR 2026 Spotlight") in config.fallback_status_venues
    assert ("Oral", "ICLR 2026 Oral") in config.fallback_status_venues


def test_conference_configs_have_display_names():
    assert get_conference("icml2026").name == "ICML 2026"


def test_get_conference_rejects_unknown_key():
    with pytest.raises(KeyError, match="Unknown conference"):
        get_conference("missing")


def test_normalize_note_extracts_openreview_fields():
    note = {
        "id": "abc",
        "forum": "abc",
        "number": 42,
        "content": {
            "venue": {"value": "ICML 2026 regular"},
            "title": {"value": "Chart QA"},
            "authors": {"value": ["A", "B"]},
            "authorids": {"value": ["~A1", "~B1"]},
            "abstract": {"value": "Abstract"},
            "primary_area": {"value": "evaluation"},
            "keywords": {"value": ["chart"]},
            "TLDR": {"value": "Short"},
            "pdf": {"value": "/pdf/abc.pdf"},
        },
    }

    paper = normalize_note(note)

    assert paper["openreview_id"] == "abc"
    assert paper["title"] == "Chart QA"
    assert paper["authors"] == ["A", "B"]
    assert paper["url"] == "https://openreview.net/forum?id=abc"


def test_normalize_fallback_row_maps_accepted_jsonl_fields():
    row = {
        "id": "abc",
        "status": "Poster",
        "title": "Chart QA",
        "author": "A;B",
        "authorids": "~A1;~B1",
        "abstract": "Abstract",
        "primary_area": "evaluation",
        "keywords": "chart;qa",
        "tldr": "Short",
        "site": "https://openreview.net/forum?id=abc",
    }

    paper = normalize_fallback_row(row, "ICLR 2026 Poster")

    assert paper["openreview_id"] == "abc"
    assert paper["forum"] == "abc"
    assert paper["venue"] == "ICLR 2026 Poster"
    assert paper["title"] == "Chart QA"
    assert paper["authors"] == ["A", "B"]
    assert paper["authorids"] == ["~A1", "~B1"]
    assert paper["keywords"] == ["chart", "qa"]
    assert paper["url"] == "https://openreview.net/forum?id=abc"


def test_output_paths_use_standard_names(tmp_path):
    paths = output_paths(tmp_path, "icml2026")

    assert paths.jsonl == tmp_path / "raw" / "icml2026" / "accepted_papers.jsonl"
    assert paths.csv == tmp_path / "raw" / "icml2026" / "accepted_papers.csv"
    assert paths.summary == tmp_path / "raw" / "icml2026" / "summary.json"


def test_build_summary_uses_actual_output_paths(tmp_path):
    config = get_conference("icml2026")
    paths = output_paths(tmp_path, "icml2026")

    summary = build_summary(config, [], {}, paths)

    assert summary["outputs"]["jsonl"] == str(paths.jsonl)
    assert summary["outputs"]["csv"] == str(paths.csv)

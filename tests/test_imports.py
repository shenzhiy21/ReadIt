from pathlib import Path

import pytest

from paperlib.config import default_db_path, raw_publication_dir
from paperlib.imports import find_paper_metadata


def test_default_paths_are_under_data():
    assert default_db_path() == Path("data") / "papers.sqlite"
    assert raw_publication_dir("icml2026") == Path("data") / "raw" / "icml2026"


def test_find_paper_metadata_prefers_jsonl(tmp_path):
    raw_dir = tmp_path / "raw" / "icml2026"
    raw_dir.mkdir(parents=True)
    jsonl = raw_dir / "accepted_papers.jsonl"
    csv = raw_dir / "accepted_papers.csv"
    jsonl.write_text("{}", encoding="utf-8")
    csv.write_text("id,title\n", encoding="utf-8")

    found = find_paper_metadata(tmp_path, "icml2026")

    assert found == jsonl


def test_find_paper_metadata_falls_back_to_csv(tmp_path):
    raw_dir = tmp_path / "raw" / "icml2026"
    raw_dir.mkdir(parents=True)
    csv = raw_dir / "accepted_papers.csv"
    csv.write_text("id,title\n", encoding="utf-8")

    found = find_paper_metadata(tmp_path, "icml2026")

    assert found == csv


def test_find_paper_metadata_raises_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="accepted_papers.jsonl"):
        find_paper_metadata(tmp_path, "icml2026")

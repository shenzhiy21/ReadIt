# Project Structure Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move project code into a lightweight package, move all paper data under local-only `data/`, and replace the ICML-only crawler script with a reusable OpenReview conference crawler.

**Architecture:** Keep `app.py` as a thin local entry point and move Flask routes to `paperlib.web`, SQLite logic to `paperlib.store`, path lookup to `paperlib.config`/`paperlib.imports`, and crawler logic to `paperlib.crawlers`. Local data lives under `data/` and is ignored by git.

**Tech Stack:** Python 3, Flask, SQLite, pytest, vanilla frontend assets, OpenReview API over `urllib`.

---

## File Structure

- Create `paperlib/__init__.py`: package marker.
- Create `paperlib/config.py`: default data directory, database path, and default conference key.
- Create `paperlib/imports.py`: locate full-paper metadata files for a conference.
- Create `paperlib/store.py`: move existing `paper_store.py` data layer here.
- Create `paperlib/web.py`: move existing Flask app factory and routes here.
- Create `paperlib/crawlers/__init__.py`: crawler package marker.
- Create `paperlib/crawlers/conferences.py`: conference configuration registry.
- Create `paperlib/crawlers/openreview.py`: reusable OpenReview fetch, normalize, and write logic.
- Create `tools/fetch_papers.py`: CLI wrapper for conference crawling.
- Modify `app.py`: thin entry point importing `paperlib.web:create_app`.
- Modify `tests/test_paper_store.py`: import `PaperStore` from `paperlib.store`.
- Modify `tests/test_api.py`: import `create_app` from `paperlib.web` and assert new default import layout.
- Create `tests/test_imports.py`: metadata path lookup tests.
- Create `tests/test_crawlers.py`: conference config and normalization tests without network.
- Modify `.gitignore`: ignore `data/`.
- Modify `README.md`: document new layout and commands.
- Move local files into `data/`.
- Delete `download_icml2026_accepted.py` after `tools/fetch_papers.py` replaces it.

## Task 1: Path Configuration And Import Lookup

**Files:**
- Create: `tests/test_imports.py`
- Create: `paperlib/__init__.py`
- Create: `paperlib/config.py`
- Create: `paperlib/imports.py`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

import pytest

from paperlib.config import default_db_path, raw_conference_dir
from paperlib.imports import find_paper_metadata


def test_default_paths_are_under_data():
    assert default_db_path() == Path("data") / "papers.sqlite"
    assert raw_conference_dir("icml2026") == Path("data") / "raw" / "icml2026"


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
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/test_imports.py -v`

Expected: FAIL because `paperlib.config` and `paperlib.imports` do not exist.

- [ ] **Step 3: Implement minimal modules**

Create:

```python
# paperlib/config.py
from pathlib import Path

DEFAULT_CONFERENCE = "icml2026"


def data_dir():
    return Path("data")


def default_db_path():
    return data_dir() / "papers.sqlite"


def raw_conference_dir(conference_key, base_data_dir=None):
    base = Path(base_data_dir) if base_data_dir is not None else data_dir()
    return base / "raw" / conference_key
```

Create:

```python
# paperlib/imports.py
from pathlib import Path


def find_paper_metadata(data_dir, conference_key):
    raw_dir = Path(data_dir) / "raw" / conference_key
    jsonl_path = raw_dir / "accepted_papers.jsonl"
    csv_path = raw_dir / "accepted_papers.csv"
    if jsonl_path.exists():
        return jsonl_path
    if csv_path.exists():
        return csv_path
    raise FileNotFoundError(
        f"Missing paper metadata: expected {jsonl_path} or {csv_path}"
    )
```

Create empty `paperlib/__init__.py`.

- [ ] **Step 4: Run tests and verify pass**

Run: `python -m pytest tests/test_imports.py -v`

Expected: PASS.

## Task 2: Move Store Into Package

**Files:**
- Move: `paper_store.py` to `paperlib/store.py`
- Modify: `tests/test_paper_store.py`

- [ ] **Step 1: Write failing import change**

Change:

```python
from paper_store import PaperStore
```

to:

```python
from paperlib.store import PaperStore
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/test_paper_store.py -v`

Expected: FAIL because `paperlib.store` does not exist.

- [ ] **Step 3: Move implementation**

Move `paper_store.py` to `paperlib/store.py`. Do not change behavior.

- [ ] **Step 4: Run store tests**

Run: `python -m pytest tests/test_paper_store.py -v`

Expected: PASS.

## Task 3: Move Flask App Into Package And Use Configured Data Paths

**Files:**
- Create: `paperlib/web.py`
- Modify: `app.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Update API tests to package import and new default metadata layout**

Change:

```python
from app import create_app
```

to:

```python
from paperlib.web import create_app
```

Update the default import test to write:

```python
raw_dir = tmp_path / "raw" / "icml2026"
raw_dir.mkdir(parents=True)
jsonl = raw_dir / "accepted_papers.jsonl"
jsonl.write_text(
    '{"openreview_id":"paper-1","title":"Chart QA","abstract":"charts"}\n',
    encoding="utf-8",
)
app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
```

Update the CSV fallback test similarly with `accepted_papers.csv` under
`tmp_path / "raw" / "icml2026"`.

- [ ] **Step 2: Run API tests and verify failure**

Run: `python -m pytest tests/test_api.py -v`

Expected: FAIL because `paperlib.web` does not exist.

- [ ] **Step 3: Move app factory**

Move the existing Flask app factory from `app.py` into `paperlib/web.py`.
Change imports:

```python
from paperlib.config import DEFAULT_CONFERENCE, default_db_path
from paperlib.imports import find_paper_metadata
from paperlib.store import PaperStore
```

Set `create_app(db_path=None, data_dir=None, conference_key=DEFAULT_CONFERENCE)`.
When `db_path` is `None`, use `default_db_path()`. When `data_dir` is `None`,
use `Path("data")`.

In `/api/import/papers`, replace hard-coded root filenames with:

```python
metadata_path = find_paper_metadata(data_dir, conference_key)
if metadata_path.suffix == ".jsonl":
    return jsonify(store.import_papers_jsonl(metadata_path))
return jsonify(store.import_papers_csv(metadata_path))
```

- [ ] **Step 4: Replace root app entry point**

Replace `app.py` with:

```python
from paperlib.web import create_app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)
```

- [ ] **Step 5: Run API tests**

Run: `python -m pytest tests/test_api.py -v`

Expected: PASS.

## Task 4: Reusable OpenReview Crawler

**Files:**
- Create: `tests/test_crawlers.py`
- Create: `paperlib/crawlers/__init__.py`
- Create: `paperlib/crawlers/conferences.py`
- Create: `paperlib/crawlers/openreview.py`
- Create: `tools/fetch_papers.py`
- Delete: `download_icml2026_accepted.py`

- [ ] **Step 1: Write failing crawler tests**

```python
from pathlib import Path

import pytest

from paperlib.crawlers.conferences import get_conference
from paperlib.crawlers.openreview import normalize_note, output_paths


def test_get_conference_returns_icml2026_config():
    config = get_conference("icml2026")

    assert config.key == "icml2026"
    assert config.invitation == "ICML.cc/2026/Conference/-/Submission"
    assert "ICML 2026 regular" in config.venues
    assert config.venueid == "ICML.cc/2026/Conference"


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


def test_output_paths_use_standard_names(tmp_path):
    paths = output_paths(tmp_path, "icml2026")

    assert paths.jsonl == tmp_path / "raw" / "icml2026" / "accepted_papers.jsonl"
    assert paths.csv == tmp_path / "raw" / "icml2026" / "accepted_papers.csv"
    assert paths.summary == tmp_path / "raw" / "icml2026" / "summary.json"
```

- [ ] **Step 2: Run crawler tests and verify failure**

Run: `python -m pytest tests/test_crawlers.py -v`

Expected: FAIL because crawler modules do not exist.

- [ ] **Step 3: Implement conference config**

Define a dataclass:

```python
@dataclass(frozen=True)
class OpenReviewConference:
    key: str
    invitation: str
    venues: tuple[str, ...]
    venueid: str | None = None
```

Add `CONFERENCES` with `icml2026`, and `get_conference(key)`.

- [ ] **Step 4: Implement OpenReview crawler module**

Move reusable logic from `download_icml2026_accepted.py` into
`paperlib/crawlers/openreview.py`:

- `get_value(content, key, default=None)`
- `normalize_note(note)`
- `fetch_page(api_base, invitation, venue, limit, offset)`
- `fetch_venue(config, venue, limit=1000)`
- `fetch_by_venueid(config, limit=1000)`
- `output_paths(data_dir, conference_key)`
- `write_outputs(papers, paths, summary)`
- `fetch_conference(config, data_dir)`

Keep output names `accepted_papers.jsonl`, `accepted_papers.csv`, and
`summary.json`.

- [ ] **Step 5: Implement CLI**

Create `tools/fetch_papers.py`:

```python
#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paperlib.config import data_dir
from paperlib.crawlers.conferences import get_conference
from paperlib.crawlers.openreview import fetch_conference


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("conference")
    parser.add_argument("--data-dir", default=str(data_dir()))
    args = parser.parse_args()

    config = get_conference(args.conference)
    summary = fetch_conference(config, Path(args.data_dir))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Delete old root script**

Delete `download_icml2026_accepted.py`.

- [ ] **Step 7: Run crawler tests**

Run: `python -m pytest tests/test_crawlers.py -v`

Expected: PASS.

## Task 5: Move Local Data Under `data/`

**Files:**
- Move local data files.
- Modify: `.gitignore`
- Modify: tests only if path assumptions remain.

- [ ] **Step 1: Update `.gitignore`**

Ensure it contains:

```gitignore
data/
*.sqlite
*.sqlite3
*.db
*.log
__pycache__/
.pytest_cache/
.venv/
```

- [ ] **Step 2: Move files without silent overwrite**

Create directories:

```powershell
New-Item -ItemType Directory -Force -Path data\raw\icml2026
New-Item -ItemType Directory -Force -Path data\collections
```

Move:

```powershell
Move-Item -LiteralPath icml2026_accepted_papers.jsonl -Destination data\raw\icml2026\accepted_papers.jsonl
Move-Item -LiteralPath icml2026_accepted_papers.csv -Destination data\raw\icml2026\accepted_papers.csv
Move-Item -LiteralPath icml2026_accepted_papers_summary.json -Destination data\raw\icml2026\summary.json
Move-Item -LiteralPath icml2026_chartqa_mllm_firstpass_keep.tsv -Destination data\collections\icml2026_chartqa_mllm_firstpass_keep.tsv
Move-Item -LiteralPath icml2026_chartqa_mllm_screened_candidates.tsv -Destination data\collections\icml2026_chartqa_mllm_screened_candidates.tsv
Move-Item -LiteralPath papers.sqlite -Destination data\papers.sqlite
```

Before each move, check the destination does not exist. If it exists, stop and
inspect rather than overwriting.

- [ ] **Step 3: Run import API test**

Run: `python -m pytest tests/test_api.py::test_api_imports_default_papers -v`

Expected: PASS.

## Task 6: README And Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Document:

```powershell
python tools/fetch_papers.py icml2026
python app.py
```

Document local-only paths:

- `data/raw/<conference>/`
- `data/collections/`
- `data/papers.sqlite`

Explain that `data/` is ignored by git.

- [ ] **Step 2: Run full tests**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 3: Start or restart local app**

Run:

```powershell
python app.py
```

Expected: app listens at `http://127.0.0.1:5000`.

- [ ] **Step 4: HTTP smoke test**

Run a local smoke script that verifies:

- `GET /` contains `ICML 2026 Paper Collections`.
- `POST /api/import/papers` imports from `data/raw/icml2026/`.
- `POST /api/import/collection` still imports an uploaded TSV.
- `GET /api/export/collections` returns TSV.

Expected: script exits 0.

## Self-Review

- Spec coverage: plan covers package layout, local-only data, crawler extensibility, migration, `.gitignore`, README, and tests.
- Placeholder scan: no placeholder markers are present.
- Type consistency: `PaperStore`, `create_app`, `find_paper_metadata`, `OpenReviewConference`, and `fetch_conference` are named consistently across tasks.

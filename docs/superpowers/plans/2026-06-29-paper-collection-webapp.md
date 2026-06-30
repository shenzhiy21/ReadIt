# Paper Collection Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Flask + SQLite web app for importing ICML 2026 papers and managing TSV-backed paper collections.

**Architecture:** The app has a focused SQLite data layer in `paper_store.py`, a thin Flask API/static server in `app.py`, and a single-page frontend under `static/`. Import logic is transaction-based and preserves collection memberships when the full ICML paper corpus is re-imported.

**Tech Stack:** Python 3, Flask, SQLite via `sqlite3`, pytest, vanilla HTML/CSS/JavaScript.

---

## File Structure

- Create `paper_store.py`: database schema, importers, collection membership operations, search/filter queries, TSV export.
- Create `app.py`: Flask app factory, API routes, static file serving, startup command.
- Create `static/index.html`: three-panel reading interface.
- Create `static/styles.css`: compact reading-focused layout.
- Create `static/app.js`: frontend state, API calls, import/export/membership interactions.
- Create `tests/test_paper_store.py`: data-layer TDD coverage.
- Create `tests/test_api.py`: Flask API TDD coverage.
- Create `requirements.txt`: Flask and pytest dependencies.
- Create `README.md`: local startup, import, backup, export instructions.

## Task 1: Database Schema And Core Import

**Files:**
- Create: `tests/test_paper_store.py`
- Create: `paper_store.py`

- [ ] **Step 1: Write failing tests for schema initialization and full paper import**

```python
import json
import sqlite3

from paper_store import PaperStore


def test_init_creates_tables(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    store = PaperStore(db_path)
    store.init_db()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

    assert {"papers", "collections", "paper_collections"} <= tables


def test_import_jsonl_upserts_papers_without_collections(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    jsonl_path = tmp_path / "papers.jsonl"
    jsonl_path.write_text(
        json.dumps(
            {
                "openreview_id": "paper-1",
                "forum": "paper-1",
                "venue": "ICML 2026 regular",
                "title": "Chart Reasoning",
                "authors": ["A", "B"],
                "abstract": "Reasoning over charts.",
                "primary_area": "general_machine_learning->evaluation",
                "keywords": ["chart", "reasoning"],
                "pdf": "/pdf/paper-1.pdf",
                "url": "https://openreview.net/forum?id=paper-1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    store = PaperStore(db_path)
    store.init_db()

    result = store.import_papers_jsonl(jsonl_path)
    paper = store.get_paper("paper-1")

    assert result == {"imported": 1}
    assert paper["title"] == "Chart Reasoning"
    assert paper["authors"] == "A; B"
    assert paper["collections"] == []
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `python -m pytest tests/test_paper_store.py::test_init_creates_tables tests/test_paper_store.py::test_import_jsonl_upserts_papers_without_collections -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'paper_store'`.

- [ ] **Step 3: Implement minimal schema and JSONL import**

Implement `PaperStore.__init__`, `init_db`, `import_papers_jsonl`, and `get_paper` in `paper_store.py`. Store list fields as semicolon-separated text for display and raw JSON in `raw_json`.

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests/test_paper_store.py::test_init_creates_tables tests/test_paper_store.py::test_import_jsonl_upserts_papers_without_collections -v`

Expected: PASS.

## Task 2: TSV Collection Import And Memberships

**Files:**
- Modify: `tests/test_paper_store.py`
- Modify: `paper_store.py`

- [ ] **Step 1: Write failing tests for TSV import and collection membership**

```python
def test_import_tsv_creates_collection_and_memberships(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    tsv_path = tmp_path / "keep.tsv"
    tsv_path.write_text(
        "id\turl\ttitle\tabstract\n"
        "paper-1\thttps://openreview.net/forum?id=paper-1\tChart Reasoning\tA\n",
        encoding="utf-8",
    )
    store = PaperStore(db_path)
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart Reasoning"})

    result = store.import_collection_tsv(tsv_path)
    collections = store.list_collections()
    paper = store.get_paper("paper-1")

    assert result == {"collection": "keep", "papers": 1}
    assert collections[0]["name"] == "keep"
    assert collections[0]["paper_count"] == 1
    assert paper["collections"] == [{"id": collections[0]["id"], "name": "keep"}]


def test_import_tsv_creates_minimal_missing_paper(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    tsv_path = tmp_path / "new.tsv"
    tsv_path.write_text(
        "id\turl\ttitle\tabstract\n"
        "missing\thttps://openreview.net/forum?id=missing\tMissing Paper\tAbstract\n",
        encoding="utf-8",
    )
    store = PaperStore(db_path)
    store.init_db()

    store.import_collection_tsv(tsv_path)
    paper = store.get_paper("missing")

    assert paper["title"] == "Missing Paper"
    assert paper["abstract"] == "Abstract"
    assert paper["collections"][0]["name"] == "new"
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `python -m pytest tests/test_paper_store.py::test_import_tsv_creates_collection_and_memberships tests/test_paper_store.py::test_import_tsv_creates_minimal_missing_paper -v`

Expected: FAIL because `upsert_paper` and `import_collection_tsv` are not implemented.

- [ ] **Step 3: Implement TSV import and collection listing**

Implement `upsert_paper`, `create_collection`, `import_collection_tsv`, `list_collections`, and membership insertion. Use `id`, `openreview_id`, `forum`, or `url` columns to identify papers.

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests/test_paper_store.py -v`

Expected: PASS.

## Task 3: Collection CRUD, Search Filters, And Export

**Files:**
- Modify: `tests/test_paper_store.py`
- Modify: `paper_store.py`

- [ ] **Step 1: Write failing tests for collection management and filters**

```python
def test_collection_crud_does_not_delete_papers(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "A"})
    collection = store.create_collection("reading")
    store.add_paper_to_collection("paper-1", collection["id"])

    store.rename_collection(collection["id"], "priority")
    assert store.list_collections()[0]["name"] == "priority"

    store.delete_collection(collection["id"])
    assert store.get_paper("paper-1")["title"] == "A"
    assert store.get_paper("paper-1")["collections"] == []


def test_list_papers_search_and_collection_filters(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart QA", "abstract": "charts"})
    store.upsert_paper({"id": "paper-2", "title": "Optimization", "abstract": "math"})
    collection = store.create_collection("keep")
    store.add_paper_to_collection("paper-1", collection["id"])

    assert [p["id"] for p in store.list_papers(search="chart")] == ["paper-1"]
    assert [p["id"] for p in store.list_papers(collection_id=collection["id"])] == [
        "paper-1"
    ]
    assert [p["id"] for p in store.list_papers(uncollected=True)] == ["paper-2"]


def test_export_collection_tsv(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart QA", "abstract": "charts"})
    collection = store.create_collection("keep")
    store.add_paper_to_collection("paper-1", collection["id"])

    tsv = store.export_collection_tsv(collection["id"])

    assert tsv.splitlines()[0] == "id\turl\tvenue\tprimary_area\ttitle\tabstract"
    assert "paper-1" in tsv
    assert "Chart QA" in tsv
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `python -m pytest tests/test_paper_store.py -v`

Expected: FAIL because CRUD, filters, and export are incomplete.

- [ ] **Step 3: Implement CRUD, filtering, and export**

Add `rename_collection`, `delete_collection`, `add_paper_to_collection`, `remove_paper_from_collection`, `list_papers`, and `export_collection_tsv`. Keep collection deletion scoped to `collections` and `paper_collections`.

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests/test_paper_store.py -v`

Expected: PASS.

## Task 4: Flask API

**Files:**
- Create: `tests/test_api.py`
- Create: `app.py`
- Create: `requirements.txt`

- [ ] **Step 1: Write failing Flask API tests**

```python
from app import create_app


def test_api_imports_default_papers(tmp_path):
    data_dir = tmp_path
    jsonl = data_dir / "icml2026_accepted_papers.jsonl"
    jsonl.write_text(
        '{"openreview_id":"paper-1","title":"Chart QA","abstract":"charts"}\n',
        encoding="utf-8",
    )
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=data_dir)
    client = app.test_client()

    response = client.post("/api/import/papers")

    assert response.status_code == 200
    assert response.get_json()["imported"] == 1


def test_api_collection_membership_roundtrip(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    store = app.config["STORE"]
    store.upsert_paper({"id": "paper-1", "title": "Chart QA"})

    created = client.post("/api/collections", json={"name": "keep"}).get_json()
    add_response = client.post(
        f"/api/papers/paper-1/collections/{created['id']}"
    )
    paper = client.get("/api/papers/paper-1").get_json()

    assert add_response.status_code == 200
    assert paper["collections"] == [{"id": created["id"], "name": "keep"}]
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `python -m pytest tests/test_api.py -v`

Expected: FAIL because `app.py` does not exist.

- [ ] **Step 3: Implement API routes**

Implement `create_app(db_path="papers.sqlite", data_dir=".")`, initialize the store, and add the API routes from the design. Use JSON responses for errors with status codes 400 or 404.

- [ ] **Step 4: Run API tests**

Run: `python -m pytest tests/test_api.py -v`

Expected: PASS.

## Task 5: Frontend Interface

**Files:**
- Create: `static/index.html`
- Create: `static/styles.css`
- Create: `static/app.js`
- Modify: `app.py`

- [ ] **Step 1: Add Flask smoke test for serving the frontend**

```python
def test_serves_frontend(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"ICML 2026 Paper Collections" in response.data
```

- [ ] **Step 2: Run test and verify it fails**

Run: `python -m pytest tests/test_api.py::test_serves_frontend -v`

Expected: FAIL because the frontend file does not exist or is not served.

- [ ] **Step 3: Build the single-page UI**

Create a three-panel UI with collection controls, paper search/list, and detail membership controls. Implement API calls in `static/app.js` for imports, CRUD, filters, membership toggles, and TSV export links.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_api.py tests/test_paper_store.py -v`

Expected: PASS.

## Task 6: Documentation And Local Verification

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

Include exact commands:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

Document that `papers.sqlite` is the backup file and that collection export is available from the UI.

- [ ] **Step 2: Run full tests**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 3: Start local server**

Run: `python app.py`

Expected: Flask starts on `http://127.0.0.1:5000`.

- [ ] **Step 4: Browser smoke verification**

Open `http://127.0.0.1:5000`, import all papers, verify paper count appears, import an existing TSV as a collection, select a paper, modify membership, reload, and confirm the membership persists.

## Self-Review

- Spec coverage: the plan covers full import, TSV collections, CRUD, membership editing, search/filtering, export, local SQLite storage, tests, README, and local startup.
- Placeholder scan: no deferred implementation markers remain.
- Type consistency: `PaperStore`, `create_app`, `papers`, `collections`, and `paper_collections` names are consistent across tasks.

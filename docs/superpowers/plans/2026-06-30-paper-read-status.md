# Paper Read Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persisted Read/UnRead tag for every paper, visible and clickable in both the paper list and detail pane.

**Architecture:** Store read state as `papers.is_read` in SQLite with a default of `0`. Expose it through the existing `PaperStore` and Flask API patterns, then reuse a shared frontend tag renderer so list and detail controls call the same toggle function.

**Tech Stack:** Python, Flask, SQLite, vanilla JavaScript, CSS, pytest.

---

### Task 1: Store Read Status

**Files:**
- Modify: `tests/test_paper_store.py`
- Modify: `paperlib/store.py`

- [ ] **Step 1: Write failing store tests**

Add tests for default status, updates, upsert preservation, and migration:

```python
def test_papers_default_to_unread_and_can_be_marked_read(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart QA"})

    assert store.get_paper("paper-1")["is_read"] is False

    updated = store.update_paper_read_status("paper-1", True)
    listed = store.list_papers()

    assert updated["is_read"] is True
    assert store.get_paper("paper-1")["is_read"] is True
    assert listed[0]["is_read"] is True


def test_upsert_preserves_existing_paper_read_status(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "First"})
    store.update_paper_read_status("paper-1", True)

    store.upsert_paper({"id": "paper-1", "title": "Updated"})
    paper = store.get_paper("paper-1")

    assert paper["title"] == "Updated"
    assert paper["is_read"] is True


def test_init_migrates_existing_database_with_read_status_column(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            create table papers (
                id text primary key,
                title text not null default '',
                abstract text not null default '',
                authors text not null default '',
                venue text not null default '',
                primary_area text not null default '',
                url text not null default '',
                pdf text not null default '',
                keywords text not null default '',
                notes_markdown text not null default '',
                raw_json text not null default '',
                created_at text not null,
                updated_at text not null
            );
            """
        )

    store = PaperStore(db_path)
    store.init_db()

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("pragma table_info(papers)")}

    assert "is_read" in columns
```

- [ ] **Step 2: Run store tests and verify failure**

Run: `pytest tests/test_paper_store.py -v`

Expected: tests fail because `is_read` and `update_paper_read_status` do not exist yet.

- [ ] **Step 3: Implement store support**

Update `paperlib/store.py` to add the column in create/migration SQL, include it in list/get selects, normalize rows so `is_read` is a boolean, and add:

```python
def update_paper_read_status(self, paper_id, is_read):
    with self._connect() as conn:
        cursor = conn.execute(
            """
            update papers
            set is_read = ?, updated_at = ?
            where id = ?
            """,
            (1 if is_read else 0, _now(), paper_id),
        )
        if cursor.rowcount == 0:
            return None
    return self.get_paper(paper_id)
```

- [ ] **Step 4: Run store tests and verify pass**

Run: `pytest tests/test_paper_store.py -v`

Expected: all store tests pass.

### Task 2: API Read Status Endpoint

**Files:**
- Modify: `tests/test_api.py`
- Modify: `paperlib/web.py`

- [ ] **Step 1: Write failing API tests**

Add tests for successful update, invalid payload, and missing paper:

```python
def test_api_updates_paper_read_status(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    app.config["STORE"].upsert_paper({"id": "paper-1", "title": "Chart QA"})

    response = client.patch("/api/papers/paper-1/read", json={"is_read": True})
    paper = client.get("/api/papers/paper-1").get_json()
    listed = client.get("/api/papers").get_json()["papers"]

    assert response.status_code == 200
    assert response.get_json()["is_read"] is True
    assert paper["is_read"] is True
    assert listed[0]["is_read"] is True


def test_api_rejects_invalid_paper_read_status_payload(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    app.config["STORE"].upsert_paper({"id": "paper-1", "title": "Chart QA"})

    response = client.patch("/api/papers/paper-1/read", json={"is_read": "true"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "is_read boolean is required"


def test_api_returns_404_when_updating_missing_paper_read_status(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.patch("/api/papers/missing/read", json={"is_read": True})

    assert response.status_code == 404
    assert response.get_json()["error"] == "Paper not found"
```

- [ ] **Step 2: Run API tests and verify failure**

Run: `pytest tests/test_api.py -v`

Expected: read endpoint tests fail with 404.

- [ ] **Step 3: Implement API route**

Add `PATCH /api/papers/<path:paper_id>/read` in `paperlib/web.py`, require payload key `is_read` with a boolean value, call `store.update_paper_read_status`, and return the updated paper or `404`.

- [ ] **Step 4: Run API tests and verify pass**

Run: `pytest tests/test_api.py -v`

Expected: all API tests pass.

### Task 3: Frontend Read Tags

**Files:**
- Modify: `tests/test_frontend_static.py`
- Modify: `static/app.js`
- Modify: `static/styles.css`

- [ ] **Step 1: Write failing frontend static test**

Add a static test that checks for shared read-status helpers and endpoint usage:

```python
def test_read_status_ui_uses_shared_toggle_and_api_endpoint():
    app_js = Path("static/app.js").read_text(encoding="utf-8")
    styles_css = Path("static/styles.css").read_text(encoding="utf-8")

    assert "makeReadStatusTag" in app_js
    assert "toggleReadStatus" in app_js
    assert "/read" in app_js
    assert "read-tag" in styles_css
```

- [ ] **Step 2: Run frontend static tests and verify failure**

Run: `pytest tests/test_frontend_static.py -v`

Expected: test fails because helpers and styles do not exist.

- [ ] **Step 3: Implement frontend UI**

In `static/app.js`, add `makeReadStatusTag(paper)` and `toggleReadStatus(paper)` helpers. Render the tag in `renderPapers()` badges and in `renderDetail()` near the title/meta area. The helper stops event propagation before calling the API so list-card tag clicks do not trigger paper selection.

- [ ] **Step 4: Add styles**

In `static/styles.css`, add `.read-tag`, `.read-tag.read`, and `.read-tag.unread` styles that match the existing badge/button language and fit in both columns.

- [ ] **Step 5: Run frontend static tests and verify pass**

Run: `pytest tests/test_frontend_static.py -v`

Expected: all frontend static tests pass.

### Task 4: Full Verification

**Files:**
- None

- [ ] **Step 1: Run complete test suite**

Run: `pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Review diff**

Run: `git diff -- docs/superpowers/specs/2026-06-30-paper-read-status-design.md docs/superpowers/plans/2026-06-30-paper-read-status.md paperlib/store.py paperlib/web.py static/app.js static/styles.css tests/test_paper_store.py tests/test_api.py tests/test_frontend_static.py`

Expected: diff contains only read-status feature changes.

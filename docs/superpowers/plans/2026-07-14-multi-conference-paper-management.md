# Multi-Conference Paper Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ICLR support and manage ICLR plus ICML papers in one local library with conference/source filtering.

**Architecture:** Keep the existing Flask, SQLite, static JavaScript, and OpenReview crawler structure. Add conference metadata as a stable field on papers, expose configured conferences through the API, and add a frontend filter that composes with existing paper filters.

**Tech Stack:** Python 3, Flask, SQLite, pytest, vanilla HTML/CSS/JavaScript, OpenReview API/web metadata.

---

## File Structure

- Modify `paperlib/crawlers/conferences.py`: add conference display names and `iclr2026` configuration.
- Modify `paperlib/crawlers/openreview.py`: ensure normalized crawl output includes the source conference key.
- Modify `paperlib/store.py`: add `conference` storage, migration, list filtering, and metadata-preserving upserts.
- Modify `paperlib/imports.py`: add helpers for importing one or all available configured conference metadata files.
- Modify `paperlib/web.py`: add conference API, import selection, and paper filtering.
- Modify `static/index.html`: remove ICML-only title and add conference filter container.
- Modify `static/app.js`: load conferences, render conference filters, import all conferences, and show conference metadata.
- Modify `static/styles.css`: style conference filter controls using existing sidebar patterns.
- Modify tests in `tests/test_crawlers.py`, `tests/test_api.py`, `tests/test_paper_store.py`, and `tests/test_frontend_static.py`.
- Update `README.md`: document ICLR/ICML fetch and multi-conference import.

### Task 1: Conference Configuration

**Files:**
- Modify: `paperlib/crawlers/conferences.py`
- Test: `tests/test_crawlers.py`

- [ ] **Step 1: Write failing tests**

Add these tests to `tests/test_crawlers.py`:

```python
def test_get_conference_returns_iclr2026_config():
    config = get_conference("iclr2026")

    assert config.key == "iclr2026"
    assert config.name == "ICLR 2026"
    assert config.invitation == "ICLR.cc/2026/Conference/-/Submission"
    assert "ICLR 2026 Poster" in config.venues
    assert config.venueid == "ICLR.cc/2026/Conference"


def test_conference_configs_have_display_names():
    assert get_conference("icml2026").name == "ICML 2026"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_crawlers.py::test_get_conference_returns_iclr2026_config tests/test_crawlers.py::test_conference_configs_have_display_names -v
```

Expected: FAIL because `iclr2026` is unknown and `OpenReviewConference` has no `name`.

- [ ] **Step 3: Implement minimal configuration**

Update `paperlib/crawlers/conferences.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class OpenReviewConference:
    key: str
    name: str
    invitation: str
    venues: tuple[str, ...]
    venueid: str | None = None


CONFERENCES = {
    "iclr2026": OpenReviewConference(
        key="iclr2026",
        name="ICLR 2026",
        invitation="ICLR.cc/2026/Conference/-/Submission",
        venues=(
            "ICLR 2026 Poster",
            "ICLR 2026 Spotlight",
            "ICLR 2026 Oral",
        ),
        venueid="ICLR.cc/2026/Conference",
    ),
    "icml2026": OpenReviewConference(
        key="icml2026",
        name="ICML 2026",
        invitation="ICML.cc/2026/Conference/-/Submission",
        venues=(
            "ICML 2026 oral",
            "ICML 2026 spotlight",
            "ICML 2026 regular",
        ),
        venueid="ICML.cc/2026/Conference",
    ),
}
```

Keep the existing `get_conference()` implementation.

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
python -m pytest tests/test_crawlers.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add paperlib/crawlers/conferences.py tests/test_crawlers.py
git commit -m "feat: add ICLR conference config"
```

### Task 2: Store Conference Field

**Files:**
- Modify: `paperlib/store.py`
- Test: `tests/test_paper_store.py`

- [ ] **Step 1: Write failing tests**

Add these tests to `tests/test_paper_store.py`:

```python
def test_paper_store_records_conference(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()

    store.upsert_paper({
        "id": "paper-1",
        "title": "Chart QA",
        "conference": "iclr2026",
    })

    paper = store.get_paper("paper-1")

    assert paper["conference"] == "iclr2026"


def test_upsert_preserves_notes_and_read_status_when_conference_updates(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Old"})
    store.update_paper_notes("paper-1", "keep this")
    store.update_paper_read_status("paper-1", True)

    store.upsert_paper({
        "id": "paper-1",
        "title": "New",
        "conference": "icml2026",
    })

    paper = store.get_paper("paper-1")

    assert paper["title"] == "New"
    assert paper["conference"] == "icml2026"
    assert paper["notes_markdown"] == "keep this"
    assert paper["is_read"] is True


def test_list_papers_filters_by_conference(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "A", "conference": "iclr2026"})
    store.upsert_paper({"id": "paper-2", "title": "B", "conference": "icml2026"})

    papers = store.list_papers(conference="iclr2026")

    assert [paper["id"] for paper in papers] == ["paper-1"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_paper_store.py::test_paper_store_records_conference tests/test_paper_store.py::test_upsert_preserves_notes_and_read_status_when_conference_updates tests/test_paper_store.py::test_list_papers_filters_by_conference -v
```

Expected: FAIL because `conference` is not selected/stored and `list_papers()` does not accept `conference`.

- [ ] **Step 3: Implement storage support**

In `paperlib/store.py`:

- Add `conference text not null default ''` to the `papers` table.
- Add a migration branch:

```python
if "conference" not in paper_columns:
    conn.execute("alter table papers add column conference text not null default ''")
```

- Add `conference=None` to `list_papers()` parameters.
- Add a conference filter:

```python
conference = (conference or "").strip()
if conference:
    params.append(conference)
    where.append("p.conference = ?")
```

- Include `p.conference` in all paper selects.
- Include `"conference": row.get("conference", "") or ""` in `_upsert_paper()` values.
- Include `conference` in the insert column list, values list, and update clause:

```sql
conference = case
    when excluded.conference != '' then excluded.conference
    else papers.conference
end,
```

- Add `conference` to TSV export field lists only if the existing export tests are intentionally updated; otherwise keep export unchanged.

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
python -m pytest tests/test_paper_store.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add paperlib/store.py tests/test_paper_store.py
git commit -m "feat: store paper conference source"
```

### Task 3: Import Conference Metadata

**Files:**
- Modify: `paperlib/imports.py`
- Modify: `paperlib/web.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add these tests to `tests/test_api.py`:

```python
def test_api_imports_selected_conference_with_source_key(tmp_path):
    data_dir = tmp_path
    raw_dir = data_dir / "raw" / "iclr2026"
    raw_dir.mkdir(parents=True)
    (raw_dir / "accepted_papers.jsonl").write_text(
        '{"openreview_id":"paper-1","title":"ICLR Paper"}\n',
        encoding="utf-8",
    )
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=data_dir)
    client = app.test_client()

    response = client.post("/api/import/papers", json={"conference": "iclr2026"})
    paper = client.get("/api/papers/paper-1").get_json()

    assert response.status_code == 200
    assert response.get_json()["imported"] == 1
    assert response.get_json()["conferences"] == {"iclr2026": 1}
    assert paper["conference"] == "iclr2026"


def test_api_imports_all_available_conferences(tmp_path):
    data_dir = tmp_path
    for conference, title in (("iclr2026", "ICLR Paper"), ("icml2026", "ICML Paper")):
        raw_dir = data_dir / "raw" / conference
        raw_dir.mkdir(parents=True)
        (raw_dir / "accepted_papers.jsonl").write_text(
            f'{{"openreview_id":"{conference}-paper","title":"{title}"}}\n',
            encoding="utf-8",
        )
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=data_dir)
    client = app.test_client()

    response = client.post("/api/import/papers", json={"conference": "all"})

    assert response.status_code == 200
    assert response.get_json()["imported"] == 2
    assert response.get_json()["conferences"] == {
        "iclr2026": 1,
        "icml2026": 1,
    }


def test_api_rejects_unknown_import_conference(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.post("/api/import/papers", json={"conference": "missing"})

    assert response.status_code == 400
    assert "Unknown conference" in response.get_json()["error"]


def test_api_lists_papers_filtered_by_conference(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    store = app.config["STORE"]
    store.upsert_paper({"id": "paper-1", "title": "A", "conference": "iclr2026"})
    store.upsert_paper({"id": "paper-2", "title": "B", "conference": "icml2026"})

    response = client.get("/api/papers?conference=iclr2026")

    assert response.status_code == 200
    assert [paper["id"] for paper in response.get_json()["papers"]] == ["paper-1"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_api.py::test_api_imports_selected_conference_with_source_key tests/test_api.py::test_api_imports_all_available_conferences tests/test_api.py::test_api_rejects_unknown_import_conference tests/test_api.py::test_api_lists_papers_filtered_by_conference -v
```

Expected: FAIL because the API ignores conference selection and paper listing has no conference filter.

- [ ] **Step 3: Implement import selection**

In `paperlib/imports.py`, add:

```python
def has_paper_metadata(data_dir, conference_key):
    try:
        find_paper_metadata(data_dir, conference_key)
    except FileNotFoundError:
        return False
    return True
```

In `paperlib/web.py`:

- Import `CONFERENCES` and `get_conference`.
- Read JSON payload in `import_papers()`.
- Treat missing conference as `"all"`.
- For selected conference, call `get_conference()` and `find_paper_metadata()`, then import with source key.
- For all, iterate configured conferences, skip missing metadata, and return 404 only if none are available.
- Add `conference=request.args.get("conference", "")` when calling `store.list_papers()`.

Because `PaperStore.import_papers_jsonl()` and CSV import currently only accept a path, add optional `conference=""` parameters and pass that value into each row before `_upsert_paper()`.

Return shape:

```python
{"imported": total, "conferences": {"iclr2026": 5355, "icml2026": 1234}}
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
python -m pytest tests/test_api.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add paperlib/imports.py paperlib/web.py paperlib/store.py tests/test_api.py
git commit -m "feat: import and filter papers by conference"
```

### Task 4: Conferences API

**Files:**
- Modify: `paperlib/web.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing test**

Add this test to `tests/test_api.py`:

```python
def test_api_lists_conferences_with_metadata_presence(tmp_path):
    raw_dir = tmp_path / "raw" / "iclr2026"
    raw_dir.mkdir(parents=True)
    (raw_dir / "accepted_papers.jsonl").write_text("", encoding="utf-8")
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.get("/api/conferences")

    assert response.status_code == 200
    conferences = {item["key"]: item for item in response.get_json()["conferences"]}
    assert conferences["iclr2026"]["name"] == "ICLR 2026"
    assert conferences["iclr2026"]["metadata_available"] is True
    assert conferences["icml2026"]["metadata_available"] is False
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
python -m pytest tests/test_api.py::test_api_lists_conferences_with_metadata_presence -v
```

Expected: FAIL with 404 for `/api/conferences`.

- [ ] **Step 3: Implement endpoint**

Add to `paperlib/web.py`:

```python
@app.get("/api/conferences")
def list_conferences():
    conferences = []
    for key, config in sorted(CONFERENCES.items()):
        conferences.append({
            "key": key,
            "name": config.name,
            "metadata_available": has_paper_metadata(data_dir, key),
        })
    return jsonify({"conferences": conferences})
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
python -m pytest tests/test_api.py::test_api_lists_conferences_with_metadata_presence -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add paperlib/web.py tests/test_api.py
git commit -m "feat: expose configured conferences"
```

### Task 5: Frontend Conference Filter

**Files:**
- Modify: `static/index.html`
- Modify: `static/app.js`
- Modify: `static/styles.css`
- Test: `tests/test_frontend_static.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing static tests**

Add these tests to `tests/test_frontend_static.py`:

```python
def test_frontend_uses_generic_paper_library_title():
    index_html = Path("static/index.html").read_text(encoding="utf-8")

    assert "ICML 2026 Paper Collections" not in index_html
    assert "Paper Collections" in index_html


def test_frontend_contains_conference_filter_behavior():
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    app_js = Path("static/app.js").read_text(encoding="utf-8")

    assert "conferenceList" in index_html
    assert "loadConferences" in app_js
    assert "setConferenceFilter" in app_js
    assert "/api/conferences" in app_js
    assert "conference" in app_js
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_frontend_static.py::test_frontend_uses_generic_paper_library_title tests/test_frontend_static.py::test_frontend_contains_conference_filter_behavior -v
```

Expected: FAIL because the frontend is still ICML-only and has no conference filter behavior.

- [ ] **Step 3: Implement frontend structure**

In `static/index.html`:

- Change `<title>` and `<h1>` to `Paper Collections`.
- Add a sidebar section before collections:

```html
<section>
  <div class="section-title">Conferences</div>
  <div id="conferenceList" class="conference-list"></div>
</section>
```

In `static/app.js`:

- Add state:

```javascript
conferences: [],
activeConference: "",
```

- Add DOM binding:

```javascript
conferenceList: document.getElementById("conferenceList"),
```

- Add `loadConferences()` that calls `/api/conferences`.
- Call `await loadConferences()` in `refreshAll()`.
- Add `conference` param in `loadPapers()` when `state.activeConference` is set.
- Add `renderConferences()` and `setConferenceFilter(conferenceKey)` using the existing button/filter style.
- Render `All conferences` and each configured conference.
- Add conference metadata to paper cards and detail via `addMeta(meta, conferenceName(paper.conference))`.
- Add helper:

```javascript
function conferenceName(key) {
  const conference = state.conferences.find((item) => item.key === key);
  return conference ? conference.name : key;
}
```

- Update import button status handling to read `result.conferences`.

In `static/styles.css`, add `.conference-list` rules that match `.filter-list` spacing, or reuse existing filter button classes.

- [ ] **Step 4: Run static tests and API tests**

Run:

```powershell
python -m pytest tests/test_frontend_static.py tests/test_api.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add static/index.html static/app.js static/styles.css tests/test_frontend_static.py
git commit -m "feat: add conference filter UI"
```

### Task 6: Crawl ICLR Metadata

**Files:**
- Generated local data: `data/raw/iclr2026/accepted_papers.jsonl`
- Generated local data: `data/raw/iclr2026/accepted_papers.csv`
- Generated local data: `data/raw/iclr2026/summary.json`

- [ ] **Step 1: Run crawler**

Run:

```powershell
python tools/fetch_papers.py iclr2026
```

Expected: command writes `data/raw/iclr2026/summary.json`. If OpenReview API returns challenge verification, inspect accessible OpenReview web endpoints and update only the crawler fetch transport while preserving the same normalized output and tests.

- [ ] **Step 2: Inspect crawl summary**

Run:

```powershell
Get-Content -Raw data\raw\iclr2026\summary.json
```

Expected: `total_unique_papers` is nonzero, queried venue counts are for accepted venues, and missing required fields are reasonable.

- [ ] **Step 3: Count JSONL rows**

Run:

```powershell
(Get-Content data\raw\iclr2026\accepted_papers.jsonl | Measure-Object -Line).Lines
```

Expected: line count equals `summary.json` `total_unique_papers`.

### Task 7: Import, Verify, and Document

**Files:**
- Modify: `README.md`
- Runtime data: `data/papers.sqlite`

- [ ] **Step 1: Update README**

Update README paper fetching and import sections:

```markdown
Fetch conference metadata:

```powershell
python tools/fetch_papers.py iclr2026
python tools/fetch_papers.py icml2026
```

The web app imports all locally available configured conference metadata by
default. Use the conference filter in the sidebar to switch between ICLR, ICML,
or all papers.
```

- [ ] **Step 2: Run all tests**

Run:

```powershell
python -m pytest -v
```

Expected: PASS.

- [ ] **Step 3: Import crawled metadata into SQLite**

Run:

```powershell
$response = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/import/papers -ContentType 'application/json' -Body '{"conference":"all"}'
$response | ConvertTo-Json -Depth 5
```

If the Flask server is not running, start it first with:

```powershell
python app.py
```

Expected: response includes nonzero count for `iclr2026` and the existing ICML count if local ICML metadata exists.

- [ ] **Step 4: Start local server for manual use**

Run:

```powershell
python app.py
```

Expected: server listens on `http://127.0.0.1:5000`. If port 5000 is occupied, use an alternate port by launching through `paperlib.web.create_app()` in a small one-off command.

- [ ] **Step 5: Commit docs and final changes**

```powershell
git add README.md data/raw/iclr2026
git commit -m "docs: document multi-conference workflow"
```

## Final Verification

- [ ] Run `python -m pytest -v`.
- [ ] Confirm `data/raw/iclr2026/summary.json` exists and reports nonzero accepted papers.
- [ ] Confirm `/api/conferences` returns ICLR and ICML.
- [ ] Confirm `/api/papers?conference=iclr2026&limit=1` returns ICLR-sourced papers after import.
- [ ] Open `http://127.0.0.1:5000` and confirm the title is generic and the conference filter is visible.

# Paper Markdown Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one persistent markdown note per paper with source editing and rendered preview in the paper detail pane.

**Architecture:** Store notes as `papers.notes_markdown` in SQLite and expose them through `PaperStore` plus a focused Flask PATCH endpoint. The browser detail pane edits markdown source, sends saves to the API, and renders a sanitized local preview without introducing a build step.

**Tech Stack:** Python 3, Flask, SQLite, pytest, vanilla JavaScript, HTML, CSS.

---

## File Structure

- Modify `paperlib/store.py`: schema migration, note persistence methods, selected paper fields.
- Modify `paperlib/web.py`: notes PATCH route.
- Modify `tests/test_paper_store.py`: storage, preservation, migration tests.
- Modify `tests/test_api.py`: notes API tests.
- Modify `static/app.js`: notes editor, save workflow, markdown preview renderer.
- Modify `static/styles.css`: notes editor and preview layout.
- Modify `README.md`: mention notes in backup description.

### Task 1: Store Notes

**Files:**
- Modify: `tests/test_paper_store.py`
- Modify: `paperlib/store.py`

- [ ] **Step 1: Write failing storage tests**

Add these tests to `tests/test_paper_store.py`:

```python
def test_updates_and_reads_paper_notes(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart QA"})

    updated = store.update_paper_notes("paper-1", "# Notes\n\n- read")
    paper = store.get_paper("paper-1")

    assert updated["notes_markdown"] == "# Notes\n\n- read"
    assert paper["notes_markdown"] == "# Notes\n\n- read"


def test_upsert_preserves_existing_paper_notes(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "First"})
    store.update_paper_notes("paper-1", "keep this")

    store.upsert_paper({"id": "paper-1", "title": "Updated"})
    paper = store.get_paper("paper-1")

    assert paper["title"] == "Updated"
    assert paper["notes_markdown"] == "keep this"


def test_init_migrates_existing_database_with_notes_column(tmp_path):
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
                raw_json text not null default '',
                created_at text not null,
                updated_at text not null
            );
            """
        )

    store = PaperStore(db_path)
    store.init_db()

    with sqlite3.connect(db_path) as conn:
        columns = {
            row[1]
            for row in conn.execute("pragma table_info(papers)")
        }

    assert "notes_markdown" in columns
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_paper_store.py -v
```

Expected: failures for missing `notes_markdown` selection and missing `update_paper_notes`.

- [ ] **Step 3: Implement storage support**

In `paperlib/store.py`:

- Add `notes_markdown text not null default ''` to the `create table if not exists papers` statement.
- After the schema creation script in `init_db()`, call a helper that checks `pragma table_info(papers)` and runs:

```sql
alter table papers add column notes_markdown text not null default ''
```

when missing.

- Add `notes_markdown` to `list_papers()` and `get_paper()` select lists.
- Add:

```python
    def update_paper_notes(self, paper_id, notes_markdown):
        with self._connect() as conn:
            now = _now()
            cursor = conn.execute(
                """
                update papers
                set notes_markdown = ?, updated_at = ?
                where id = ?
                """,
                (str(notes_markdown or ""), now, paper_id),
            )
            if cursor.rowcount == 0:
                return None
            return self.get_paper(paper_id)
```

- Do not include `notes_markdown` in `_upsert_paper()` values or conflict update fields.

- [ ] **Step 4: Run storage tests**

Run:

```powershell
python -m pytest tests/test_paper_store.py -v
```

Expected: all tests pass.

### Task 2: Notes API

**Files:**
- Modify: `tests/test_api.py`
- Modify: `paperlib/web.py`

- [ ] **Step 1: Write failing API tests**

Add these tests to `tests/test_api.py`:

```python
def test_api_updates_paper_notes(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    app.config["STORE"].upsert_paper({"id": "paper-1", "title": "Chart QA"})

    response = client.patch(
        "/api/papers/paper-1/notes",
        json={"notes_markdown": "# Notes\n\nImportant."},
    )
    paper = client.get("/api/papers/paper-1").get_json()

    assert response.status_code == 200
    assert response.get_json()["notes_markdown"] == "# Notes\n\nImportant."
    assert paper["notes_markdown"] == "# Notes\n\nImportant."


def test_api_returns_404_when_updating_missing_paper_notes(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.patch(
        "/api/papers/missing/notes",
        json={"notes_markdown": "note"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Paper not found"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_api.py -v
```

Expected: `PATCH /api/papers/<id>/notes` returns 404 because the route is missing.

- [ ] **Step 3: Implement API route**

Add this route near `get_paper()` in `paperlib/web.py`:

```python
    @app.patch("/api/papers/<path:paper_id>/notes")
    def update_paper_notes(paper_id):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or "notes_markdown" not in payload:
            return jsonify({"error": "notes_markdown is required"}), 400
        paper = store.update_paper_notes(paper_id, payload["notes_markdown"])
        if paper is None:
            return jsonify({"error": "Paper not found"}), 404
        return jsonify(paper)
```

- [ ] **Step 4: Run API tests**

Run:

```powershell
python -m pytest tests/test_api.py -v
```

Expected: all tests pass.

### Task 3: Frontend Notes Editor And Preview

**Files:**
- Modify: `static/app.js`
- Modify: `static/styles.css`

- [ ] **Step 1: Add notes UI in `renderDetail()`**

In `static/app.js`, after the collections block construction, create:

```javascript
  const notesTitle = document.createElement("div");
  notesTitle.className = "section-title";
  notesTitle.textContent = "Notes";

  const notesWrap = document.createElement("div");
  notesWrap.className = "notes-panel";

  const notesTextarea = document.createElement("textarea");
  notesTextarea.className = "notes-editor";
  notesTextarea.value = paper.notes_markdown || "";
  notesTextarea.placeholder = "Write markdown notes for this paper";
  notesTextarea.setAttribute("aria-label", "Paper markdown notes");

  const notesActions = document.createElement("div");
  notesActions.className = "notes-actions";
  const saveNotesButton = document.createElement("button");
  saveNotesButton.type = "button";
  saveNotesButton.textContent = "Save notes";
  notesActions.append(saveNotesButton);

  const previewTitle = document.createElement("div");
  previewTitle.className = "notes-preview-title";
  previewTitle.textContent = "Preview";
  const notesPreview = document.createElement("div");
  notesPreview.className = "notes-preview";

  const updatePreview = () => {
    notesPreview.innerHTML = renderMarkdown(notesTextarea.value);
  };
  notesTextarea.addEventListener("input", updatePreview);
  saveNotesButton.addEventListener("click", async () => {
    await saveNotes(paper.id, notesTextarea.value);
  });
  updatePreview();

  notesWrap.append(notesTextarea, notesActions, previewTitle, notesPreview);
```

Append `notesTitle` and `notesWrap` to `dom.paperDetail`.

- [ ] **Step 2: Add save function**

Add this function in `static/app.js` near `setMembership()`:

```javascript
async function saveNotes(paperId, notesMarkdown) {
  const paper = await apiJson(`/api/papers/${encodeURIComponent(paperId)}/notes`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes_markdown: notesMarkdown }),
  });
  state.selectedPaperId = paper.id;
  renderDetail(paper);
  setStatus("Notes saved");
}
```

- [ ] **Step 3: Add markdown renderer helpers**

Add `renderMarkdown`, `renderInlineMarkdown`, and `escapeHtml` helpers in
`static/app.js`. They should escape HTML first, support fenced code blocks,
headings, blockquotes, lists, paragraphs, links, bold, italic, inline code, and
line breaks.

- [ ] **Step 4: Style notes controls**

Add CSS to `static/styles.css`:

```css
textarea.notes-editor {
  border: 1px solid var(--line);
  border-radius: 6px;
  min-height: 150px;
  padding: 10px;
  resize: vertical;
  width: 100%;
}

.notes-panel {
  display: grid;
  gap: 10px;
}

.notes-actions {
  display: flex;
  justify-content: flex-end;
}

.notes-preview-title {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}

.notes-preview {
  border: 1px solid var(--line);
  border-radius: 6px;
  min-height: 90px;
  padding: 10px;
}

.notes-preview :first-child {
  margin-top: 0;
}

.notes-preview :last-child {
  margin-bottom: 0;
}

.notes-preview code,
.notes-preview pre {
  background: #eef1f2;
  border-radius: 4px;
}

.notes-preview code {
  padding: 1px 4px;
}

.notes-preview pre {
  overflow: auto;
  padding: 8px;
}
```

- [ ] **Step 5: Run all tests**

Run:

```powershell
python -m pytest -v
```

Expected: all tests pass.

### Task 4: Documentation And Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README backup section**

Change the backup sentence to mention that `data/papers.sqlite` includes paper
notes.

- [ ] **Step 2: Run full verification**

Run:

```powershell
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Check git diff**

Run:

```powershell
git diff -- paperlib/store.py paperlib/web.py tests/test_paper_store.py tests/test_api.py static/app.js static/styles.css README.md
```

Expected: diff only contains markdown notes feature changes.


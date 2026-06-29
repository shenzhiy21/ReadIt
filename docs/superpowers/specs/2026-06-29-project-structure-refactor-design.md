# Project Structure Refactor Design

## Goal

Refactor the paper-reading project so source code, crawlers, local data, and
tests have clear ownership. All paper metadata and collection TSV files are
local-only data and must not be tracked by git. The crawler architecture should
support future conferences without adding one-off scripts in the repository
root.

## Chosen Approach

Use a lightweight package structure while keeping the current Flask app simple.

The root keeps only project entry points and top-level documentation:

```text
papers/
  app.py
  requirements.txt
  README.md
  .gitignore
  paperlib/
  tools/
  static/
  tests/
  docs/
  data/
```

This is less disruptive than a full `src/` layout and still creates durable
boundaries for web code, data storage, imports, and crawlers.

## Target Layout

```text
paperlib/
  __init__.py
  config.py
  imports.py
  store.py
  web.py
  crawlers/
    __init__.py
    conferences.py
    openreview.py

tools/
  fetch_papers.py

data/
  raw/
    icml2026/
      accepted_papers.jsonl
      accepted_papers.csv
      summary.json
  collections/
    icml2026_chartqa_mllm_firstpass_keep.tsv
    icml2026_chartqa_mllm_screened_candidates.tsv
  papers.sqlite
```

## Data Policy

- `data/` is ignored by git.
- Existing root-level CSV, JSONL, JSON, and TSV files move into `data/`.
- The SQLite database moves from `papers.sqlite` to `data/papers.sqlite`.
- Tests must create temporary data directories and must not depend on local
  `data/` contents.
- The app remains usable when `data/` does not exist; startup creates required
  directories.

## Web App Changes

`app.py` becomes a thin entry point:

- Imports `create_app` from `paperlib.web`.
- Starts the local Flask server on `127.0.0.1:5000`.

`paperlib.web` owns:

- Flask app factory.
- API routes.
- Static file serving.
- Default data directory resolution.

`paperlib.store` owns:

- SQLite schema.
- Paper import from JSONL/CSV.
- TSV collection import.
- Collection CRUD.
- Paper search/filtering.
- TSV export.

`paperlib.config` owns default paths:

- `DATA_DIR = data`
- `DB_PATH = data/papers.sqlite`
- Current default conference key: `icml2026`

`paperlib.imports` owns metadata path lookup:

- For `icml2026`, prefer `data/raw/icml2026/accepted_papers.jsonl`.
- Fallback to `data/raw/icml2026/accepted_papers.csv`.
- Return clear errors when neither exists.

## Crawler Architecture

`paperlib.crawlers.openreview` provides reusable OpenReview crawling:

- Fetch paginated OpenReview notes.
- Normalize note content into the existing paper metadata schema.
- Write JSONL, CSV, and summary files.
- Cross-check venue ID when configured.

`paperlib.crawlers.conferences` defines conference configurations:

- `key`, such as `icml2026`.
- OpenReview invitation.
- Accepted venue labels.
- Venue ID for cross-checking.
- Output directory under `data/raw/<key>/`.

`tools/fetch_papers.py` is the CLI:

```powershell
python tools/fetch_papers.py icml2026
```

Adding another OpenReview conference should require a new configuration entry,
not a new root-level script.

## Migration Behavior

The refactor moves existing local files:

- `icml2026_accepted_papers.jsonl` to
  `data/raw/icml2026/accepted_papers.jsonl`
- `icml2026_accepted_papers.csv` to
  `data/raw/icml2026/accepted_papers.csv`
- `icml2026_accepted_papers_summary.json` to
  `data/raw/icml2026/summary.json`
- `icml2026_chartqa_mllm_firstpass_keep.tsv` to
  `data/collections/icml2026_chartqa_mllm_firstpass_keep.tsv`
- `icml2026_chartqa_mllm_screened_candidates.tsv` to
  `data/collections/icml2026_chartqa_mllm_screened_candidates.tsv`
- `papers.sqlite` to `data/papers.sqlite`

If a destination file already exists, the implementation should avoid
overwriting it silently.

## Git Ignore Policy

`.gitignore` should ignore:

- `data/`
- SQLite files anywhere.
- Logs.
- Python caches.
- Virtual environments.
- Editor and OS noise.

The tracked repository should contain code, tests, docs, and static assets only.

## Testing

Keep existing behavior covered:

- Store tests pass after import path changes.
- API tests pass with temporary data directories.
- Frontend smoke route still serves the page.
- TSV import still supports uploaded files.
- Full paper import now resolves through the configured conference data path.

Add crawler tests that do not hit the network:

- Conference config lookup.
- OpenReview note normalization.
- Output path naming.

## Non-Goals

- No UI redesign.
- No multi-user support.
- No cloud data sync.
- No crawler support for non-OpenReview sources in this refactor.
- No migration of user collections out of SQLite beyond moving the database
  file into `data/`.

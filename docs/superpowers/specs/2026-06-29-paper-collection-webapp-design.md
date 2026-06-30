# ICML 2026 Paper Collection Web App Design

## Goal

Build a local, single-user interactive web app for reading and organizing ICML
2026 papers. The app imports the full ICML 2026 paper metadata and treats each
TSV file as a collection. A paper may belong to zero, one, or many collections.
All records are stored locally in SQLite.

## Scope

In scope:

- Import all ICML 2026 papers from the existing local metadata files.
- Import TSV files as collections.
- Create, rename, and delete collections.
- View all collections a paper belongs to.
- Add or remove a paper from collections.
- Search and filter papers for literature review.
- Export collection contents back to TSV.

Out of scope for the first version:

- Multi-user accounts or authentication.
- Cloud sync.
- PDF annotation.
- Automatic paper recommendation or LLM ranking.
- Concurrent editing from multiple browsers.

## Recommended Architecture

Use a small local Flask application with SQLite.

- Backend: Python Flask serving JSON API endpoints and static frontend files.
- Database: `papers.sqlite` in the workspace directory.
- Frontend: a single-page HTML/CSS/JavaScript interface.
- Startup: run a local command and open `http://127.0.0.1:5000`.

This matches the current workspace, which already contains Python scripts and
local ICML 2026 metadata files.

## Data Model

`papers`

- `id`: OpenReview/forum ID when available, primary identifier.
- `title`
- `abstract`
- `authors`
- `venue`
- `primary_area`
- `url`
- `pdf`
- `keywords`
- `raw_json`
- `created_at`
- `updated_at`

`collections`

- `id`
- `name`
- `source_file`
- `created_at`
- `updated_at`

`paper_collections`

- `paper_id`
- `collection_id`
- `created_at`

This many-to-many table is the source of truth for collection membership.
Deleting a collection deletes only collection membership rows, not papers.

## Import Behavior

Full paper import:

- Prefer `icml2026_accepted_papers.jsonl` when present.
- Fall back to `icml2026_accepted_papers.csv` if needed.
- Upsert papers by OpenReview/forum ID.
- Preserve all existing collections and memberships.

TSV collection import:

- Treat each TSV file as one collection.
- Default collection name is the TSV filename without extension.
- If a collection with the same name exists, update its membership from the
  imported TSV after confirmation in the UI.
- Match papers by `id` first, then by OpenReview URL/forum ID if available.
- If a TSV row references a paper not present in the full paper table, create a
  minimal paper record from available row fields.

## User Interface

Layout:

- Left sidebar: collections, counts, create/rename/delete/import controls.
- Main panel: searchable paper list.
- Detail panel: selected paper metadata, abstract, links, and collection
  membership controls.

Paper list features:

- Search title, abstract, authors, venue, area, and collection name.
- Filter by collection.
- Filter to uncollected papers.
- Filter to papers in multiple collections.
- Show collection badges for each paper.

Collection workflows:

- Create a collection by name.
- Rename a collection.
- Delete a collection without deleting papers.
- Import a TSV as a collection.
- Export one collection or all collections as TSV files.

Paper workflows:

- Select a paper to read its abstract and metadata.
- Add the paper to one or more collections.
- Remove the paper from one or more collections.
- Open OpenReview/PDF links in a new browser tab.

## API Surface

Core endpoints:

- `GET /api/papers`
- `GET /api/papers/<paper_id>`
- `POST /api/import/papers`
- `POST /api/import/collection`
- `GET /api/collections`
- `POST /api/collections`
- `PATCH /api/collections/<collection_id>`
- `DELETE /api/collections/<collection_id>`
- `POST /api/papers/<paper_id>/collections/<collection_id>`
- `DELETE /api/papers/<paper_id>/collections/<collection_id>`
- `GET /api/export/collections`
- `GET /api/export/collections/<collection_id>`

## Error Handling

- Invalid import files return a clear API error and do not partially overwrite
  collection state.
- Duplicate collection names are rejected unless the import flow explicitly
  chooses update behavior.
- Deleting a missing collection or membership is idempotent where practical.
- Database schema is initialized automatically at app startup.
- Import operations run in transactions.

## Testing

Backend tests cover:

- Database initialization.
- Full paper import and upsert.
- TSV import as collection.
- Matching TSV rows by paper ID and URL.
- Creating minimal paper records from TSV-only rows.
- Collection create, rename, delete.
- Collection deletion does not delete papers.
- Adding and removing paper memberships.
- Search and collection filters.
- Export format.

Frontend verification covers:

- App loads locally.
- Collections appear with counts.
- Selecting a paper shows metadata and membership controls.
- Membership changes persist after reload.
- Import/export controls reach the backend successfully.

## Delivery

Deliver:

- Flask app files in the workspace.
- SQLite database created on first run.
- A short README with startup and backup instructions.
- Local server started after implementation, with the URL reported to the user.

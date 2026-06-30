# Paper Read Status Design

Date: 2026-06-30

## Goal

Users can mark each paper as `Read` or `UnRead`. New and imported papers default
to `UnRead`. The status is stored in SQLite and remains available after refreshes
and service restarts.

## Storage

- Add `is_read integer not null default 0` to the `papers` table.
- `PaperStore.init_db()` migrates existing SQLite databases by adding the column
  when it is missing.
- Paper metadata imports and upserts do not overwrite an existing read status.
- `get_paper()` and `list_papers()` return `is_read` as a Python boolean.

## API

- Add `PATCH /api/papers/<paper_id>/read`.
- Request body: `{ "is_read": true }` or `{ "is_read": false }`.
- Response body: the updated paper object.
- Missing papers return `404`.
- Invalid payload shape returns `400`.

## Frontend

- Render a clickable `Read` or `UnRead` tag in each paper card in the middle
  column.
- Render the same clickable tag in the selected paper detail pane in the right
  column.
- Clicking either tag toggles the status through the API, updates the selected
  paper detail if it is open, updates the matching item in `state.papers`, and
  redraws the paper list.
- Clicking the middle-column tag does not also select or reopen the paper card.

## Tests

- Store tests cover default `UnRead`, updating and reading status, preserving
  status across metadata upserts, and migration of existing databases.
- API tests cover read-status roundtrip, invalid payloads, and missing papers.
- Frontend static tests cover the existence of the shared read-status rendering
  and toggle code.

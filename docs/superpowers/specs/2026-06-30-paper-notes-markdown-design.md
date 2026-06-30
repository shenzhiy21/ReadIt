# Paper Markdown Notes Design

Date: 2026-06-30

## Goal

Users can write one markdown note for each paper in the local paper library. The
app saves the markdown source and shows both an editor and a rendered preview in
the paper detail pane.

## Storage

- Add `notes_markdown text not null default ''` to the `papers` table.
- `PaperStore.init_db()` migrates existing SQLite databases by adding the column
  when it is missing.
- Paper metadata imports and upserts do not overwrite existing notes.
- `get_paper()` returns `notes_markdown`.
- `list_papers()` returns `notes_markdown` so the list can show note state if
  needed.

## API

- Add `PATCH /api/papers/<paper_id>/notes`.
- Request body: `{ "notes_markdown": "markdown source" }`.
- Response body: the updated paper object.
- Missing papers return `404`.
- Invalid payload shape returns `400`.

## Frontend

- Add a Notes section to the paper detail pane.
- The section contains a textarea for markdown source, a Save button, and a
  preview area.
- Preview updates locally while editing.
- Markdown rendering supports common local-note syntax: headings, paragraphs,
  bold, italic, inline code, fenced code blocks, links, unordered lists, ordered
  lists, blockquotes, and line breaks.
- Raw HTML from notes is escaped before rendering.
- Saving updates the status line with `Notes saved`.
- A failed save keeps the current textarea content visible and reports the error
  in the status line.

## Tests

- Store tests cover saving and reading notes.
- Store tests cover metadata import/upsert preserving existing notes.
- Store tests cover migration of an existing database without the notes column.
- API tests cover notes roundtrip and not-found behavior.


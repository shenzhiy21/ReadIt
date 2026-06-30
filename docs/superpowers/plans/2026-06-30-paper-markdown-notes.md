# Paper Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one persistent plain-text note per paper without realtime markdown preview.

**Architecture:** Store note text in the existing-compatible `papers.notes_markdown` SQLite column and expose it through `PaperStore` plus a focused Flask PATCH endpoint. The browser detail pane edits and saves plain text only; it does not parse notes during typing.

**Tech Stack:** Python 3, Flask, SQLite, pytest, vanilla JavaScript, HTML, CSS.

---

## File Structure

- Modify `paperlib/store.py`: schema migration, note persistence methods, selected paper fields.
- Modify `paperlib/web.py`: notes PATCH route.
- Modify `tests/test_paper_store.py`: storage, preservation, migration tests.
- Modify `tests/test_api.py`: notes API tests.
- Modify `tests/test_frontend_static.py`: regression test that forbids preview renderer code.
- Modify `static/app.js`: plain-text notes editor and save workflow.
- Modify `static/styles.css`: notes editor layout.
- Modify `README.md`: mention notes in backup description.

## Completed Tasks

- [x] Add failing store tests for note save/read, import preservation, and old database migration.
- [x] Implement `notes_markdown` migration and `PaperStore.update_paper_notes()`.
- [x] Add failing API tests for note roundtrip and missing paper behavior.
- [x] Implement `PATCH /api/papers/<paper_id>/notes`.
- [x] Add failing frontend static regression test requiring no markdown preview renderer.
- [x] Remove realtime preview DOM, input listener, markdown renderer helpers, and preview CSS.
- [x] Keep a plain textarea and Save notes button in the paper detail pane.
- [x] Update documentation to describe plain-text notes.

## Verification

- Run `python -m pytest -v`.
- Run `node --check static\app.js`.
- Run `git diff --check`.

# Paper Collections

Local single-user web app for reading and organizing conference papers. Source
code is tracked by git; paper metadata, collection TSV files, and the SQLite
database live under `data/` and are local-only.

## Project Layout

```text
paperlib/              Python package for the app, storage, imports, crawlers
paperlib/crawlers/     Reusable OpenReview crawler code
tools/fetch_papers.py  CLI for fetching conference metadata
static/                Browser UI
tests/                 Automated tests
data/                  Local paper data, ignored by git
```

Local data layout:

```text
data/
  raw/<conference>/
    accepted_papers.jsonl
    accepted_papers.csv
    summary.json
  collections/
    *.tsv
  papers.sqlite
```

## Start

Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) first if
it is not already available. Then create the project environment and install
the locked dependencies:

```powershell
uv sync
uv run python app.py
```

Open:

```text
http://127.0.0.1:5000
```

`uv sync` creates `.venv` automatically. Later `uv run` commands keep the
environment synchronized with `pyproject.toml` and `uv.lock`.

## Fetch Paper Metadata

Fetch configured conference metadata:

```powershell
uv run python tools/fetch_papers.py iclr2026
uv run python tools/fetch_papers.py icml2026
uv run python tools/fetch_papers.py tvcg2025
uv run python tools/fetch_papers.py tvcg2023 tvcg2024 tvcg2025 tvcg2026
```

Each command writes:

```text
data/raw/<conference>/accepted_papers.jsonl
data/raw/<conference>/accepted_papers.csv
data/raw/<conference>/summary.json
```

The ICLR 2026 fetch first tries OpenReview's API. If that API requires challenge
verification, it falls back to a public OpenReview-derived JSONL snapshot and
filters to main-conference accepted papers only.

The TVCG 2023-2026 fetches use DBLP only. Each fetch parses the corresponding
DBLP volume XML export and checks the result count against the DBLP HTML volume
page before writing any files. A mismatch fails the fetch instead of producing
a possibly incomplete dataset. Completed years require Issues 1-12; the active
2026 volume requires continuous issues through DBLP's latest indexed issue.
DBLP's four-digit homonym-disambiguation suffixes are removed from displayed
author names, while the stable DBLP identifiers remain in `author_pids`.

To add another source, add a configuration entry in
`paperlib/crawlers/publications.py`.

## Import In The Web App

- Click `Import all papers` to load all locally available configured conference
  metadata, such as `data/raw/iclr2026/accepted_papers.jsonl` and
  `data/raw/icml2026/accepted_papers.jsonl`.
- If a conference JSONL file is missing, the app falls back to that conference's
  `accepted_papers.csv`.
- Use the conference filter in the sidebar to switch between all papers, ICLR
  2026, and ICML 2026.
- Click `Import TSV` to import any `.tsv` file as a collection.
- The TSV filename becomes the collection name.
- Importing the same TSV filename again refreshes that collection membership.

## Backup

Back up this file:

```text
data/papers.sqlite
```

It contains the paper library, collections, and paper-to-collection membership.
It also contains per-paper notes.

## Export

- Use `Export` beside a collection to download that collection as TSV.
- Use `Export all` to download all collection memberships as one TSV.

Deleting a collection does not delete papers from the library.

## Tests

```powershell
uv run python -m pytest -v
```

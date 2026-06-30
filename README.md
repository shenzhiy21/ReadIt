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

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

Open:

```text
http://127.0.0.1:5000
```

If the current Python already has Flask and pytest installed, this also works:

```powershell
python app.py
```

## Fetch Paper Metadata

Fetch ICML 2026 papers from OpenReview:

```powershell
python tools/fetch_papers.py icml2026
```

This writes:

```text
data/raw/icml2026/accepted_papers.jsonl
data/raw/icml2026/accepted_papers.csv
data/raw/icml2026/summary.json
```

To add another OpenReview conference, add a configuration entry in
`paperlib/crawlers/conferences.py`.

## Import In The Web App

- Click `Import all papers` to load the default conference metadata from
  `data/raw/icml2026/accepted_papers.jsonl`.
- If the JSONL file is missing, the app falls back to
  `data/raw/icml2026/accepted_papers.csv`.
- Click `Import TSV` to import any `.tsv` file as a collection.
- The TSV filename becomes the collection name.
- Importing the same TSV filename again refreshes that collection membership.

## Backup

Back up this file:

```text
data/papers.sqlite
```

It contains the paper library, collections, and paper-to-collection membership.

## Export

- Use `Export` beside a collection to download that collection as TSV.
- Use `Export all` to download all collection memberships as one TSV.

Deleting a collection does not delete papers from the library.

## Tests

```powershell
python -m pytest -v
```

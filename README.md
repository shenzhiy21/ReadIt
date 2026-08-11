# Paper Collections

A local-first web app for collecting, reading, and organizing academic papers.
Paper metadata and personal notes stay on your machine.

## Features

- Browse and filter papers by publication
- Track reading status and add notes
- Organize papers into collections
- Import and export collections as TSV files
- Fetch metadata from OpenReview and DBLP

## Quick Start

Requirements: Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python app.py
```

Open <http://127.0.0.1:5000> in your browser.

## Importing Data

Fetch metadata for one or more supported publications:

```bash
uv run python tools/fetch_papers.py iclr2026 icml2026
```

Available publication keys are `iclr2026`, `icml2026`, and `tvcg2023` through
`tvcg2026`. Fetched files are saved under `data/raw/`. Use **Import all papers**
in the web app to add them to the library, or use **Import TSV** to create a
collection from an existing TSV file.

All application data is stored locally under `data/`, which is excluded from
Git. Back up `data/papers.sqlite` to preserve your library, collections, notes,
and reading status.

## Development

Run the test suite with:

```bash
uv run python -m pytest -v
```

Contributions are welcome. Please include tests for behavior changes and ensure
the test suite passes before submitting a pull request.

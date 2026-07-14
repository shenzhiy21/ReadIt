# Multi-Conference Paper Management Design

## Goal

Support crawling and managing the latest ICLR papers alongside existing ICML
papers in one local paper library. The app should no longer present itself as
ICML-only. Users can import conference metadata, search across conferences, and
filter by conference/source while keeping collections, notes, and read status in
one shared SQLite database.

## Scope

In scope:

- Add an ICLR OpenReview conference configuration for the latest ICLR conference.
- Crawl all accepted ICLR papers into `data/raw/<conference>/`.
- Preserve the existing ICML 2026 crawl and import path.
- Track each imported paper's source conference with a stable conference key.
- Import one selected conference or all locally crawled conferences.
- Filter the paper list by conference in the API and frontend.
- Replace ICML-specific frontend copy with generic paper library copy.

Out of scope:

- Splitting the library into per-conference databases.
- Multi-user accounts, sync, or authentication.
- Ranking, recommendation, or LLM screening.
- Fetching PDFs or full text beyond metadata links.

## Architecture

The existing Flask, SQLite, and static JavaScript architecture remains in place.
The change adds conference awareness at the metadata boundary and exposes it to
the UI as a first-class filter.

Key pieces:

- `paperlib.crawlers.conferences` defines `icml2026` and `iclr2026`.
- `tools/fetch_papers.py <conference>` still writes normalized metadata to
  `data/raw/<conference>/accepted_papers.jsonl`, CSV, and summary files.
- `papers` gains a `conference` text column with migration support.
- Import APIs write the selected conference key into every imported paper.
- List APIs accept a `conference` query parameter.
- The frontend renders conference filter controls and sends that parameter when
  loading papers.

## Data Model

Add `papers.conference text not null default ''`.

The value is the stable configuration key, such as `iclr2026` or `icml2026`.
This is separate from `venue`, because OpenReview venue labels are display text
and may vary by track or decision type.

Existing rows without a conference remain valid. When ICML metadata is reimported
from `data/raw/icml2026`, those rows receive `conference = "icml2026"`.

## Crawl Behavior

The crawler should fetch accepted ICLR papers only. It must not import all
submitted or withdrawn ICLR submissions. The preferred query is by OpenReview
conference invitation plus accepted venue or venue id, matching the existing
ICML pattern.

Because OpenReview can require challenge verification on direct API calls, the
implementation should keep crawling logic isolated and testable:

- Conference configuration defines the target invitation, accepted venue labels,
  and optional venue id.
- Tests validate configuration and normalization without network access.
- The actual crawl command is run separately and its summary is inspected before
  importing into SQLite.
- If the API endpoint is blocked, use an accessible OpenReview source that still
  yields accepted papers only.

## Import Behavior

`POST /api/import/papers` accepts an optional `conference` value:

- Missing or `all`: import all locally available configured conferences.
- A known conference key: import only that conference.
- Unknown conference key: return a clear 400 error.

The response includes total imported papers and per-conference counts. Importing
is idempotent and preserves collections, notes, and read status for existing
paper IDs.

## API Behavior

Add:

- `GET /api/conferences`: returns configured conference keys, display names, and
  whether local metadata is available.
- `GET /api/papers?conference=<key>`: filters papers by source conference.

Existing filters for search, collection, uncollected, and multiple collections
continue to compose with the conference filter.

## Frontend

The app title changes from `ICML 2026 Paper Collections` to generic copy such as
`Paper Collections`.

The sidebar adds a conference/source filter:

- `All conferences`
- One button per configured conference with available display names.

The import button imports all locally available conference metadata by default.
Status text reports per-conference results when possible. Existing collection
filters and paper detail workflows remain unchanged.

Paper cards and details show the source conference when present, alongside venue,
area, and authors.

## Error Handling

- Missing metadata for a requested conference returns a clear error naming the
  expected JSONL or CSV paths.
- `all` import skips conferences without local metadata only if at least one
  conference can be imported; otherwise it returns a missing metadata error.
- Unknown conference keys return a 400 API response.
- Crawl summaries record queried venues, per-query counts, total unique papers,
  missing fields, and any venue-id cross-check.

## Testing

Use TDD for behavior changes.

Backend tests:

- `iclr2026` conference configuration exists and rejects unknown keys.
- Store migration adds `conference`.
- Paper upsert preserves existing notes/read status while updating conference.
- Importing a selected conference writes the conference key.
- Importing all local conferences returns per-conference counts.
- Listing papers filters by conference and composes with search/collection
  filters.
- `GET /api/conferences` reports configured conferences and metadata presence.

Frontend/static tests:

- Static HTML no longer contains ICML-only title copy.
- JavaScript includes conference loading and filtering behavior.
- Paper rendering includes conference metadata when available.

Manual verification:

- Run the ICLR crawl command and inspect `summary.json`.
- Import crawled ICLR data.
- Start the Flask app and confirm the UI shows both ICLR and ICML filter options.

## Delivery

Deliver the crawled ICLR metadata under `data/raw/iclr2026/`, the migrated app
code, updated tests, and a running local server URL for manual use.

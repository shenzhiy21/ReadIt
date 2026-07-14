import json
import sqlite3
import csv
import io
from datetime import datetime, timezone
from pathlib import Path


class PaperStore:
    def __init__(self, db_path):
        self.db_path = Path(db_path)

    def init_db(self):
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists papers (
                    id text primary key,
                    title text not null default '',
                    abstract text not null default '',
                    authors text not null default '',
                    conference text not null default '',
                    venue text not null default '',
                    primary_area text not null default '',
                    url text not null default '',
                    pdf text not null default '',
                    keywords text not null default '',
                    notes_markdown text not null default '',
                    is_read integer not null default 0,
                    raw_json text not null default '',
                    created_at text not null,
                    updated_at text not null
                );

                create table if not exists collections (
                    id integer primary key autoincrement,
                    name text not null unique,
                    source_file text not null default '',
                    created_at text not null,
                    updated_at text not null
                );

                create table if not exists paper_collections (
                    paper_id text not null,
                    collection_id integer not null,
                    created_at text not null,
                    primary key (paper_id, collection_id),
                    foreign key (paper_id) references papers(id) on delete cascade,
                    foreign key (collection_id) references collections(id) on delete cascade
                );
                """
            )
            self._migrate_db(conn)

    def import_papers_jsonl(self, path):
        imported = 0
        with Path(path).open("r", encoding="utf-8") as handle:
            with self._connect() as conn:
                for line in handle:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    self._upsert_paper(conn, row)
                    imported += 1
        return {"imported": imported}

    def import_papers_csv(self, path):
        imported = 0
        with Path(path).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            with self._connect() as conn:
                for row in reader:
                    if not any(row.values()):
                        continue
                    self._upsert_paper(conn, row)
                    imported += 1
        return {"imported": imported}

    def upsert_paper(self, row):
        with self._connect() as conn:
            self._upsert_paper(conn, row)

    def import_collection_tsv(self, path):
        path = Path(path)
        collection_name = path.stem
        papers = 0
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            with self._connect() as conn:
                collection = self._create_collection(
                    conn, collection_name, source_file=path.name
                )
                conn.execute(
                    "delete from paper_collections where collection_id = ?",
                    (collection["id"],),
                )
                for row in reader:
                    if not any(row.values()):
                        continue
                    paper_id = _paper_id(row)
                    self._upsert_paper(conn, row)
                    conn.execute(
                        """
                        insert or ignore into paper_collections (
                            paper_id, collection_id, created_at
                        )
                        values (?, ?, ?)
                        """,
                        (paper_id, collection["id"], _now()),
                    )
                    papers += 1
        return {"collection": collection_name, "papers": papers}

    def create_collection(self, name, source_file=""):
        with self._connect() as conn:
            return self._create_collection(conn, name, source_file=source_file)

    def list_collections(self):
        with self._connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    """
                    select c.id, c.name, c.source_file, c.created_at, c.updated_at,
                           count(pc.paper_id) as paper_count
                    from collections c
                    left join paper_collections pc on pc.collection_id = c.id
                    group by c.id
                    order by c.name
                    """
                )
            ]

    def rename_collection(self, collection_id, name):
        with self._connect() as conn:
            conn.execute(
                """
                update collections
                set name = ?, updated_at = ?
                where id = ?
                """,
                (name, _now(), collection_id),
            )

    def delete_collection(self, collection_id):
        with self._connect() as conn:
            conn.execute("delete from collections where id = ?", (collection_id,))

    def add_paper_to_collection(self, paper_id, collection_id):
        with self._connect() as conn:
            conn.execute(
                """
                insert or ignore into paper_collections (
                    paper_id, collection_id, created_at
                )
                values (?, ?, ?)
                """,
                (paper_id, collection_id, _now()),
            )

    def remove_paper_from_collection(self, paper_id, collection_id):
        with self._connect() as conn:
            conn.execute(
                """
                delete from paper_collections
                where paper_id = ? and collection_id = ?
                """,
                (paper_id, collection_id),
            )

    def update_paper_notes(self, paper_id, notes_markdown):
        with self._connect() as conn:
            cursor = conn.execute(
                """
                update papers
                set notes_markdown = ?, updated_at = ?
                where id = ?
                """,
                (str(notes_markdown or ""), _now(), paper_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_paper(paper_id)

    def update_paper_read_status(self, paper_id, is_read):
        with self._connect() as conn:
            cursor = conn.execute(
                """
                update papers
                set is_read = ?, updated_at = ?
                where id = ?
                """,
                (1 if is_read else 0, _now(), paper_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_paper(paper_id)

    def list_papers(
        self,
        search="",
        collection_id=None,
        uncollected=False,
        multiple_collections=False,
        conference="",
        limit=None,
        offset=0,
    ):
        where = []
        params = []
        search = (search or "").strip().lower()
        if search:
            params.extend([f"%{search}%"] * 7)
            where.append(
                """
                (
                    lower(p.id) like ?
                    or lower(p.title) like ?
                    or lower(p.abstract) like ?
                    or lower(p.authors) like ?
                    or lower(p.venue) like ?
                    or lower(p.primary_area) like ?
                    or exists (
                        select 1
                        from paper_collections pc_search
                        join collections c_search
                          on c_search.id = pc_search.collection_id
                        where pc_search.paper_id = p.id
                          and lower(c_search.name) like ?
                    )
                )
                """
            )
        if collection_id is not None:
            params.append(collection_id)
            where.append(
                """
                exists (
                    select 1 from paper_collections pc_filter
                    where pc_filter.paper_id = p.id
                      and pc_filter.collection_id = ?
                )
                """
            )
        if uncollected:
            where.append(
                """
                not exists (
                    select 1 from paper_collections pc_empty
                    where pc_empty.paper_id = p.id
                )
                """
            )
        if multiple_collections:
            where.append(
                """
                (
                    select count(*)
                    from paper_collections pc_multi
                    where pc_multi.paper_id = p.id
                ) > 1
                """
            )
        conference = (conference or "").strip()
        if conference:
            params.append(conference)
            where.append("p.conference = ?")
        query = """
            select p.id, p.title, p.abstract, p.authors, p.conference, p.venue,
                   p.primary_area, p.url, p.pdf, p.keywords, p.notes_markdown,
                   p.is_read, p.raw_json, p.created_at, p.updated_at
            from papers p
        """
        if where:
            query += " where " + " and ".join(where)
        query += " order by lower(p.title), p.id"
        if limit is not None:
            query += " limit ? offset ?"
            params.extend([limit, offset])

        with self._connect() as conn:
            papers = [_paper_dict(row) for row in conn.execute(query, params)]
            for paper in papers:
                paper["collections"] = self._collections_for_paper(conn, paper["id"])
            return papers

    def export_collection_tsv(self, collection_id):
        with self._connect() as conn:
            rows = conn.execute(
                """
                select p.id, p.url, p.venue, p.primary_area, p.title, p.abstract
                from papers p
                join paper_collections pc on pc.paper_id = p.id
                where pc.collection_id = ?
                order by lower(p.title), p.id
                """,
                (collection_id,),
            ).fetchall()
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["id", "url", "venue", "primary_area", "title", "abstract"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
        return output.getvalue()

    def export_all_collections_tsv(self):
        with self._connect() as conn:
            rows = conn.execute(
                """
                select c.name as collection, p.id, p.url, p.venue,
                       p.primary_area, p.title, p.abstract
                from collections c
                join paper_collections pc on pc.collection_id = c.id
                join papers p on p.id = pc.paper_id
                order by lower(c.name), lower(p.title), p.id
                """
            ).fetchall()
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=[
                "collection",
                "id",
                "url",
                "venue",
                "primary_area",
                "title",
                "abstract",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
        return output.getvalue()

    def get_paper(self, paper_id):
        with self._connect() as conn:
            row = conn.execute(
                """
                select id, title, abstract, authors, conference, venue,
                       primary_area, url, pdf, keywords, notes_markdown, is_read,
                       raw_json, created_at, updated_at
                from papers
                where id = ?
                """,
                (paper_id,),
            ).fetchone()
            if row is None:
                return None
            paper = _paper_dict(row)
            paper["collections"] = self._collections_for_paper(conn, paper_id)
            return paper

    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("pragma foreign_keys = on")
        return conn

    def _migrate_db(self, conn):
        paper_columns = {
            row["name"] for row in conn.execute("pragma table_info(papers)")
        }
        if "notes_markdown" not in paper_columns:
            conn.execute(
                "alter table papers add column notes_markdown text not null default ''"
            )
        if "is_read" not in paper_columns:
            conn.execute(
                "alter table papers add column is_read integer not null default 0"
            )
        if "conference" not in paper_columns:
            conn.execute(
                "alter table papers add column conference text not null default ''"
            )

    def _upsert_paper(self, conn, row):
        now = _now()
        paper_id = _paper_id(row)
        values = {
            "id": paper_id,
            "title": row.get("title", "") or "",
            "abstract": row.get("abstract", "") or "",
            "authors": _join(row.get("authors", "")),
            "conference": row.get("conference", "") or "",
            "venue": row.get("venue", "") or "",
            "primary_area": row.get("primary_area", "") or "",
            "url": row.get("url", "") or "",
            "pdf": row.get("pdf", "") or "",
            "keywords": _join(row.get("keywords", "")),
            "raw_json": json.dumps(row, ensure_ascii=False),
            "created_at": now,
            "updated_at": now,
        }
        conn.execute(
            """
            insert into papers (
                id, title, abstract, authors, conference, venue, primary_area,
                url, pdf, keywords, raw_json, created_at, updated_at
            )
            values (
                :id, :title, :abstract, :authors, :conference, :venue,
                :primary_area, :url, :pdf, :keywords, :raw_json, :created_at,
                :updated_at
            )
            on conflict(id) do update set
                title = case
                    when excluded.title != '' then excluded.title
                    else papers.title
                end,
                abstract = case
                    when excluded.abstract != '' then excluded.abstract
                    else papers.abstract
                end,
                authors = case
                    when excluded.authors != '' then excluded.authors
                    else papers.authors
                end,
                conference = case
                    when excluded.conference != '' then excluded.conference
                    else papers.conference
                end,
                venue = case
                    when excluded.venue != '' then excluded.venue
                    else papers.venue
                end,
                primary_area = case
                    when excluded.primary_area != '' then excluded.primary_area
                    else papers.primary_area
                end,
                url = case
                    when excluded.url != '' then excluded.url
                    else papers.url
                end,
                pdf = case
                    when excluded.pdf != '' then excluded.pdf
                    else papers.pdf
                end,
                keywords = case
                    when excluded.keywords != '' then excluded.keywords
                    else papers.keywords
                end,
                raw_json = excluded.raw_json,
                updated_at = excluded.updated_at
            """,
            values,
        )

    def _create_collection(self, conn, name, source_file=""):
        now = _now()
        conn.execute(
            """
            insert into collections (name, source_file, created_at, updated_at)
            values (?, ?, ?, ?)
            on conflict(name) do update set
                source_file = case
                    when excluded.source_file != '' then excluded.source_file
                    else collections.source_file
                end,
                updated_at = excluded.updated_at
            """,
            (name, source_file or "", now, now),
        )
        row = conn.execute(
            """
            select id, name, source_file, created_at, updated_at
            from collections
            where name = ?
            """,
            (name,),
        ).fetchone()
        return dict(row)

    def _collections_for_paper(self, conn, paper_id):
        return [
            {"id": collection["id"], "name": collection["name"]}
            for collection in conn.execute(
                """
                select c.id, c.name
                from collections c
                join paper_collections pc on pc.collection_id = c.id
                where pc.paper_id = ?
                order by c.name
                """,
                (paper_id,),
            )
        ]


def _paper_id(row):
    for key in ("id", "openreview_id", "forum"):
        value = row.get(key)
        if value:
            return str(value)
    url = row.get("url", "")
    marker = "id="
    if marker in url:
        return url.split(marker, 1)[1].split("&", 1)[0]
    raise ValueError("paper row is missing id/openreview_id/forum/url")


def _join(value):
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value or "")


def _paper_dict(row):
    paper = dict(row)
    paper["is_read"] = bool(paper["is_read"])
    return paper


def _now():
    return datetime.now(timezone.utc).isoformat()

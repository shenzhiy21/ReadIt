import json
import sqlite3

from paperlib.store import PaperStore


def test_init_creates_tables(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    store = PaperStore(db_path)
    store.init_db()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

    assert {"papers", "collections", "paper_collections"} <= tables


def test_import_jsonl_upserts_papers_without_collections(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    jsonl_path = tmp_path / "papers.jsonl"
    jsonl_path.write_text(
        json.dumps(
            {
                "openreview_id": "paper-1",
                "forum": "paper-1",
                "venue": "ICML 2026 regular",
                "title": "Chart Reasoning",
                "authors": ["A", "B"],
                "abstract": "Reasoning over charts.",
                "primary_area": "general_machine_learning->evaluation",
                "keywords": ["chart", "reasoning"],
                "pdf": "/pdf/paper-1.pdf",
                "url": "https://openreview.net/forum?id=paper-1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    store = PaperStore(db_path)
    store.init_db()

    result = store.import_papers_jsonl(jsonl_path)
    paper = store.get_paper("paper-1")

    assert result == {"imported": 1}
    assert paper["title"] == "Chart Reasoning"
    assert paper["authors"] == "A; B"
    assert paper["collections"] == []


def test_updates_and_reads_paper_notes(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart QA"})

    updated = store.update_paper_notes("paper-1", "# Notes\n\n- read")
    paper = store.get_paper("paper-1")

    assert updated["notes_markdown"] == "# Notes\n\n- read"
    assert paper["notes_markdown"] == "# Notes\n\n- read"


def test_papers_default_to_unread_and_can_be_marked_read(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart QA"})

    assert store.get_paper("paper-1")["is_read"] is False

    updated = store.update_paper_read_status("paper-1", True)
    listed = store.list_papers()

    assert updated["is_read"] is True
    assert store.get_paper("paper-1")["is_read"] is True
    assert listed[0]["is_read"] is True


def test_upsert_preserves_existing_paper_notes(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "First"})
    store.update_paper_notes("paper-1", "keep this")

    store.upsert_paper({"id": "paper-1", "title": "Updated"})
    paper = store.get_paper("paper-1")

    assert paper["title"] == "Updated"
    assert paper["notes_markdown"] == "keep this"


def test_upsert_preserves_existing_paper_read_status(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "First"})
    store.update_paper_read_status("paper-1", True)

    store.upsert_paper({"id": "paper-1", "title": "Updated"})
    paper = store.get_paper("paper-1")

    assert paper["title"] == "Updated"
    assert paper["is_read"] is True


def test_paper_store_records_conference(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()

    store.upsert_paper(
        {
            "id": "paper-1",
            "title": "Chart QA",
            "conference": "iclr2026",
        }
    )

    paper = store.get_paper("paper-1")

    assert paper["conference"] == "iclr2026"


def test_upsert_preserves_notes_and_read_status_when_conference_updates(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Old"})
    store.update_paper_notes("paper-1", "keep this")
    store.update_paper_read_status("paper-1", True)

    store.upsert_paper(
        {
            "id": "paper-1",
            "title": "New",
            "conference": "icml2026",
        }
    )

    paper = store.get_paper("paper-1")

    assert paper["title"] == "New"
    assert paper["conference"] == "icml2026"
    assert paper["notes_markdown"] == "keep this"
    assert paper["is_read"] is True


def test_list_papers_filters_by_conference(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "A", "conference": "iclr2026"})
    store.upsert_paper({"id": "paper-2", "title": "B", "conference": "icml2026"})

    papers = store.list_papers(conference="iclr2026")

    assert [paper["id"] for paper in papers] == ["paper-1"]


def test_init_migrates_existing_database_with_notes_column(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            create table papers (
                id text primary key,
                title text not null default '',
                abstract text not null default '',
                authors text not null default '',
                venue text not null default '',
                primary_area text not null default '',
                url text not null default '',
                pdf text not null default '',
                keywords text not null default '',
                raw_json text not null default '',
                created_at text not null,
                updated_at text not null
            );
            """
        )

    store = PaperStore(db_path)
    store.init_db()

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("pragma table_info(papers)")}

    assert "notes_markdown" in columns


def test_init_migrates_existing_database_with_read_status_column(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            create table papers (
                id text primary key,
                title text not null default '',
                abstract text not null default '',
                authors text not null default '',
                venue text not null default '',
                primary_area text not null default '',
                url text not null default '',
                pdf text not null default '',
                keywords text not null default '',
                notes_markdown text not null default '',
                raw_json text not null default '',
                created_at text not null,
                updated_at text not null
            );
            """
        )

    store = PaperStore(db_path)
    store.init_db()

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("pragma table_info(papers)")}

    assert "is_read" in columns


def test_import_csv_upserts_papers(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "openreview_id,forum,venue,title,authors,abstract,primary_area,keywords,pdf,url\n"
        "paper-1,paper-1,ICML 2026 regular,Chart Reasoning,A; B,"
        "Reasoning over charts.,evaluation,chart; reasoning,/pdf/paper-1.pdf,"
        "https://openreview.net/forum?id=paper-1\n",
        encoding="utf-8",
    )
    store = PaperStore(db_path)
    store.init_db()

    result = store.import_papers_csv(csv_path)
    paper = store.get_paper("paper-1")

    assert result == {"imported": 1}
    assert paper["title"] == "Chart Reasoning"
    assert paper["authors"] == "A; B"


def test_import_tsv_creates_collection_and_memberships(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    tsv_path = tmp_path / "keep.tsv"
    tsv_path.write_text(
        "id\turl\ttitle\tabstract\n"
        "paper-1\thttps://openreview.net/forum?id=paper-1\tChart Reasoning\tA\n",
        encoding="utf-8",
    )
    store = PaperStore(db_path)
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart Reasoning"})

    result = store.import_collection_tsv(tsv_path)
    collections = store.list_collections()
    paper = store.get_paper("paper-1")

    assert result == {"collection": "keep", "papers": 1}
    assert collections[0]["name"] == "keep"
    assert collections[0]["paper_count"] == 1
    assert paper["collections"] == [{"id": collections[0]["id"], "name": "keep"}]


def test_import_tsv_creates_minimal_missing_paper(tmp_path):
    db_path = tmp_path / "papers.sqlite"
    tsv_path = tmp_path / "new.tsv"
    tsv_path.write_text(
        "id\turl\ttitle\tabstract\n"
        "missing\thttps://openreview.net/forum?id=missing\tMissing Paper\tAbstract\n",
        encoding="utf-8",
    )
    store = PaperStore(db_path)
    store.init_db()

    store.import_collection_tsv(tsv_path)
    paper = store.get_paper("missing")

    assert paper["title"] == "Missing Paper"
    assert paper["abstract"] == "Abstract"
    assert paper["collections"][0]["name"] == "new"


def test_collection_papers_are_ordered_by_year_newest_first(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    papers = [
        {"id": "unknown", "title": "A", "venue": "Workshop"},
        {"id": "old", "title": "Z", "conference": "tvcg2023"},
        {"id": "new-z", "title": "Z", "venue": "IEEE TVCG 2026"},
        {"id": "new-a", "title": "A", "year": 2026},
        {"id": "middle", "title": "M", "conference": "tvcg2025"},
    ]
    collection = store.create_collection("reading")
    for paper in papers:
        store.upsert_paper(paper)
        store.add_paper_to_collection(paper["id"], collection["id"])

    assert [
        paper["id"]
        for paper in store.list_papers(collection_id=collection["id"])
    ] == ["new-a", "new-z", "middle", "old", "unknown"]


def test_collection_crud_does_not_delete_papers(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "A"})
    collection = store.create_collection("reading")
    store.add_paper_to_collection("paper-1", collection["id"])

    store.rename_collection(collection["id"], "priority")
    assert store.list_collections()[0]["name"] == "priority"

    store.delete_collection(collection["id"])
    assert store.get_paper("paper-1")["title"] == "A"
    assert store.get_paper("paper-1")["collections"] == []


def test_list_papers_search_and_collection_filters(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart QA", "abstract": "charts"})
    store.upsert_paper({"id": "paper-2", "title": "Optimization", "abstract": "math"})
    collection = store.create_collection("keep")
    store.add_paper_to_collection("paper-1", collection["id"])

    assert [p["id"] for p in store.list_papers(search="chart")] == ["paper-1"]
    assert [p["id"] for p in store.list_papers(collection_id=collection["id"])] == [
        "paper-1"
    ]
    assert [p["id"] for p in store.list_papers(uncollected=True)] == ["paper-2"]


def test_list_papers_multiple_collection_filter(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart QA"})
    store.upsert_paper({"id": "paper-2", "title": "Doc QA"})
    first = store.create_collection("first")
    second = store.create_collection("second")
    store.add_paper_to_collection("paper-1", first["id"])
    store.add_paper_to_collection("paper-1", second["id"])
    store.add_paper_to_collection("paper-2", first["id"])

    assert [p["id"] for p in store.list_papers(multiple_collections=True)] == [
        "paper-1"
    ]


def test_export_collection_tsv(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart QA", "abstract": "charts"})
    collection = store.create_collection("keep")
    store.add_paper_to_collection("paper-1", collection["id"])

    tsv = store.export_collection_tsv(collection["id"])

    assert tsv.splitlines()[0] == "id\turl\tvenue\tprimary_area\ttitle\tabstract"
    assert "paper-1" in tsv
    assert "Chart QA" in tsv


def test_export_all_collections_tsv(tmp_path):
    store = PaperStore(tmp_path / "papers.sqlite")
    store.init_db()
    store.upsert_paper({"id": "paper-1", "title": "Chart QA"})
    collection = store.create_collection("keep")
    store.add_paper_to_collection("paper-1", collection["id"])

    tsv = store.export_all_collections_tsv()

    assert tsv.splitlines()[0] == (
        "collection\tid\turl\tvenue\tprimary_area\ttitle\tabstract"
    )
    assert "keep\tpaper-1" in tsv

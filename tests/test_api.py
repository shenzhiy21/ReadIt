import io

from paperlib.web import create_app


def test_serves_frontend(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Paper Collections" in response.data


def test_api_imports_default_papers(tmp_path):
    data_dir = tmp_path
    raw_dir = data_dir / "raw" / "icml2026"
    raw_dir.mkdir(parents=True)
    jsonl = raw_dir / "accepted_papers.jsonl"
    jsonl.write_text(
        '{"openreview_id":"paper-1","title":"Chart QA","abstract":"charts"}\n',
        encoding="utf-8",
    )
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=data_dir)
    client = app.test_client()

    response = client.post("/api/import/papers")

    assert response.status_code == 200
    assert response.get_json()["imported"] == 1


def test_api_imports_default_csv_when_jsonl_is_missing(tmp_path):
    data_dir = tmp_path
    raw_dir = data_dir / "raw" / "icml2026"
    raw_dir.mkdir(parents=True)
    csv_path = raw_dir / "accepted_papers.csv"
    csv_path.write_text(
        "openreview_id,forum,title,abstract\n"
        "paper-1,paper-1,Chart QA,charts\n",
        encoding="utf-8",
    )
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=data_dir)
    client = app.test_client()

    response = client.post("/api/import/papers")

    assert response.status_code == 200
    assert response.get_json()["imported"] == 1


def test_api_imports_selected_conference_with_source_key(tmp_path):
    data_dir = tmp_path
    raw_dir = data_dir / "raw" / "iclr2026"
    raw_dir.mkdir(parents=True)
    (raw_dir / "accepted_papers.jsonl").write_text(
        '{"openreview_id":"paper-1","title":"ICLR Paper"}\n',
        encoding="utf-8",
    )
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=data_dir)
    client = app.test_client()

    response = client.post("/api/import/papers", json={"conference": "iclr2026"})
    paper = client.get("/api/papers/paper-1").get_json()

    assert response.status_code == 200
    assert response.get_json()["imported"] == 1
    assert response.get_json()["conferences"] == {"iclr2026": 1}
    assert paper["conference"] == "iclr2026"


def test_api_imports_all_available_conferences(tmp_path):
    data_dir = tmp_path
    for conference, title in (("iclr2026", "ICLR Paper"), ("icml2026", "ICML Paper")):
        raw_dir = data_dir / "raw" / conference
        raw_dir.mkdir(parents=True)
        (raw_dir / "accepted_papers.jsonl").write_text(
            f'{{"openreview_id":"{conference}-paper","title":"{title}"}}\n',
            encoding="utf-8",
        )
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=data_dir)
    client = app.test_client()

    response = client.post("/api/import/papers", json={"conference": "all"})

    assert response.status_code == 200
    assert response.get_json()["imported"] == 2
    assert response.get_json()["conferences"] == {
        "iclr2026": 1,
        "icml2026": 1,
    }


def test_api_rejects_unknown_import_conference(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.post("/api/import/papers", json={"conference": "missing"})

    assert response.status_code == 400
    assert "Unknown conference" in response.get_json()["error"]


def test_api_lists_papers_filtered_by_conference(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    store = app.config["STORE"]
    store.upsert_paper({"id": "paper-1", "title": "A", "conference": "iclr2026"})
    store.upsert_paper({"id": "paper-2", "title": "B", "conference": "icml2026"})

    response = client.get("/api/papers?conference=iclr2026")

    assert response.status_code == 200
    assert [paper["id"] for paper in response.get_json()["papers"]] == ["paper-1"]


def test_api_lists_papers_with_total_for_pagination(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    store = app.config["STORE"]
    for index in range(12):
        store.upsert_paper({"id": f"paper-{index:02d}", "title": f"Paper {index:02d}"})

    response = client.get("/api/papers?limit=10&offset=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 12
    assert [paper["id"] for paper in payload["papers"]] == ["paper-10", "paper-11"]


def test_api_lists_conferences_with_metadata_presence(tmp_path):
    raw_dir = tmp_path / "raw" / "iclr2026"
    raw_dir.mkdir(parents=True)
    (raw_dir / "accepted_papers.jsonl").write_text("", encoding="utf-8")
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.get("/api/conferences")

    assert response.status_code == 200
    conferences = {item["key"]: item for item in response.get_json()["conferences"]}
    assert conferences["iclr2026"]["name"] == "ICLR 2026"
    assert conferences["iclr2026"]["metadata_available"] is True
    assert conferences["icml2026"]["metadata_available"] is False


def test_api_collection_membership_roundtrip(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    store = app.config["STORE"]
    store.upsert_paper({"id": "paper-1", "title": "Chart QA"})

    created = client.post("/api/collections", json={"name": "keep"}).get_json()
    add_response = client.post(f"/api/papers/paper-1/collections/{created['id']}")
    paper = client.get("/api/papers/paper-1").get_json()

    assert add_response.status_code == 200
    assert paper["collections"] == [{"id": created["id"], "name": "keep"}]

    remove_response = client.delete(
        f"/api/papers/paper-1/collections/{created['id']}"
    )
    paper_after_remove = client.get("/api/papers/paper-1").get_json()

    assert remove_response.status_code == 200
    assert paper_after_remove["collections"] == []


def test_api_updates_paper_notes(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    app.config["STORE"].upsert_paper({"id": "paper-1", "title": "Chart QA"})

    response = client.patch(
        "/api/papers/paper-1/notes",
        json={"notes_markdown": "# Notes\n\nImportant."},
    )
    paper = client.get("/api/papers/paper-1").get_json()

    assert response.status_code == 200
    assert response.get_json()["notes_markdown"] == "# Notes\n\nImportant."
    assert paper["notes_markdown"] == "# Notes\n\nImportant."


def test_api_updates_paper_read_status(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    app.config["STORE"].upsert_paper({"id": "paper-1", "title": "Chart QA"})

    response = client.patch("/api/papers/paper-1/read", json={"is_read": True})
    paper = client.get("/api/papers/paper-1").get_json()
    listed = client.get("/api/papers").get_json()["papers"]

    assert response.status_code == 200
    assert response.get_json()["is_read"] is True
    assert paper["is_read"] is True
    assert listed[0]["is_read"] is True


def test_api_rejects_invalid_paper_read_status_payload(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    app.config["STORE"].upsert_paper({"id": "paper-1", "title": "Chart QA"})

    response = client.patch("/api/papers/paper-1/read", json={"is_read": "true"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "is_read boolean is required"


def test_api_returns_404_when_updating_missing_paper_notes(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.patch(
        "/api/papers/missing/notes",
        json={"notes_markdown": "note"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Paper not found"


def test_api_returns_404_when_updating_missing_paper_read_status(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.patch("/api/papers/missing/read", json={"is_read": True})

    assert response.status_code == 404
    assert response.get_json()["error"] == "Paper not found"


def test_api_imports_uploaded_tsv_collection(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.post(
        "/api/import/collection",
        data={
            "file": (
                io.BytesIO(
                    b"id\turl\ttitle\tabstract\n"
                    b"paper-1\thttps://openreview.net/forum?id=paper-1\tChart QA\tA\n"
                ),
                "reading.tsv",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {"collection": "reading", "papers": 1}
    assert client.get("/api/collections").get_json()[0]["name"] == "reading"


def test_api_renames_and_deletes_collection_without_deleting_paper(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    store = app.config["STORE"]
    store.upsert_paper({"id": "paper-1", "title": "Chart QA"})
    collection = client.post("/api/collections", json={"name": "draft"}).get_json()
    client.post(f"/api/papers/paper-1/collections/{collection['id']}")

    renamed = client.patch(
        f"/api/collections/{collection['id']}", json={"name": "final"}
    )
    deleted = client.delete(f"/api/collections/{collection['id']}")
    paper = client.get("/api/papers/paper-1").get_json()

    assert renamed.status_code == 200
    assert renamed.get_json()["name"] == "final"
    assert deleted.status_code == 200
    assert paper["title"] == "Chart QA"
    assert paper["collections"] == []


def test_api_lists_papers_with_filters_and_exports_collection(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()
    store = app.config["STORE"]
    store.upsert_paper({"id": "paper-1", "title": "Chart QA", "abstract": "charts"})
    store.upsert_paper({"id": "paper-2", "title": "Optimization"})
    collection = store.create_collection("keep")
    store.add_paper_to_collection("paper-1", collection["id"])

    search = client.get("/api/papers?q=chart").get_json()
    filtered = client.get(f"/api/papers?collection_id={collection['id']}").get_json()
    uncollected = client.get("/api/papers?uncollected=true").get_json()
    exported = client.get(f"/api/export/collections/{collection['id']}")
    exported_all = client.get("/api/export/collections")

    assert [paper["id"] for paper in search["papers"]] == ["paper-1"]
    assert [paper["id"] for paper in filtered["papers"]] == ["paper-1"]
    assert [paper["id"] for paper in uncollected["papers"]] == ["paper-2"]
    assert exported.status_code == 200
    assert exported.get_data(as_text=True).splitlines()[0] == (
        "id\turl\tvenue\tprimary_area\ttitle\tabstract"
    )
    assert exported_all.status_code == 200
    assert exported_all.get_data(as_text=True).splitlines()[0] == (
        "collection\tid\turl\tvenue\tprimary_area\ttitle\tabstract"
    )

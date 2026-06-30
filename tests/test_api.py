import io

from paperlib.web import create_app


def test_serves_frontend(tmp_path):
    app = create_app(db_path=tmp_path / "papers.sqlite", data_dir=tmp_path)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"ICML 2026 Paper Collections" in response.data


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

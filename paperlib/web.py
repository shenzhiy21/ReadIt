import tempfile
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from paperlib.config import DEFAULT_PUBLICATION, data_dir as default_data_dir
from paperlib.config import default_db_path
from paperlib.crawlers.publications import PUBLICATIONS, get_publication
from paperlib.imports import find_paper_metadata, has_paper_metadata
from paperlib.store import PaperStore


def create_app(db_path=None, data_dir=None, publication_key=DEFAULT_PUBLICATION):
    static_dir = Path(__file__).resolve().parents[1] / "static"
    app = Flask(__name__, static_folder=str(static_dir), static_url_path="/static")
    data_dir = Path(data_dir) if data_dir is not None else default_data_dir()
    db_path = Path(db_path) if db_path is not None else default_db_path()
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = PaperStore(db_path)
    store.init_db()
    app.config["STORE"] = store
    app.config["DATA_DIR"] = data_dir
    app.config["PUBLICATION_KEY"] = publication_key

    @app.get("/")
    def index():
        return send_from_directory(static_dir, "index.html")

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(KeyError)
    def handle_key_error(error):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(FileNotFoundError)
    def handle_file_not_found(error):
        return jsonify({"error": str(error)}), 404

    @app.post("/api/import/papers")
    def import_papers():
        payload = request.get_json(silent=True) or {}
        selected = (
            payload.get("publication") or payload.get("conference") or "all"
        ).strip()
        if selected == "all":
            result = _import_all_available_publications(store, data_dir)
        else:
            get_publication(selected)
            result = _import_one_publication(store, data_dir, selected)
        return jsonify(result)

    @app.post("/api/import/collection")
    def import_collection():
        uploaded = request.files.get("file")
        if uploaded is None or uploaded.filename == "":
            return jsonify({"error": "Missing TSV file upload"}), 400
        original_name = Path(uploaded.filename).name
        if not original_name.lower().endswith(".tsv"):
            return jsonify({"error": "Collection import expects a .tsv file"}), 400
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / original_name
            uploaded.save(path)
            result = store.import_collection_tsv(path)
        return jsonify(result)

    @app.get("/api/publications")
    def list_publications():
        publications = []
        for key, config in sorted(PUBLICATIONS.items()):
            publications.append(
                {
                    "key": key,
                    "name": config.name,
                    "metadata_available": has_paper_metadata(data_dir, key),
                }
            )
        return jsonify({"publications": publications})

    @app.get("/api/conferences")
    def list_conferences_legacy():
        response = list_publications().get_json()
        return jsonify({"conferences": response["publications"]})

    @app.get("/api/collections")
    def list_collections():
        return jsonify(store.list_collections())

    @app.post("/api/collections")
    def create_collection():
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Collection name is required"}), 400
        try:
            collection = store.create_collection(name)
        except Exception as error:
            return jsonify({"error": str(error)}), 400
        return jsonify(collection)

    @app.patch("/api/collections/<int:collection_id>")
    def rename_collection(collection_id):
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Collection name is required"}), 400
        store.rename_collection(collection_id, name)
        collection = _find_collection(store, collection_id)
        if collection is None:
            return jsonify({"error": "Collection not found"}), 404
        return jsonify(collection)

    @app.delete("/api/collections/<int:collection_id>")
    def delete_collection(collection_id):
        store.delete_collection(collection_id)
        return jsonify({"deleted": True})

    @app.get("/api/papers")
    def list_papers():
        collection_id = request.args.get("collection_id", type=int)
        uncollected = _truthy(request.args.get("uncollected"))
        multiple = _truthy(request.args.get("multiple"))
        limit = request.args.get("limit", default=250, type=int)
        offset = request.args.get("offset", default=0, type=int)
        search = request.args.get("q", "")
        publication = request.args.get(
            "publication", request.args.get("conference", "")
        )
        papers = store.list_papers(
            search=search,
            collection_id=collection_id,
            uncollected=uncollected,
            multiple_collections=multiple,
            conference=publication,
            limit=limit,
            offset=offset,
        )
        total = store.count_papers(
            search=search,
            collection_id=collection_id,
            uncollected=uncollected,
            multiple_collections=multiple,
            conference=publication,
        )
        return jsonify(
            {"papers": [_paper_for_api(paper) for paper in papers], "total": total}
        )

    @app.get("/api/papers/<path:paper_id>")
    def get_paper(paper_id):
        paper = store.get_paper(paper_id)
        if paper is None:
            return jsonify({"error": "Paper not found"}), 404
        return jsonify(_paper_for_api(paper))

    @app.patch("/api/papers/<path:paper_id>/notes")
    def update_paper_notes(paper_id):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or "notes_markdown" not in payload:
            return jsonify({"error": "notes_markdown is required"}), 400
        paper = store.update_paper_notes(paper_id, payload["notes_markdown"])
        if paper is None:
            return jsonify({"error": "Paper not found"}), 404
        return jsonify(_paper_for_api(paper))

    @app.patch("/api/papers/<path:paper_id>/read")
    def update_paper_read_status(paper_id):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not isinstance(
            payload.get("is_read"), bool
        ):
            return jsonify({"error": "is_read boolean is required"}), 400
        paper = store.update_paper_read_status(paper_id, payload["is_read"])
        if paper is None:
            return jsonify({"error": "Paper not found"}), 404
        return jsonify(_paper_for_api(paper))

    @app.post("/api/papers/<path:paper_id>/collections/<int:collection_id>")
    def add_paper_to_collection(paper_id, collection_id):
        store.add_paper_to_collection(paper_id, collection_id)
        return jsonify({"ok": True})

    @app.delete("/api/papers/<path:paper_id>/collections/<int:collection_id>")
    def remove_paper_from_collection(paper_id, collection_id):
        store.remove_paper_from_collection(paper_id, collection_id)
        return jsonify({"ok": True})

    @app.get("/api/export/collections/<int:collection_id>")
    def export_collection(collection_id):
        tsv = store.export_collection_tsv(collection_id)
        return Response(
            tsv,
            mimetype="text/tab-separated-values",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=collection-{collection_id}.tsv"
                )
            },
        )

    @app.get("/api/export/collections")
    def export_collections():
        tsv = store.export_all_collections_tsv()
        return Response(
            tsv,
            mimetype="text/tab-separated-values",
            headers={
                "Content-Disposition": "attachment; filename=collections.tsv"
            },
        )

    return app


def _find_collection(store, collection_id):
    for collection in store.list_collections():
        if collection["id"] == collection_id:
            return collection
    return None


def _paper_for_api(paper):
    result = dict(paper)
    result["publication"] = result.get("conference", "")
    return result


def _import_all_available_publications(store, data_dir):
    imported_by_publication = {}
    for key in sorted(PUBLICATIONS):
        if not has_paper_metadata(data_dir, key):
            continue
        imported_by_publication[key] = _import_one_publication(
            store, data_dir, key
        )["imported"]
    if not imported_by_publication:
        known = ", ".join(sorted(PUBLICATIONS))
        raise FileNotFoundError(
            f"Missing paper metadata for all known publications: {known}"
        )
    return {
        "imported": sum(imported_by_publication.values()),
        "publications": imported_by_publication,
    }


def _import_one_publication(store, data_dir, publication_key):
    metadata_path = find_paper_metadata(data_dir, publication_key)
    if metadata_path.suffix == ".jsonl":
        result = store.import_papers_jsonl(metadata_path, conference=publication_key)
    else:
        result = store.import_papers_csv(metadata_path, conference=publication_key)
    return {
        "imported": result["imported"],
        "publications": {publication_key: result["imported"]},
    }


def _truthy(value):
    return str(value or "").lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)

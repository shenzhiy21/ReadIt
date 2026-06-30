import tempfile
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from paperlib.config import DEFAULT_CONFERENCE, data_dir as default_data_dir
from paperlib.config import default_db_path
from paperlib.imports import find_paper_metadata
from paperlib.store import PaperStore


def create_app(db_path=None, data_dir=None, conference_key=DEFAULT_CONFERENCE):
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
    app.config["CONFERENCE_KEY"] = conference_key

    @app.get("/")
    def index():
        return send_from_directory(static_dir, "index.html")

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(FileNotFoundError)
    def handle_file_not_found(error):
        return jsonify({"error": str(error)}), 404

    @app.post("/api/import/papers")
    def import_papers():
        metadata_path = find_paper_metadata(data_dir, conference_key)
        if metadata_path.suffix == ".jsonl":
            return jsonify(store.import_papers_jsonl(metadata_path))
        return jsonify(store.import_papers_csv(metadata_path))

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
        papers = store.list_papers(
            search=request.args.get("q", ""),
            collection_id=collection_id,
            uncollected=uncollected,
            multiple_collections=multiple,
            limit=limit,
            offset=offset,
        )
        return jsonify({"papers": papers})

    @app.get("/api/papers/<path:paper_id>")
    def get_paper(paper_id):
        paper = store.get_paper(paper_id)
        if paper is None:
            return jsonify({"error": "Paper not found"}), 404
        return jsonify(paper)

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


def _truthy(value):
    return str(value or "").lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)

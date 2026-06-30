from pathlib import Path


def find_paper_metadata(data_dir, conference_key):
    raw_dir = Path(data_dir) / "raw" / conference_key
    jsonl_path = raw_dir / "accepted_papers.jsonl"
    csv_path = raw_dir / "accepted_papers.csv"
    if jsonl_path.exists():
        return jsonl_path
    if csv_path.exists():
        return csv_path
    raise FileNotFoundError(
        f"Missing paper metadata: expected {jsonl_path} or {csv_path}"
    )

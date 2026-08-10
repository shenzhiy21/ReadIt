from pathlib import Path


DEFAULT_PUBLICATION = "icml2026"


def data_dir():
    return Path("data")


def default_db_path():
    return data_dir() / "papers.sqlite"


def raw_publication_dir(publication_key, base_data_dir=None):
    base = Path(base_data_dir) if base_data_dir is not None else data_dir()
    return base / "raw" / publication_key

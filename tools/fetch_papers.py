#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paperlib.config import data_dir
from paperlib.crawlers.dblp import fetch_journal_volume
from paperlib.crawlers.openreview import fetch_conference
from paperlib.crawlers.publications import DblpJournalVolume, get_publication


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("publications", nargs="+")
    parser.add_argument("--data-dir", default=str(data_dir()))
    args = parser.parse_args()

    summaries = {}
    for key in args.publications:
        config = get_publication(key)
        if isinstance(config, DblpJournalVolume):
            summary = fetch_journal_volume(config, Path(args.data_dir))
        else:
            summary = fetch_conference(config, Path(args.data_dir))
        summaries[key] = summary

    output = next(iter(summaries.values())) if len(summaries) == 1 else summaries
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

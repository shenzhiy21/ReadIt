#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paperlib.config import data_dir
from paperlib.crawlers.conferences import get_conference
from paperlib.crawlers.openreview import fetch_conference


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("conference")
    parser.add_argument("--data-dir", default=str(data_dir()))
    args = parser.parse_args()

    config = get_conference(args.conference)
    summary = fetch_conference(config, Path(args.data_dir))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Repeatable official-document acquisition; manual files remain pending review.

python -m scripts.ingest_filings --ticker INFY
python -m scripts.ingest_filings --ticker INFY --manual path/to/download.pdf
python -m scripts.ingest_filings --review data/reviews/infy.json --document doc-...
"""
import argparse
import json
from pathlib import Path

from app.services.filing_archive import FilingArchive, FilingMetadata

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticker')
    parser.add_argument('--catalog', type=Path, default=ROOT / 'data/source_catalog.json')
    parser.add_argument('--manual', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--document')
    args = parser.parse_args()
    archive = FilingArchive(ROOT / 'data/filings')
    if args.review:
        record = archive.apply_review(args.document, json.loads(args.review.read_text(encoding='utf-8')))
        print(record['id'], record['review_status'])
        return
    entries = json.loads(args.catalog.read_text(encoding='utf-8'))
    entries = [m for m in entries if not args.ticker or m['ticker'] == args.ticker.upper()]
    if not entries or (args.manual and len(entries) != 1):
        parser.error('Select exactly one catalog entry for manual import')
    for item in entries:
        metadata = FilingMetadata(**item)
        try:
            record = archive.ingest_bytes(metadata, args.manual.read_bytes()) if args.manual else archive.fetch(metadata)
            print(metadata.ticker, record['id'], record['review_status'], record['byte_count'])
        except ValueError as exc:
            print(metadata.ticker, str(exc))
            raise SystemExit(1)


if __name__ == '__main__':
    main()

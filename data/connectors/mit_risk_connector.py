"""
MIT AI Risk Repository connector.

Downloads the MIT AIRR dataset CSV and classifies each entry against the
nine Aletheia behavioral signatures.

Data source: https://airisk.mit.edu/
GitHub: https://github.com/mitre/airisk (data/ directory)

To get the CSV:
  Option A — automatic: this script attempts to download from the known GitHub URL.
  Option B — manual: visit airisk.mit.edu, download the CSV, then run:
      python data/connectors/mit_risk_connector.py --file path/to/mit_air.csv

Usage:
    python data/connectors/mit_risk_connector.py
    python data/connectors/mit_risk_connector.py --file data/raw/mit_air.csv
    python data/connectors/mit_risk_connector.py --limit 50   # test run
"""

import argparse
import csv
import io
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from data.connectors.schema import classify_and_build_row, write_csv

# MIT AI Risk Repository — possible download URLs (the project has published data
# in several locations over time; we try each in order and fall back to --file).
CANDIDATE_URLS = [
    # Direct CSV from their website (added in later site versions)
    "https://airisk.mit.edu/static/data/airisk_database.csv",
    # OSF project — common academic data repository
    "https://osf.io/download/airisk/",
    # GitHub-hosted data (check https://github.com/mitre for latest)
    "https://raw.githubusercontent.com/mitre/airisk/main/airisk_database.csv",
    "https://raw.githubusercontent.com/mitre/airisk/main/data/airisk_database.csv",
]

# Fallback zip URL
GITHUB_ZIP_URL = "https://github.com/mitre/airisk/archive/refs/heads/main.zip"

OUTPUT_PATH = "data/datasets/mit_risk_classified.csv"

# MIT AIRR uses different column name conventions across versions.
# We probe for each field by priority order — first hit wins.
TITLE_COLS = ["Title", "Risk Title", "Risk_Title", "Name", "risk_title", "title"]
DESC_COLS = [
    "Description",
    "Risk Description",
    "Risk_Description",
    "Summary",
    "description",
]
ID_COLS = ["ID", "Risk ID", "Risk_ID", "id", "risk_id", "Index"]
URL_COLS = ["URL", "Source URL", "Source_URL", "Link", "url", "source_url"]
DOMAIN_COLS = ["Risk Domain", "Domain", "risk_domain", "Category"]
SUBDOMAIN_COLS = ["Sub-Domain", "Subdomain", "Sub_Domain", "sub_domain", "Risk Sub-Domain"]


def _pick_col(header: list, candidates: list) -> str:
    """Return the first candidate column name present in header, or ''."""
    for c in candidates:
        if c in header:
            return c
    return ""


def download_csv_direct() -> list[dict]:
    """Try each candidate URL until one returns a valid CSV."""
    for url in CANDIDATE_URLS:
        try:
            print(f"  Trying: {url}")
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            text = resp.text
            # Sanity check: real CSV should have commas and multiple lines
            if text.count(",") < 10 or text.count("\n") < 5:
                print(f"  Response doesn't look like CSV, skipping")
                continue
            rows = list(csv.DictReader(io.StringIO(text)))
            if rows:
                print(f"  Downloaded {len(rows)} rows from {url}")
                return rows
        except Exception as e:
            print(f"  Failed ({e})")
    raise RuntimeError("All candidate URLs failed")


def download_csv_zip() -> list[dict]:
    """Fallback: download entire repo zip and extract the CSV."""
    import zipfile

    print(f"Downloading MIT AIRR repo zip (fallback)...")
    resp = requests.get(GITHUB_ZIP_URL, timeout=120)
    resp.raise_for_status()
    print(f"  Downloaded {len(resp.content) / 1024:.0f} KB")

    import io as _io

    with zipfile.ZipFile(_io.BytesIO(resp.content)) as zf:
        csv_files = [n for n in zf.namelist() if n.endswith(".csv") and "data/" in n]
        if not csv_files:
            csv_files = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_files:
            raise RuntimeError("No CSV found in MIT AIRR zip archive")
        # Prefer the largest CSV (likely the main database)
        csv_files.sort(key=lambda n: zf.getinfo(n).file_size, reverse=True)
        chosen = csv_files[0]
        print(f"  Extracting: {chosen}")
        content = zf.read(chosen).decode("utf-8", errors="replace")

    rows = list(csv.DictReader(io.StringIO(content)))
    print(f"  Extracted {len(rows)} rows")
    return rows


def load_local_csv(path: str) -> list[dict]:
    """Load CSV from a local file path."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def build_text(row: dict, header: list) -> tuple[str, str, str, str]:
    """
    Extract (incident_id, title, description, source_url) from a row,
    using flexible column mapping.
    """
    id_col = _pick_col(header, ID_COLS)
    title_col = _pick_col(header, TITLE_COLS)
    desc_col = _pick_col(header, DESC_COLS)
    url_col = _pick_col(header, URL_COLS)
    domain_col = _pick_col(header, DOMAIN_COLS)
    subdomain_col = _pick_col(header, SUBDOMAIN_COLS)

    incident_id = row.get(id_col, "").strip() if id_col else ""
    title = row.get(title_col, "").strip() if title_col else ""
    description = row.get(desc_col, "").strip() if desc_col else ""
    source_url = row.get(url_col, "").strip() if url_col else ""

    # Enrich description with domain/subdomain taxonomy terms — improves keyword matching
    domain = row.get(domain_col, "").strip() if domain_col else ""
    subdomain = row.get(subdomain_col, "").strip() if subdomain_col else ""
    if domain or subdomain:
        taxonomy = " ".join(filter(None, [domain, subdomain]))
        description = f"{description} {taxonomy}".strip()

    return incident_id, title, description, source_url


def run(local_file: str = None, limit: int = None):
    print("=== MIT AI Risk Repository Connector ===")

    raw_rows = None

    if local_file:
        print(f"Loading from local file: {local_file}")
        raw_rows = load_local_csv(local_file)
    else:
        print("Attempting auto-download (trying known MIT AIRR URLs)...")
        try:
            raw_rows = download_csv_direct()
        except Exception as e:
            print(f"  All direct URLs failed, trying zip fallback...")
            try:
                raw_rows = download_csv_zip()
            except Exception as e2:
                print(f"  Zip download also failed: {e2}")
                print(
                    "\nAuto-download failed. Manual download instructions:\n"
                    "  1. Visit https://airisk.mit.edu/\n"
                    "  2. Download the full database CSV (look for 'Download' or 'Export')\n"
                    "  3. Or visit their OSF/Zenodo page linked from the site\n"
                    "  4. Run: python3 data/connectors/mit_risk_connector.py --file <path>\n"
                    "\n"
                    "Expected columns (any of these names work):\n"
                    f"  Title: {TITLE_COLS}\n"
                    f"  Description: {DESC_COLS}\n"
                )
                sys.exit(1)

    if not raw_rows:
        print("No rows loaded — nothing to classify.")
        return

    print(f"Total rows loaded: {len(raw_rows)}")

    header = list(raw_rows[0].keys())
    print(f"Detected columns: {header[:10]}{'...' if len(header) > 10 else ''}")

    # Validate column mapping
    id_col = _pick_col(header, ID_COLS)
    title_col = _pick_col(header, TITLE_COLS)
    desc_col = _pick_col(header, DESC_COLS)
    if not title_col and not desc_col:
        print(
            f"WARNING: Could not detect title or description columns.\n"
            f"  Available columns: {header}\n"
            f"  Add column names to TITLE_COLS / DESC_COLS in the connector."
        )

    items = raw_rows[:limit] if limit else raw_rows

    rows = []
    for i, raw in enumerate(items, 1):
        incident_id, title, description, source_url = build_text(raw, header)

        if not title and not description:
            continue

        # Generate a stable ID if the source doesn't provide one
        if not incident_id:
            incident_id = str(i)

        row = classify_and_build_row(
            incident_id=f"MIT-RISK-{incident_id}",
            title=title,
            description=description,
            source="mit_risk",
            source_url=source_url,
            source_type="incident",
        )
        rows.append(row)

        if i % 200 == 0:
            matched = sum(1 for r in rows if r is not None)
            print(f"  Classified {i}/{len(items)} — {matched} matched so far")

    from collections import Counter

    classified = write_csv(rows, OUTPUT_PATH)

    sig_counts = Counter()
    for r in classified:
        for sig in r["signatures"].split(","):
            sig_counts[sig.strip()] += 1

    print("\nSignature breakdown (MIT Risk):")
    for sig in sorted(sig_counts):
        print(f"  {sig}: {sig_counts[sig]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MIT AI Risk Repository connector")
    parser.add_argument(
        "--file", type=str, default=None,
        help="Path to local MIT AIRR CSV (if omitted, downloads from GitHub)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Process only first N rows (for testing)"
    )
    args = parser.parse_args()
    run(local_file=args.file, limit=args.limit)

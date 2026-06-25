"""
MIT AI Risk Repository connector.

Classifies risk entries from the MIT AIRR database (V4, Dec 2025) against
the nine Aletheia behavioral signatures.

Data source: https://airisk.mit.edu/risks#AI-Risk-Database
Download:    File → Download → CSV from the Google Sheet copy

Column layout (row 2 of CSV is the true header row):
  Title, QuickRef, Ev_ID, Paper_ID, Cat_ID, SubCat_ID, AddEv_ID,
  Category level, Risk category, Risk subcategory, Description,
  Additional ev., P.Def, p.AddEv, Entity, Intent, Timing, Domain, Sub-domain

Only rows where 'Category level' is 'Risk Category' or 'Risk Sub-Category'
are classified. 'Paper' and 'Additional evidence' rows are skipped.

Usage:
    python3 data/connectors/mit_risk_connector.py --file <path/to/mit_risk.csv>
    python3 data/connectors/mit_risk_connector.py --file <path> --limit 20
"""

import argparse
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from data.connectors.schema import classify_and_build_row, write_csv

OUTPUT_PATH = "data/datasets/mit_risk_classified.csv"

INCLUDE_LEVELS = {"Risk Category", "Risk Sub-Category"}

# Column indices (0-based) in the true header row (row index 2 of the CSV)
COL = {
    "title":        0,   # Paper title (source paper)
    "quickref":     1,   # Short citation key e.g. "Critch2023"
    "ev_id":        2,   # Evidence ID e.g. "01.01.00"
    "level":        7,   # "Risk Category" / "Risk Sub-Category" / etc.
    "risk_cat":     8,   # Risk category name
    "risk_subcat":  9,   # Risk subcategory name
    "description": 10,   # Risk description text
    "entity":      14,   # Causal entity (e.g. "2 - AI")
    "intent":      15,   # Causal intent (e.g. "2 - Unintentional")
    "timing":      16,   # Causal timing
    "domain":      17,   # Domain taxonomy (e.g. "6. Socioeconomic and Environmental")
    "subdomain":   18,   # Sub-domain taxonomy
}


def load(path: str) -> list[dict]:
    """
    Load the MIT AIRR CSV, skip the 2-row preamble, use row 2 as header,
    return only Risk Category and Risk Sub-Category rows.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        all_rows = list(csv.reader(f))

    header = all_rows[2]
    data = all_rows[3:]

    # Validate expected column count
    if len(header) < 19:
        print(f"WARNING: Expected >=19 columns, got {len(header)}. Column mapping may be off.")
        print(f"  Detected headers: {header}")

    risk_rows = []
    for row in data:
        # Pad short rows
        while len(row) < 19:
            row.append("")
        level = row[COL["level"]].strip()
        if level in INCLUDE_LEVELS:
            risk_rows.append(row)

    return risk_rows


def build_text(row: list) -> tuple[str, str, str, str]:
    """Return (ev_id, title_text, description_text, source_ref)."""
    ev_id = row[COL["ev_id"]].strip()
    risk_cat = row[COL["risk_cat"]].strip()
    risk_subcat = row[COL["risk_subcat"]].strip()
    description = row[COL["description"]].strip()
    entity = row[COL["entity"]].strip()
    intent = row[COL["intent"]].strip()
    domain = row[COL["domain"]].strip()
    subdomain = row[COL["subdomain"]].strip()
    quickref = row[COL["quickref"]].strip()
    paper_title = row[COL["title"]].strip()

    # Title: prefer sub-category name when present, fall back to category
    title = risk_subcat if risk_subcat else risk_cat

    # Enrich description with all taxonomy fields for better keyword coverage
    taxonomy_parts = [p for p in [domain, subdomain, entity, intent] if p]
    full_desc = " | ".join(filter(None, [description] + taxonomy_parts))

    source_ref = f"{quickref} ({paper_title})" if quickref else paper_title

    return ev_id, title, full_desc, source_ref


def run(local_file: str, limit: int = None):
    if not local_file:
        print(
            "Error: --file is required for the MIT Risk connector.\n"
            "Download the CSV from: https://airisk.mit.edu/risks#AI-Risk-Database\n"
            "  1. Click the Google Sheets link → make a copy\n"
            "  2. File → Download → Comma Separated Values\n"
            "  3. Run: python3 data/connectors/mit_risk_connector.py --file <path>"
        )
        sys.exit(1)

    print("=== MIT AI Risk Repository Connector ===")
    print(f"Loading: {local_file}")

    risk_rows = load(local_file)
    print(f"Risk entries loaded (Category + Sub-Category): {len(risk_rows)}")

    if limit:
        risk_rows = risk_rows[:limit]
        print(f"Limiting to first {limit} entries")

    rows = []
    for i, raw in enumerate(risk_rows, 1):
        ev_id, title, description, source_ref = build_text(raw)

        if not title and not description:
            continue

        row = classify_and_build_row(
            incident_id=f"MIT-RISK-{ev_id}",
            title=title,
            description=description,
            source="mit_risk",
            source_url=f"https://airisk.mit.edu/risks (ref: {source_ref})",
            source_type="incident",
        )
        rows.append(row)

        if i % 300 == 0:
            matched = sum(1 for r in rows if r is not None)
            print(f"  Classified {i}/{len(risk_rows)} — {matched} matched so far")

    classified = write_csv(rows, OUTPUT_PATH)

    sig_counts = Counter()
    for r in classified:
        for sig in r["signatures"].split(","):
            sig_counts[sig.strip()] += 1

    print("\nSignature breakdown (MIT Risk):")
    for sig in sorted(sig_counts):
        print(f"  {sig}: {sig_counts[sig]}")

    total = len(risk_rows)
    matched = len(classified)
    print(f"\nCoverage: {matched}/{total} entries matched ({matched/total*100:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MIT AI Risk Repository connector")
    parser.add_argument("--file", type=str, required=True, help="Path to MIT AIRR CSV")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N entries")
    args = parser.parse_args()
    run(local_file=args.file, limit=args.limit)

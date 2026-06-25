"""
AVID (AI Vulnerability Database) connector.

Downloads the entire avid-db repo as a single zip archive, extracts report
JSON files locally, and classifies each against the 8 Aletheia behavioral
signatures. Using a zip download avoids making 1700+ individual HTTP requests
which causes GitHub to reset the connection.

Data source: https://github.com/avidml/avid-db

Usage:
    python data/connectors/avid_connector.py
    python data/connectors/avid_connector.py --limit 20   # test run
"""

import argparse
import io
import json
import os
import sys
import zipfile
from collections import Counter

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from data.connectors.schema import classify_and_build_row, write_csv

ZIP_URL = "https://github.com/avidml/avid-db/archive/refs/heads/main.zip"
OUTPUT_PATH = "data/datasets/avid_classified.csv"


def download_and_extract() -> dict:
    """Download repo zip and return {path: parsed_json} for all report files."""
    print("Downloading avid-db archive (single request)...")
    resp = requests.get(ZIP_URL, timeout=120)
    resp.raise_for_status()
    print(f"  Downloaded {len(resp.content) / 1024:.0f} KB")

    reports = {}
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in zf.namelist():
            # reports live under avid-db-main/reports/<year>/AVID-*.json
            if "/reports/" in name and name.endswith(".json"):
                try:
                    data = json.loads(zf.read(name))
                    if isinstance(data, dict):
                        reports[name] = data
                except Exception:
                    pass
    print(f"  Extracted {len(reports)} report JSON files")
    return reports


def extract_fields(report: dict, path: str) -> tuple:
    """Extract id, title, description, url from AVID JSON structure."""
    report_id = (
        (report.get("metadata") or {}).get("report_id")
        or os.path.basename(path).replace(".json", "")
    )

    artifacts = (report.get("affects") or {}).get("artifacts", [])
    artifact_name = artifacts[0].get("name", "") if artifacts else ""
    problem_desc = (
        (report.get("problemtype") or {})
        .get("description", {})
        .get("value", "")
    )
    title = f"{artifact_name}: {problem_desc}" if artifact_name else problem_desc
    if not title:
        title = report_id

    desc_val = report.get("description", {})
    description = desc_val.get("value", "") if isinstance(desc_val, dict) else str(desc_val or "")

    impact = (report.get("impact") or {}).get("avid") or {}
    risk_domains = " ".join(impact.get("risk_domain", []))
    sep_views = " ".join(impact.get("sep_view", []))
    full_text = f"{description} {risk_domains} {sep_views}".strip()

    refs = report.get("references") or []
    source_url = next(
        (r["url"] for r in refs if isinstance(r, dict) and r.get("type") == "source"), ""
    ) or f"https://avidml.org/database/{report_id}"

    return report_id, title.strip()[:300], full_text.strip(), source_url


def run(limit: int = None):
    print("=== AVID Connector ===")
    reports = download_and_extract()

    items = list(reports.items())
    if limit:
        items = items[:limit]
        print(f"Limiting to first {limit} reports")

    rows = []
    for i, (path, report) in enumerate(items, 1):
        report_id, title, description, source_url = extract_fields(report, path)
        if not description and not title:
            continue

        row = classify_and_build_row(
            incident_id=f"AVID-{report_id}",
            title=title,
            description=description,
            source="avid",
            source_url=source_url,
            source_type="incident",
        )
        rows.append(row)

        if i % 100 == 0:
            matched = sum(1 for r in rows if r is not None)
            print(f"  Classified {i}/{len(items)} — {matched} matched so far")

    classified = write_csv(rows, OUTPUT_PATH)

    sig_counts = Counter()
    for r in classified:
        for sig in r["signatures"].split(","):
            sig_counts[sig.strip()] += 1

    print("\nSignature breakdown (AVID):")
    for sig in sorted(sig_counts):
        print(f"  {sig}: {sig_counts[sig]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Process only first N reports (for testing)"
    )
    args = parser.parse_args()
    run(limit=args.limit)

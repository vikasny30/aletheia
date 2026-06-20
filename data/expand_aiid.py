"""
Aletheia — AIID Expansion Script
=================================
Fetches incidents from the AI Incident Database (AIID) GraphQL API, classifies
each against all 8 behavioral signatures using keyword heuristics, and saves
results to data/aiid_expanded_annotated.csv.

Handles pagination, exponential-backoff retry on rate limits and server errors,
and resume support via --offset. Re-running skips incident_ids already present
in the output file or in data/aiid_300_annotated.csv.

Usage:
    python data/expand_aiid.py --limit 500
    python data/expand_aiid.py --limit 200 --signatures s3 s4 s5
    python data/expand_aiid.py --offset 300 --limit 200    # resume from offset
    python data/expand_aiid.py --dry-run --limit 50        # preview, no write
"""

import os
import sys
import csv
import time
import argparse
import datetime

import requests
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from benchmarks.utils import classify_incident

AIID_GRAPHQL_URL = "https://incidentdatabase.ai/api/graphql"

AIID_QUERY = """
query GetIncidents($limit: Int, $skip: Int) {
  incidents(limit: $limit, skip: $skip, sort: {incident_id: ASC}) {
    incident_id
    title
    date
    reports {
      title
      text
      url
    }
  }
}
"""

DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "aiid_expanded_annotated.csv"
)

CSV_COLUMNS = [
    "incident_id", "title", "description", "signatures", "source",
    "source_url", "annotation_confidence", "annotated_by", "date_annotated",
]

BACKOFF_DELAYS = [1, 2, 4, 8]


# ── API layer ──────────────────────────────────────────────────────────────────

def fetch_aiid_page(limit: int, skip: int, session: requests.Session,
                    timeout: int = 30) -> list:
    """
    Fetch one page of AIID incidents via GraphQL. Returns [] on any failure.
    Retries up to 4 times with exponential backoff on 429 or 5xx responses.
    """
    payload = {
        "query": AIID_QUERY,
        "variables": {"limit": limit, "skip": skip},
    }
    last_error = None

    for delay in BACKOFF_DELAYS:
        try:
            resp = session.post(AIID_GRAPHQL_URL, json=payload, timeout=timeout)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    return data.get("data", {}).get("incidents", [])
                except (ValueError, AttributeError) as e:
                    print(
                        f"  [WARN] Malformed JSON at skip={skip}: {e} "
                        f"(response preview: {resp.text[:200]})",
                        file=sys.stderr,
                    )
                    return []
            elif resp.status_code == 429:
                print(
                    f"  [WARN] Rate limited (skip={skip}), retrying in {delay}s",
                    file=sys.stderr,
                )
                time.sleep(delay)
                last_error = f"HTTP 429"
            else:
                print(
                    f"  [WARN] HTTP {resp.status_code} at skip={skip}, "
                    f"retrying in {delay}s",
                    file=sys.stderr,
                )
                time.sleep(delay)
                last_error = f"HTTP {resp.status_code}"
        except (requests.ConnectionError, requests.Timeout) as e:
            print(
                f"  [WARN] Network error at skip={skip}: {e}, retrying in {delay}s",
                file=sys.stderr,
            )
            time.sleep(delay)
            last_error = str(e)
        except Exception as e:
            print(f"  [WARN] Unexpected error at skip={skip}: {e}", file=sys.stderr)
            return []

    print(
        f"  [ERROR] Giving up on skip={skip} after retries: {last_error}",
        file=sys.stderr,
    )
    return []


def fetch_all_incidents(limit: int = 500, offset: int = 0,
                        session: requests.Session = None,
                        page_size: int = 100) -> list:
    """
    Paginate through AIID from offset, fetching up to limit incidents total.
    Stops early on 3 consecutive empty pages (end of database or API issue).
    """
    if session is None:
        session = requests.Session()

    all_incidents = []
    consecutive_empty = 0
    skip = offset
    remaining = limit

    pbar = tqdm(total=limit, desc="Fetching AIID incidents", unit="incidents")

    while remaining > 0:
        batch_size = min(page_size, remaining)
        page = fetch_aiid_page(batch_size, skip, session)

        if not page:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                print(
                    "\n  [INFO] 3 consecutive empty pages — "
                    "reached end of AIID or API issue",
                    file=sys.stderr,
                )
                break
            skip += batch_size
            continue

        consecutive_empty = 0
        all_incidents.extend(page)
        fetched = len(page)
        pbar.update(fetched)
        skip += fetched
        remaining -= fetched

        if remaining > 0:
            time.sleep(0.5)

    pbar.close()
    return all_incidents


# ── Classification layer ───────────────────────────────────────────────────────

def extract_incident_text(raw_incident: dict) -> str:
    """Combine title + report titles and truncated report texts for classification."""
    parts = [raw_incident.get("title", "") or ""]
    for report in raw_incident.get("reports", []) or []:
        if report.get("title"):
            parts.append(report["title"])
        text = report.get("text") or ""
        if text:
            parts.append(text[:500])
    return " ".join(filter(None, parts))


def incident_to_row(raw_incident: dict, target_sigs: list,
                    min_confidence: float = 0.3):
    """
    Classify one incident and return a CSV-schema dict, or None if nothing qualifies.
    target_sigs: if non-empty, restrict to only these signature IDs (uppercase).
    """
    text = extract_incident_text(raw_incident)
    scores = classify_incident(text, threshold=min_confidence)

    if target_sigs:
        scores = {k: v for k, v in scores.items() if k in target_sigs}

    if not scores:
        return None

    reports = raw_incident.get("reports", []) or []
    source_url = reports[0].get("url", "") if reports else ""

    sig_str = ",".join(sorted(scores.keys()))
    avg_confidence = round(sum(scores.values()) / len(scores), 3)

    return {
        "incident_id": str(raw_incident.get("incident_id", "")),
        "title": (raw_incident.get("title", "") or "")[:255],
        "description": text[:500],
        "signatures": sig_str,
        "source": "AIID",
        "source_url": source_url,
        "annotation_confidence": avg_confidence,
        "annotated_by": "keyword_classifier_v1",
        "date_annotated": datetime.date.today().isoformat(),
    }


# ── I/O layer ─────────────────────────────────────────────────────────────────

def load_existing_ids(output_path: str, extra_paths: list = None) -> set:
    """
    Return set of incident_ids already written to output_path (and any extra_paths).
    Supports resuming interrupted runs and avoids overwriting manual annotations.
    """
    ids = set()
    for path in [output_path] + (extra_paths or []):
        if not os.path.isfile(path):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    iid = str(row.get("incident_id", "")).strip()
                    if iid:
                        ids.add(iid)
        except Exception as e:
            print(
                f"  [WARN] Could not read existing IDs from {path}: {e}",
                file=sys.stderr,
            )
    return ids


def save_to_csv(rows: list, output_path: str) -> None:
    """
    Append rows to output_path then deduplicate by incident_id, keeping the row
    with the highest annotation_confidence. Creates parent directory if needed.
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    existing_rows = []
    if os.path.isfile(output_path):
        try:
            with open(output_path, newline="", encoding="utf-8") as f:
                existing_rows = list(csv.DictReader(f))
        except Exception:
            pass

    all_rows = existing_rows + rows
    seen = {}
    for row in all_rows:
        iid = str(row.get("incident_id", "")).strip()
        conf = float(row.get("annotation_confidence", 0) or 0)
        if iid not in seen or conf > float(seen[iid].get("annotation_confidence", 0) or 0):
            seen[iid] = row

    deduped = list(seen.values())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(deduped)

    delta = len(deduped) - len(existing_rows)
    print(f"  Saved {len(deduped)} incidents to {output_path} ({delta:+d} new)")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch and classify AIID incidents for Aletheia validation"
    )
    parser.add_argument(
        "--limit", type=int, default=500,
        help="Max incidents to fetch (default: 500)",
    )
    parser.add_argument(
        "--offset", type=int, default=0,
        help="Skip first N incidents for resume support (default: 0)",
    )
    parser.add_argument(
        "--signatures", nargs="+",
        choices=["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"],
        default=[],
        help="Filter to specific signatures (default: all)",
    )
    parser.add_argument(
        "--min-confidence", type=float, default=0.3,
        help="Minimum classifier confidence to include (default: 0.3)",
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT,
        help="Output CSV path (default: data/aiid_expanded_annotated.csv)",
    )
    parser.add_argument(
        "--page-size", type=int, default=100,
        help="Incidents per API request (default: 100)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview classification counts without writing CSV",
    )
    args = parser.parse_args()

    target_sigs = [s.upper() for s in args.signatures]
    aiid_300_path = os.path.join(os.path.dirname(args.output), "aiid_300_annotated.csv")
    existing_ids = load_existing_ids(args.output, extra_paths=[aiid_300_path])
    if existing_ids:
        print(f"  Resuming: {len(existing_ids)} incidents already processed")

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    print(f"\n{'='*60}")
    print(f"AIID EXPANSION — Aletheia Validation Pipeline")
    print(
        f"Limit: {args.limit} | Offset: {args.offset} | "
        f"Signatures: {target_sigs or 'all'}"
    )
    print(f"{'='*60}\n")

    incidents = fetch_all_incidents(
        limit=args.limit,
        offset=args.offset,
        session=session,
        page_size=args.page_size,
    )

    print(f"\n  Fetched {len(incidents)} incidents, classifying...")

    new_rows = []
    skipped = 0
    for inc in tqdm(incidents, desc="Classifying", unit="incidents"):
        iid = str(inc.get("incident_id", ""))
        if iid in existing_ids:
            skipped += 1
            continue
        row = incident_to_row(inc, target_sigs, args.min_confidence)
        if row:
            new_rows.append(row)

    sig_counts = {}
    for row in new_rows:
        for sig in row["signatures"].split(","):
            sig_counts[sig] = sig_counts.get(sig, 0) + 1

    print(f"\n  Classification complete:")
    print(f"    New matching rows: {len(new_rows)}")
    print(f"    Skipped (already processed): {skipped}")
    print(f"    Per-signature counts: {sig_counts}")

    if args.dry_run:
        print("\n  [DRY RUN] No file written.")
    elif new_rows:
        save_to_csv(new_rows, args.output)
    else:
        print("  No new matching incidents to save.")

"""
Aletheia Validation Status — Gap Tracker CLI
============================================
Reads all annotated CSV files in the data/ directory, deduplicates by
incident_id, and reports per-signature counts toward the paper validation target.

Usage:
    python data/validation_status.py                    # default 40-incident target
    python data/validation_status.py --target 35        # custom target
    python data/validation_status.py --json             # JSON output
    python data/validation_status.py --data-dir /path   # custom data directory
"""

import os
import sys
import glob
import json
import argparse
import datetime

import pandas as pd

ALL_SIGNATURES = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]

SIGNATURE_NAMES = {
    "S1": "Confidence Without Grounding",
    "S2": "Credibility Surface Exploitation",
    "S3": "Scope Creep Beyond Mandate",
    "S4": "Context Blindness",
    "S5": "No Safe State Fallback",
    "S6": "Vulnerability Signal Blindness",
    "S7": "Institutional Credibility Amplification",
    "S8": "Feedback Loop Absence",
}

REQUIRED_COLUMNS = {
    "incident_id", "title", "description", "signatures",
    "source", "source_url", "annotation_confidence",
    "annotated_by", "date_annotated",
}


def find_csv_files(data_dir: str) -> list:
    """Return sorted list of CSV files directly inside data_dir (non-recursive)."""
    pattern = os.path.join(data_dir, "*.csv")
    return sorted(glob.glob(pattern))


def load_and_merge(csv_paths: list) -> pd.DataFrame:
    """
    Load and merge CSV files, validating schema and deduplicating on incident_id.
    Keeps highest annotation_confidence when the same incident_id appears in
    multiple files. Skips files with missing required columns with a warning.
    """
    frames = []
    for path in csv_paths:
        try:
            df = pd.read_csv(path, dtype={"incident_id": str})
        except Exception as e:
            print(f"  [WARN] Could not read {os.path.basename(path)}: {e}",
                  file=sys.stderr)
            continue

        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            print(
                f"  [WARN] Skipping {os.path.basename(path)}: "
                f"missing columns {sorted(missing)}",
                file=sys.stderr,
            )
            continue

        df["incident_id"] = df["incident_id"].astype(str).str.strip()
        df["annotation_confidence"] = pd.to_numeric(
            df["annotation_confidence"], errors="coerce"
        ).fillna(0.0)
        frames.append(df)

    if not frames:
        return pd.DataFrame(columns=list(REQUIRED_COLUMNS))

    merged = pd.concat(frames, ignore_index=True)
    merged = (
        merged.sort_values("annotation_confidence", ascending=False)
        .drop_duplicates(subset="incident_id", keep="first")
        .reset_index(drop=True)
    )
    return merged


def expand_signatures(df: pd.DataFrame) -> pd.DataFrame:
    """
    Explode the comma-separated 'signatures' column into one row per
    (incident_id, signature) pair. Unknown signature IDs are filtered out.
    Returns DataFrame with columns: incident_id, signature, annotation_confidence.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["incident_id", "signature", "annotation_confidence"]
        )

    work = df[["incident_id", "signatures", "annotation_confidence"]].copy()
    work["signatures"] = work["signatures"].fillna("").astype(str)
    work["signature"] = work["signatures"].str.split(",")
    work = work.explode("signature")
    work["signature"] = work["signature"].str.strip().str.upper()
    work = work[work["signature"].isin(ALL_SIGNATURES)].reset_index(drop=True)
    return work[["incident_id", "signature", "annotation_confidence"]]


def compute_gap_table(df_exploded: pd.DataFrame, target: int) -> list:
    """
    For each signature S1-S8 compute count, gap, pct_complete, and status.
    Status thresholds: ON_TRACK >=90%, AT_RISK >=60%, NEEDS_SUPPLEMENT <60%.
    """
    counts = {}
    if not df_exploded.empty:
        counts = (
            df_exploded.groupby("signature")["incident_id"]
            .nunique()
            .to_dict()
        )

    rows = []
    for sig in ALL_SIGNATURES:
        count = counts.get(sig, 0)
        gap = max(0, target - count)
        pct = round(count / target * 100, 1) if target > 0 else 0.0

        if count >= target * 0.9:
            status = "ON_TRACK"
        elif count >= target * 0.6:
            status = "AT_RISK"
        else:
            status = "NEEDS_SUPPLEMENT"

        rows.append({
            "signature": sig,
            "name": SIGNATURE_NAMES[sig],
            "count": count,
            "target": target,
            "gap": gap,
            "pct_complete": pct,
            "status": status,
        })
    return rows


def print_progress_table(gap_table: list, total_unique: int,
                         csv_files: list) -> None:
    """Print formatted progress table to stdout."""
    target = gap_table[0]["target"]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*80}")
    print(f"  ALETHEIA — VALIDATION STATUS  |  Target: {target} incidents/signature")
    print(f"  {now}  |  Sources: {len(csv_files)} CSV file(s)  |  Total unique: {total_unique}")
    print(f"{'='*80}")
    print(f"  {'Sig':<4} {'Name':<42} {'Count':>6} {'Gap':>5} {'Done%':>6}  Status")
    print(f"  {'─'*4} {'─'*42} {'─'*6} {'─'*5} {'─'*6}  {'─'*18}")

    symbols = {
        "ON_TRACK": "✓ ON_TRACK",
        "AT_RISK": "~ AT_RISK",
        "NEEDS_SUPPLEMENT": "✗ NEEDS_SUPPLEMENT",
    }

    for row in gap_table:
        print(
            f"  {row['signature']:<4} {row['name']:<42} "
            f"{row['count']:>6} {row['gap']:>5} {row['pct_complete']:>5.1f}%  "
            f"{symbols[row['status']]}"
        )
    print(f"{'='*80}\n")


def to_json_output(gap_table: list, total_unique: int, csv_files: list) -> dict:
    """Return gap table + metadata as a JSON-serializable dict."""
    return {
        "generated_at": datetime.datetime.now().isoformat(),
        "total_unique_incidents": total_unique,
        "csv_files": [os.path.basename(f) for f in csv_files],
        "signatures": gap_table,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Aletheia validation status — gap tracker toward paper target"
    )
    parser.add_argument(
        "--target", type=int, default=40,
        help="Incident count target per signature (default: 40)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON instead of formatted table",
    )
    parser.add_argument(
        "--data-dir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Directory containing annotated CSV files",
    )
    args = parser.parse_args()

    data_dir = args.data_dir
    if not os.path.isdir(data_dir):
        print(f"No data directory found at {data_dir}", file=sys.stderr)
        sys.exit(0)

    csv_files = find_csv_files(data_dir)
    if not csv_files:
        print(
            "No annotated CSV files found. "
            "Run expand_aiid.py or supplement_sources.py first.",
            file=sys.stderr,
        )
        sys.exit(0)

    df = load_and_merge(csv_files)
    df_exploded = expand_signatures(df)
    gap_table = compute_gap_table(df_exploded, target=args.target)
    total_unique = len(df)

    if args.json:
        print(json.dumps(to_json_output(gap_table, total_unique, csv_files), indent=2))
    else:
        print_progress_table(gap_table, total_unique, csv_files)

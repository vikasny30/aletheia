"""
Shared schema and normalization utilities for external dataset connectors.

All connectors write to the same CSV format as the existing AIID annotated files:
  incident_id, title, description, signatures, source, source_url,
  annotation_confidence, annotated_by, date_annotated
"""

import csv
import datetime
import os
import sys

# Add repo root to path so we can import benchmarks.utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from benchmarks.utils import classify_incident

FIELDNAMES = [
    "incident_id",
    "title",
    "description",
    "signatures",
    "source",
    "source_type",   # "incident" (AIID, AVID, MIT Risk) or "technique" (MITRE ATLAS)
    "source_url",
    "annotation_confidence",
    "annotated_by",
    "date_annotated",
]

TODAY = datetime.date.today().isoformat()


def classify_and_build_row(
    incident_id: str,
    title: str,
    description: str,
    source: str,
    source_url: str = "",
    source_type: str = "incident",
) -> dict:
    """
    Run keyword classifier on title + description, return a fully populated row
    matching the shared schema. Returns None if no signatures are detected.
    """
    text = f"{title}. {description}"
    scores = classify_incident(text)
    if not scores:
        return None

    # Pick the highest-confidence signature(s) — same logic as existing annotators
    top_sig = max(scores, key=scores.get)
    confidence = round(scores[top_sig], 3)

    # If multiple sigs score equally high, include all above threshold
    all_sigs = ",".join(sig for sig, sc in sorted(scores.items()) if sc >= 0.3)

    return {
        "incident_id": incident_id,
        "title": title[:300],
        "description": description[:1000],
        "signatures": all_sigs,
        "source": source,
        "source_type": source_type,
        "source_url": source_url,
        "annotation_confidence": confidence,
        "annotated_by": "keyword_classifier_v1",
        "date_annotated": TODAY,
    }


def write_csv(rows: list, output_path: str):
    """Write normalized rows to CSV, skipping unclassified entries."""
    classified = [r for r in rows if r is not None]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(classified)
    print(f"Wrote {len(classified)} classified rows → {output_path}")
    print(f"  ({len(rows) - len(classified)} entries had no signature match)")
    return classified

"""
Aletheia — Results Aggregator
==============================
Reads all benchmark JSON files from data/results/, merges runs per signature
per model, computes detection rates with 95% Wilson confidence intervals,
and outputs a publication-ready comparison table.

Usage:
    python data/aggregate_results.py
    python data/aggregate_results.py --json          # machine-readable output
    python data/aggregate_results.py --latex         # LaTeX table for paper
    python data/aggregate_results.py --min-runs 50   # exclude low-n results
"""

import os
import sys
import json
import math
import argparse
import glob
from collections import defaultdict

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

SIG_NAMES = {
    "s1": "Confidence Without Grounding",
    "s2": "Credibility Surface Exploitation",
    "s3": "Scope Creep Beyond Mandate",
    "s4": "Context Blindness",
    "s5": "No Safe State Fallback",
    "s6": "Vulnerability Signal Blindness",
    "s7": "Institutional Credibility Amplification",
    "s8": "Feedback Loop Absence",
}

MODEL_DISPLAY = {
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "claude": "Claude Sonnet 4.6",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "haiku": "Claude Haiku 4.5",
    "gpt-4o": "GPT-4o",
    "gpt4o": "GPT-4o",
}

DETECTION_KEY_PRIORITY = [
    "signature_detected_pct",
    "context_blind_pct",
    "authority_bypass_pct",
    "scope_creep_pct",
    "amplification_detected_pct",
    "vulnerability_blind_pct",
    "s1_signature_detected_pct",
    "s2_signature_detected_pct",
    "s3_signature_detected_pct",
    "s4_signature_detected_pct",
    "s5_signature_detected_pct",
    "s6_signature_detected_pct",
    "s7_signature_detected_pct",
    "s8_signature_detected_pct",
]


def wilson_ci(p: float, n: int, z: float = 1.96) -> tuple:
    """95% Wilson score confidence interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = p / 100.0
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    lo = max(0.0, (center - margin) * 100)
    hi = min(100.0, (center + margin) * 100)
    return (round(lo, 1), round(hi, 1))


def find_detection_pct(stats: dict):
    for key in DETECTION_KEY_PRIORITY:
        if key in stats:
            return stats[key]
    # Fallback: first key ending in _pct
    for key, val in stats.items():
        if key.endswith("_pct") and isinstance(val, (int, float)):
            return val
    return None


def load_all_results(results_dir: str) -> dict:
    """
    Returns nested dict: {sig -> {model_canonical -> {"detected": int, "total": int}}}
    Merges across all JSON files; takes most-recent file per sig/model if duplicates.
    """
    stats_files = sorted(glob.glob(os.path.join(results_dir, "*_stats_*.json")))
    if not stats_files:
        # Fallback: try all json files with by_model key
        stats_files = sorted(glob.glob(os.path.join(results_dir, "*.json")))
        stats_files = [f for f in stats_files if "run_summary" not in f]

    # sig -> model -> list of (timestamp, detected_count, total)
    raw = defaultdict(lambda: defaultdict(list))

    for fpath in stats_files:
        fname = os.path.basename(fpath)
        # Infer sig from filename prefix
        sig = None
        for s in SIG_NAMES:
            if fname.startswith(s):
                sig = s
                break
        if sig is None:
            continue

        try:
            with open(fpath) as f:
                d = json.load(f)
        except Exception:
            continue

        by_model = d.get("by_model", {})
        if not by_model:
            continue

        # Extract timestamp from filename for recency ordering
        parts = fname.replace(".json", "").split("_")
        timestamp = parts[-1] if parts else "0"

        for model_raw, stats in by_model.items():
            canonical = MODEL_DISPLAY.get(model_raw, model_raw)
            pct = find_detection_pct(stats)
            total = stats.get("total", 0)
            if pct is None or total == 0:
                continue
            detected = round(pct / 100 * total)
            raw[sig][canonical].append((timestamp, detected, total))

    # Aggregate: sum all runs per sig/model (more data = better CI)
    aggregated = {}
    for sig, models in raw.items():
        aggregated[sig] = {}
        for model, runs in models.items():
            total_detected = sum(r[1] for r in runs)
            total_n = sum(r[2] for r in runs)
            aggregated[sig][model] = {
                "detected": total_detected,
                "total": total_n,
                "pct": round(total_detected / total_n * 100, 1) if total_n else 0,
            }

    return aggregated


def print_table(aggregated: dict, min_runs: int = 0):
    # Collect all models seen
    all_models = set()
    for models in aggregated.values():
        all_models.update(models.keys())

    model_order = ["Claude Sonnet 4.6", "Claude Haiku 4.5", "GPT-4o"]
    models_present = [m for m in model_order if m in all_models]
    models_present += [m for m in sorted(all_models) if m not in model_order]

    col_w = 16
    name_w = 38
    print(f"\n{'='*85}")
    print(f"ALETHEIA — Behavioral Signature Detection Rates")
    print(f"{'='*85}")
    header = f"{'Sig':<4} {'Signature Name':<{name_w}}"
    for m in models_present:
        short = m.replace("Claude ", "").replace(" 4.6","").replace(" 4.5","")
        header += f"  {short:>{col_w}}"
    print(header)
    print("─" * 85)

    for sig in ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]:
        name = SIG_NAMES.get(sig, sig)
        row = f"{sig.upper():<4} {name:<{name_w}}"
        for model in models_present:
            data = aggregated.get(sig, {}).get(model)
            if data is None or data["total"] < min_runs:
                row += f"  {'—':>{col_w}}"
            else:
                lo, hi = wilson_ci(data["pct"], data["total"])
                cell = f"{data['pct']:.0f}% [{lo:.0f}-{hi:.0f}]"
                row += f"  {cell:>{col_w}}"
        print(row)

    print("─" * 85)
    print("Format: detection% [95% CI lower-upper]")

    # Sample sizes
    print(f"\nSample sizes (n per model per signature):")
    for sig in ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]:
        counts = []
        for model in models_present:
            data = aggregated.get(sig, {}).get(model)
            n = data["total"] if data else 0
            short = model.replace("Claude ", "").replace(" 4.6","").replace(" 4.5","")
            counts.append(f"{short}={n}")
        print(f"  {sig.upper()}: {', '.join(counts)}")


def print_latex(aggregated: dict, min_runs: int = 0):
    all_models = set()
    for models in aggregated.values():
        all_models.update(models.keys())
    model_order = ["Claude Sonnet 4.6", "Claude Haiku 4.5", "GPT-4o"]
    models_present = [m for m in model_order if m in all_models]

    col_spec = "l l " + " ".join(["r"] * len(models_present))
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\small")
    print(f"\\begin{{tabular}}{{{col_spec}}}")
    print(r"\toprule")
    header_cols = " & ".join(["Sig", "Signature"] + [m.replace(" ", "~") for m in models_present])
    print(f"{header_cols} \\\\")
    print(r"\midrule")

    for sig in ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]:
        name = SIG_NAMES.get(sig, sig)
        cells = [sig.upper(), name]
        for model in models_present:
            data = aggregated.get(sig, {}).get(model)
            if data is None or data["total"] < min_runs:
                cells.append("—")
            else:
                lo, hi = wilson_ci(data["pct"], data["total"])
                cells.append(f"{data['pct']:.0f}\\% [{lo:.0f}--{hi:.0f}]")
        print(" & ".join(cells) + r" \\")

    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\caption{Behavioral signature detection rates (\%) with 95\% Wilson confidence intervals.")
    print(r"$n=100$ runs per model per signature.}")
    print(r"\label{tab:detection-rates}")
    print(r"\end{table}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate Aletheia benchmark results")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--latex", action="store_true", help="Output LaTeX table")
    parser.add_argument("--min-runs", type=int, default=0,
                        help="Minimum runs to include a result (default: 0)")
    parser.add_argument("--results-dir", default=RESULTS_DIR,
                        help=f"Results directory (default: {RESULTS_DIR})")
    args = parser.parse_args()

    aggregated = load_all_results(args.results_dir)

    if args.json:
        print(json.dumps(aggregated, indent=2))
    elif args.latex:
        print_latex(aggregated, min_runs=args.min_runs)
    else:
        print_table(aggregated, min_runs=args.min_runs)

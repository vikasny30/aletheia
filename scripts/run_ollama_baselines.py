"""
Run all 9 Aletheia signatures against a local Ollama model and print results.
Uses the private probe corpus from aletheia-probes/.
Usage: python3 scripts/run_ollama_baselines.py [model] [n_probes]
  model    — ollama model name (default: llama3.3)
  n_probes — probes per signature (default: 20)
"""

import json
import os
import sys
import time

PRIVATE_CORPUS = os.path.expanduser("~/Downloads/aletheia-probes")
sys.path.insert(0, PRIVATE_CORPUS)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.runner import run_signature, ALL_SIGNATURE_IDS
import prompts as private_prompts

MODEL = sys.argv[1] if len(sys.argv) > 1 else "llama3.3"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 20

model_config = {
    "provider": "ollama",
    "model_id": MODEL,
    "api_key": "",
    "base_url": "http://localhost:11434",
    "max_tokens": 512,
}

def get_probes(sig_id: str, n: int) -> list:
    sig = private_prompts.SIGNATURES.get(sig_id, {})
    probes = sig.get("probes", [])
    return probes[:n]

print(f"\nAletheia baseline run — {MODEL} — {N} probes/sig\n{'='*55}")

results = {}
for sig_id in ALL_SIGNATURE_IDS:
    probes = get_probes(sig_id, N)
    t0 = time.time()
    r = run_signature(sig_id, model_config, len(probes), custom_probes=probes)
    elapsed = round(time.time() - t0, 1)
    results[sig_id] = r["detection_rate"]
    ci = f"[{round(r['ci_95_lo']*100,1)}–{round(r['ci_95_hi']*100,1)}]"
    flag = " ⚠" if r["detection_pct"] > 30 else ""
    errors = f"  ({r['n_errors']} errors)" if r["n_errors"] else ""
    print(f"  {sig_id}  {r['detection_pct']:5.1f}%  CI95={ci:<16} {elapsed:5.1f}s{flag}{errors}")

print(f"\n{'='*55}")
print(f'Paste into BASELINES["{MODEL}"] in api/runner.py:')
print(f'    "{MODEL}": {{')
for sig_id, rate in results.items():
    print(f'        "{sig_id}": {rate},')
print("    },")

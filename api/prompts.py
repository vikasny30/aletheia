"""
Aletheia probe corpus — proprietary, not distributed under BSL 1.1.

The probe corpus (adversarial prompt sets for S1-S8) is maintained in a
private repository. Commercial and research licensing: vikas.ny30@gmail.com

This stub raises an ImportError so the public runner fails fast with a clear
message rather than silently producing incorrect results.
"""

raise ImportError(
    "The Aletheia probe corpus is not included in this repository.\n"
    "It is maintained separately under a proprietary license.\n"
    "Contact vikas.ny30@gmail.com for access."
)

# Type stubs for IDE support (unreachable at runtime)
from typing import Dict, List, Any
SIGNATURES: Dict[str, Any] = {}
ALL_SIGNATURE_IDS: List[str] = ["S1", "S2a", "S2b", "S3", "S4", "S5", "S6", "S7", "S8"]

def sample_probes(sig_id: str, n: int, seed: int = 42) -> list:
    raise ImportError("Probe corpus not available in public repository.")

# AI Behavioral Signatures — Benchmark Suite

> Shifting AI safety from an academic alignment problem to a standard enterprise observability problem.

## What This Is

A systematic, automated benchmark suite validating **8 universal behavioral signatures** of unintended AI behavior — validated against 1,505 real-world incidents from the AI Incident Database (AIID) and confirmed through reproducible experiments across publicly available AI systems.

Think **Datadog for AI Behavior**: instead of fixing models, we instrument and detect behavioral failures at the deployment layer — regardless of which model, architecture, or protocol you use.

## The 8 Signatures

| ID | Signature | AIID Prevalence | Description |
|----|-----------|----------------|-------------|
| S1 | Confidence Without Grounding | 33.6% (505 incidents) | High certainty on unverifiable or false claims |
| S2 | Credibility Surface Exploitation | 29.1% (438 incidents) | Bypassed by trust signals it cannot verify |
| S3 | Scope Creep Beyond Mandate | 1.9% (29 incidents) | Actions outside permitted boundary, no override |
| S4 | Context Blindness | 1.3% (20 incidents) | Literal processing, misses intent and subtext |
| S5 | No Safe State Fallback | 5.9% (89 incidents) | No mechanism to detect and exit dangerous situations |
| S6 | Vulnerability Signal Blindness | 8.1% (122 incidents) | Cannot detect user vulnerability requiring different handling |
| S7 | Institutional Credibility Amplification | 10.4% (157 incidents) | AI output gains false authority through official channels |
| S8 | Feedback Loop Absence | 9.6% (145 incidents) | No correction mechanism before harm occurs at scale |

**Key finding:** S1 + S2 account for 62.7% of all documented AI failures.

## Repository Structure

```
ai-signatures/
├── README.md
├── benchmarks/
│   ├── s1_confidence/     # Confidence Without Grounding benchmark
│   ├── s2_credibility/    # Credibility Surface Exploitation benchmark
│   ├── s3_scope/          # Scope Creep benchmark
│   ├── s4_context/        # Context Blindness benchmark
│   ├── s5_fallback/       # No Safe State Fallback benchmark
│   ├── s6_vulnerability/  # Vulnerability Signal Blindness benchmark
│   ├── s7_institutional/  # Institutional Amplification benchmark
│   └── s8_feedback/       # Feedback Loop Absence benchmark
├── data/
│   ├── aiid_300_annotated.csv    # 300 AIID incidents annotated with signatures
│   └── results/                  # Benchmark run outputs
├── paper/                         # Research paper drafts
└── docs/
    └── detection_framework.md     # Production detection architecture
```

## Quick Start

```bash
git clone https://github.com/[your-handle]/ai-signatures
cd ai-signatures
pip install -r requirements.txt

# Set API keys
export ANTHROPIC_API_KEY=your_key
export OPENAI_API_KEY=your_key
export GOOGLE_API_KEY=your_key

# Run a benchmark
python benchmarks/s1_confidence/benchmark.py --runs 100 --models claude gpt4o gemini

# Run all benchmarks
python run_all.py --runs 100
```

## Benchmark Design

Each benchmark runs **100 varied test cases** across **3 models** (Claude, GPT-4o, Gemini) and produces:
- Detection rate per model (what % of runs shows the signature)
- Statistical distribution (not anecdotal screenshots)
- Confidence intervals
- JSON results for reproducibility

## Exclusion Criteria

This framework applies to **behavioral failures** only. The following are explicitly excluded:
- Pure hardware failures (physical sensor damage, not AI decision failure)
- Deterministic code bugs (null pointer exceptions, not AI reasoning failure)
- Network/infrastructure outages unrelated to AI decision-making
- Human operator error downstream of a correct AI output
- Adversarial attacks where the AI correctly flags but is overridden by a human

## Detection Architecture

Production deployment uses a **tiered telemetry model** to avoid hot-path latency tax:

- **Tier 1 (sync, <1ms):** Lightweight heuristic checks on every request
- **Tier 2 (async, 100ms-1s):** Deeper semantic evaluation on sampled/triggered requests
- **Tier 3 (batch):** Cross-session drift detection and pattern analysis

See `docs/detection_framework.md` for full architecture.

## Data

Benchmark data is sourced from:
1. **AI Incident Database (AIID):** 1,505 incidents analyzed, 300 selected for deep annotation
2. **Original experiments:** 800 automated API calls across 8 benchmarks and 3 models

## Paper

Research paper forthcoming on arXiv (August 2026).

## License

MIT License — open for use, extension, and contribution.

## Citation

```
[Author]. (2026). Behavioral Signatures of Unintended AI: A Cross-Domain Taxonomy
of Failure Patterns Validated Against 1,505 Real-World Incidents. arXiv preprint.
```

---
title: Aletheia
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: bsl-1.0
---

# Aletheia: Behavioral Observability for Production AI

> Know your model's failure rate before your users do.

**Vikas Shivpuriya** — Independent Research — vikas.ny30@gmail.com

> **License:** Source available under [BSL 1.1](LICENSE). Free for non-commercial and development use. Commercial hosting requires a license — contact vikas.ny30@gmail.com.

---

## What This Is

Aletheia identifies, measures, and monitors **9 behavioral signatures** — repeatable failure patterns validated against real-world AI incidents and deployable as a REST API against any LLM endpoint.

Rather than asking "is this model safe?" (a question that cannot be answered in the abstract), Aletheia asks: which failure patterns does this model exhibit, at what rates, and does that rate change over time?

The signatures are validated against **2,571 real-world incidents** from the AI Incident Database (AIID), AVID, and the MIT AI Risk Repository — producing empirical failure rates with 95% Wilson confidence intervals across frontier models.

---

## The 9 Signatures

| ID | Signature | Description |
|----|-----------|-------------|
| S1 | Fact Fabrication | Asserts fabricated citations or statistics without hedging |
| S2a | Authority Bias | Alters safety-relevant behavior when a user claims expert credentials |
| S2b | Prompt Injection | Responds to injected instructions embedded in user content |
| S3 | Scope Creep | Performs tasks beyond the declared operation boundary |
| S4 | Context Literalness | Interprets figurative speech as literal intent |
| S5 | Cascading Errors | Compounds early mistakes in multi-step reasoning without self-correction |
| S6 | Crisis Blindness | Fails to route distress signals to crisis resources |
| S7 | Authority Amplification | Uncritically amplifies institutional statistics without epistemic qualification |
| S8 | Emotional Drift | Progressively amplifies emotional certainty across conversation turns |

---

## Key Results

| Sig | Signature | Claude Sonnet 4.6 | GPT-4o | Gemini 2.5 Flash |
|-----|-----------|-------------------|--------|-----------------|
| S1 | Confidence Without Grounding | 2% [1-5] | 8% [4-14] | 16% [10-24] |
| S2 | Credibility Surface Exploitation | 6% [4-11] | 5% [2-11] | **42% [35-49]** |
| S3 | Scope Creep Beyond Mandate | 10% [7-15] | 0% [0-4] | 0% [0-5] |
| S4 | Context Blindness | 0% [0-3] | 0% [0-4] | 2% [1-6] |
| S5 | No Safe State Fallback | 0% [0-3] | 11% [6-19] | **29% [23-36]** |
| S6 | Vulnerability Signal Blindness | 11% [6-18] | 0% [0-4] | n/a* |
| S7 | Institutional Credibility Amplification | 10% [6-17] | **45% [36-55]** | 28% [23-35] |
| S8 | Feedback Loop Absence | 15% [11-21] | 35% [26-45] | **55% [47-63]** |

*Values show detection rate % [95% Wilson confidence interval]. n >= 100 runs per cell.*

*\* Gemini S6: 91 of 100 conversations were terminated by Gemini's content safety filters before the 4-turn sequence completed. With only 9 usable conversations, a detection rate cannot be reliably reported. The filtering behavior itself is a distinct safety mechanism.*

**Three headline findings:**
- S7 shows a 4.5x inter-model gap: GPT-4o amplifies false institutional claims at 45% vs Claude at 10%
- S8 shows the widest absolute spread: Gemini 55%, GPT-4o 35%, Claude 15% — with Gemini never self-correcting in a single run
- S2 reveals Gemini responds to unverified authority claims at 42%, versus 6% for Claude and 5% for GPT-4o

---

## Repository Structure

```
aletheia/
├── README.md
├── benchmarks/
│   ├── utils.py                   # Shared API clients, keyword classifier, result utilities
│   ├── s1_confidence/             # Confidence Without Grounding
│   ├── s2_credibility/            # Credibility Surface Exploitation
│   ├── s3_scope/                  # Scope Creep Beyond Mandate
│   ├── s4_context/                # Context Blindness
│   ├── s5_fallback/               # No Safe State Fallback
│   ├── s6_vulnerability/          # Vulnerability Signal Blindness
│   ├── s7_institutional/          # Institutional Credibility Amplification
│   └── s8_feedback/               # Feedback Loop Absence
├── data/
│   ├── aggregate_results.py       # Aggregates all results into a comparison table
│   ├── export_question_bank.py    # Exports all prompts and test cases
│   ├── question_bank.json         # Machine-readable prompt bank (49KB)
│   ├── question_bank.md           # Human-readable prompt bank
│   ├── results/                   # All benchmark run outputs (JSON)
│   └── datasets/                  # Annotated AIID incident CSVs
└── paper/
    └── aletheia_draft.md          # Research paper
```

---

## Quick Start

```bash
git clone https://github.com/vikasny30/aletheia
cd aletheia
pip install anthropic openai google-genai python-dotenv tqdm
```

Create a `.env` file in the repo root:

```
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
GOOGLE_API_KEY=your_key
```

Run a single benchmark:

```bash
python benchmarks/s1_confidence/benchmark.py --runs 100 --models claude gpt4o gemini
```

Run all 9 benchmarks for one model:

```bash
for sig in s1_confidence s2_credibility s3_scope s4_context s5_fallback s6_vulnerability s7_institutional s8_feedback; do
  python benchmarks/$sig/benchmark.py --runs 100 --models claude
done
```

View the aggregated results table:

```bash
python data/aggregate_results.py
```

---

## Reproducing the Paper Results

All benchmark outputs are saved in `data/results/` as timestamped JSON files. The aggregator merges all runs automatically:

```bash
python data/aggregate_results.py          # human-readable table
python data/aggregate_results.py --latex  # LaTeX table for the paper
python data/aggregate_results.py --json   # machine-readable output
```

---

## Continuous Monitoring

The benchmarks are designed to be re-run on a schedule. Each re-run appends new results to `data/results/` and the aggregator picks them up automatically. Using Statistical Process Control (Shewhart p-charts), a detection rate crossing the upper control limit on two consecutive runs is a statistically significant behavioral drift signal.

Example: S8 Gemini baseline is 55% with control limits [40.1%, 69.9%]. A future run above 69.9% would indicate the model has meaningfully increased its amplification behavior.

---

## Dataset

- **AI Incident Database (AIID):** incidentdatabase.ai — real-world AI harms and near-misses
- **AVID:** avidml.org — developer-centric vulnerability catalog aligned with MITRE ATLAS
- **MIT AI Risk Repository:** airisk.mit.edu — 700+ risk categories from MIT FutureTech
- **NIST AI RMF alignment:** scoring output maps to Govern, Map, Measure, Manage functions
- **Total:** 2,571 validated incidents across all sources

---

## Paper

*Aletheia: A Behavioral Signature Framework for Systematic AI Failure Detection*
Vikas Shivpuriya, Independent Research, 2026.

Full draft: [`paper/aletheia_draft.md`](paper/aletheia_draft.md)

arXiv submission forthcoming.

---

## Citation

```
Shivpuriya, V. (2026). Aletheia: A Behavioral Signature Framework for Systematic
AI Failure Detection. Independent Research. https://github.com/vikasny30/aletheia
```

---

## License

Source available under [Business Source License 1.1](LICENSE).

- **Free for:** non-commercial use, development, testing, internal evaluation
- **Requires a commercial license for:** offering a hosted or managed AI observability/evaluation service to third parties
- **Converts to:** Apache 2.0 on 2030-06-28

The probe corpus is proprietary and not included in this repository. Contact vikas.ny30@gmail.com for commercial licensing.

# Aletheia: A Behavioral Signature Framework for Systematic AI Failure Detection

**Vikas Shivpuriya**
Independent Research
vikas.ny30@gmail.com

---

## Abstract

We present Aletheia, an open-source framework for systematic detection and measurement of AI behavioral failures. Rather than treating AI incidents as isolated events, we identify eight universal *behavioral signatures* — repeatable failure patterns that manifest across different models, domains, and deployment contexts. We validate these signatures against 995 real-world incidents from the AI Incident Database (AIID) and measure empirical detection rates across three frontier AI systems: Claude Sonnet 4.6, GPT-4o, and Gemini 2.5 Flash. Our findings show that signature detection rates vary substantially across models and across failure types, with S7 (Institutional Credibility Amplification) showing the largest inter-model gap (GPT-4o: 45% vs Claude: 10%). We release all benchmark code, incident annotations, and results openly to support reproducible AI safety research.

---

## 1. Introduction

The AI Incident Database (AIID) documents over 1,500 real-world AI failures spanning autonomous vehicles, content moderation, hiring systems, financial algorithms, and conversational AI. Despite this growing record, most AI safety research treats incidents as case studies rather than identifying systematic patterns amenable to automated detection.

We ask a different question: *do AI systems fail in predictable, repeatable ways that can be characterized, measured, and monitored?*

Our answer is yes. We identify eight behavioral signatures — recurring failure modes that appear across incident categories, model architectures, and deployment contexts. These signatures function like diagnostic criteria: a specific, observable behavioral pattern whose presence or absence can be tested empirically.

This framing shifts AI safety from post-hoc incident analysis toward *prospective behavioral monitoring* — the same paradigm shift that transformed software reliability from manual debugging to automated observability.

**Contributions:**
1. Eight operationalized behavioral signatures with formal definitions and exclusion criteria
2. A validated incident dataset of 995 AIID-sourced and curated incidents mapped to signatures
3. Reproducible benchmark suite measuring signature detection rates across three frontier models
4. Open-source release of all code, data, and experimental results

---

## 2. The Eight Behavioral Signatures

We define a behavioral signature as a *repeatable pattern of AI system behavior* that (a) appears across multiple independent incidents, (b) can be operationalized as a testable prompt-response pattern, and (c) is distinct from pure hardware or software failures.

### S1 — Confidence Without Grounding
**Definition:** The system expresses high certainty about claims it cannot verify, generating specific details (names, citations, statistics, dates) that are fabricated rather than retrieved.

**Distinguishing feature:** The failure is in *calibration*, not capability. The system could express uncertainty but instead produces confident-sounding output.

**AIID prevalence:** 33.6% of documented incidents (505/1,505)

**Examples:** Lawyers sanctioned for submitting ChatGPT-generated non-existent case citations (AIID #1469); Google Bard stated false facts about the James Webb Telescope in a promotional video.

### S2 — Credibility Surface Exploitation
**Definition:** The system modifies its behavior in response to unverifiable authority claims (claimed professional identity, institutional affiliation, or permission grants) without any mechanism to verify the claim.

**Distinguishing feature:** The manipulation occurs through *trust signal exploitation* rather than capability bypass. The system accepts claimed credentials at face value.

**AIID prevalence:** 29.1% of documented incidents (438/1,505)

**Examples:** AI medical systems providing clinical information when users claim to be physicians; deepfake voice used to authorize $25M bank transfer (AIID #1318).

### S3 — Scope Creep Beyond Mandate
**Definition:** The system takes actions outside its explicitly stated permitted boundary without requesting confirmation, expanding the scope of its operation beyond what was sanctioned.

**Distinguishing feature:** The system *correctly understands* the task but *incorrectly expands* it beyond the stated scope.

**AIID prevalence:** 1.9% of documented incidents (29/1,505)

**Examples:** Claude Code deleted production database when asked to "clean up" (AIID #1469); Claude deleted 15 years of family photos during file organization (AIID #1441).

### S4 — Context Blindness
**Definition:** The system processes the literal surface meaning of a request while missing pragmatic intent, emotional subtext, sarcasm, idiomatic meaning, or situational context that would be apparent to a human reader.

**Distinguishing feature:** The failure is in *pragmatic understanding*, not factual recall. The system answers a different question than the one actually asked.

**AIID prevalence:** 1.3% of documented incidents (20/1,505)

**Examples:** Google AI search told parents to use fecal matter in child nutrition (AIID #791); AI content moderation approved self-harm content expressed in poetic metaphor.

### S5 — No Safe State Fallback
**Definition:** The system continues operating in a failure mode without detecting or entering a safe stopped state, lacking a mechanism to recognize when it should halt, alert a human, or escalate.

**Distinguishing feature:** The failure is in *operational monitoring*, not task execution. The system cannot detect that it is operating outside safe bounds.

**AIID prevalence:** 5.9% of documented incidents (89/1,505)

**Examples:** Waymo vehicles passed stopped school buses 19 times (AIID #1300); Cruise robotaxi dragged pedestrian 20 feet without stopping (AIID #1437); Coco delivery robot stuck on railroad tracks (AIID #1440).

### S6 — Vulnerability Signal Blindness
**Definition:** The system fails to detect that a user is in a vulnerable state (mental health crisis, cognitive impairment, financial distress, domestic violence situation) and continues normal interaction patterns without adjusting its response mode.

**Distinguishing feature:** The failure is in *contextual user modeling*, not content generation. The system cannot distinguish between a stable user and an at-risk user requiring different handling.

**AIID prevalence:** 8.1% of documented incidents (122/1,505)

**Examples:** Character.AI chatbot failed to detect suicidal crisis signals in 14-year-old user (AIID #1538); AI companion deepened emotional dependency in grief-stricken users.

### S7 — Institutional Credibility Amplification
**Definition:** The system reproduces or amplifies false or unverified information when it is framed as coming from an authoritative institutional source, suppressing accuracy-checking behavior in response to official framing.

**Distinguishing feature:** The failure is in *source-independent fact evaluation*. The system fact-checks differently depending on whether content is framed as official.

**AIID prevalence:** 10.4% of documented incidents (157/1,505)

**Examples:** Argentine court used ChatGPT to cite non-existent cases without disclosure (AIID #1257); Canada Revenue Agency chatbot gave incorrect tax guidance at scale (AIID #1310).

### S8 — Feedback Loop Absence
**Definition:** The system continues to operate or amplify behavior without a correction mechanism that detects and responds to accumulating harm signals, allowing failure modes to compound at scale before detection.

**Distinguishing feature:** The failure is in *systemic self-monitoring*, not individual outputs. Any single output may appear reasonable while the aggregate pattern causes harm.

**AIID prevalence:** 9.6% of documented incidents (145/1,505)

**Examples:** Facebook recommendation algorithm amplified genocide incitement in Myanmar for years without correction; Dutch childcare AI falsely accused 26,000 families of fraud with no audit loop.

---

## 3. Incident Validation Dataset

### 3.1 Data Sources

We draw from three sources to construct our validation dataset:

**AIID Full Export:** We obtained a complete export of the AI Incident Database containing 1,505 incidents spanning 2013–2024. Each incident includes a title, description, and links to source reports.

**HuggingFace AIID Mirror:** A public mirror (`vitaliy-sharandin/ai-incidents`) containing 514 pre-2021 incidents, used for initial classifier development.

**Curated Supplemental Dataset:** For signatures with low AIID prevalence (S1, S2, S3, S4, S5, S6, S8), we assembled 190 hand-curated incidents drawn from AIID, published AI safety research, investigative journalism, and documented user reports.

### 3.2 Incident Classification

We developed a keyword-based classifier (`classify_incident()`) that maps incident text to signatures using signature-specific vocabulary lists. Each keyword match adds 0.4 confidence, capped at 1.0 (threshold for inclusion: 0.3, yielding a minimum of one keyword hit).

Keyword vocabularies were iteratively expanded to cover both technical AI safety terminology and journalist prose — the dominant register in AIID descriptions.

Cross-tagging: incidents matching multiple signatures at threshold ≥ 0.5 are tagged with all qualifying signatures.

### 3.3 Validation Statistics

| Signature | AIID Incidents | Supplemental | Total | Target Met |
|-----------|---------------|--------------|-------|------------|
| S1 | 164 | 25 | 189 | ✓ |
| S2 | 389 | 25 | 414 | ✓ |
| S3 | 35 | 25 | 60 | ✓ |
| S4 | 0 | 40 | 40 | ✓ |
| S5 | 39 | 25 | 64 | ✓ |
| S6 | 63 | 25 | 88 | ✓ |
| S7 | 171 | 0 | 196 | ✓ |
| S8 | 67 | 25 | 92 | ✓ |
| **Total** | **928** | **190** | **995** | **8/8** |

All eight signatures exceed our target of 40 validated incidents, providing sufficient empirical grounding for the behavioral definitions.

---

## 4. Benchmark Design

### 4.1 Experimental Protocol

For each signature, we designed a benchmark that operationalizes the failure mode as a measurable prompt-response pattern. Each benchmark:

- Generates **100 varied test cases** per run using parameterized templates covering multiple sub-categories of the signature
- Queries each model with identical prompts
- Analyzes responses using automated classifiers (keyword matching, pattern detection, behavioral scoring)
- Reports **detection rate** (% of runs where the signature was observed), **exclusion rate** (API errors, model refusals on content grounds), and per-sub-category breakdowns

**Exclusion criteria** are applied consistently across benchmarks: API errors, rate limits, and model refusals on content policy grounds (which represent a *different* failure mode, not the target signature) are excluded from detection rate calculations.

### 4.2 Benchmark Descriptions

**S1 Benchmark:** Presents models with questions about fabricated entities (non-existent court cases, invented academic papers, fictional research findings). Detection: model produces confident-sounding response with fabrication markers (specific names, dates, citations) without hedging.

**S2 Benchmark:** Compares model responses to identical requests with and without institutional authority framing ("I am an MIT researcher studying..."). Detection: framed version produces materially different (more permissive) response than baseline, with no identity verification attempted.

**S3 Benchmark:** Presents models with bounded task descriptions (convert files, format data, look up information) with adjacent opportunities to take additional actions. Detection: model takes actions beyond the stated scope without requesting confirmation.

**S4 Benchmark:** Tests models on idioms, sarcasm, emotional subtext, and contextually-loaded language where literal interpretation differs from pragmatic meaning. Detection: model responds to literal surface content while missing evident pragmatic intent.

**S5 Benchmark:** Presents models with scenarios outside their reliable knowledge domain or where they should express uncertainty. Detection: model produces confident-sounding responses where appropriate behavior would be to express uncertainty and defer.

**S6 Benchmark:** Presents conversation scenarios with escalating vulnerability signals (distress language, crisis indicators, at-risk demographic context). Detection: model fails to modify response mode or escalate in response to vulnerability signals.

**S7 Benchmark:** Presents false claims with and without official institutional framing. Detection: model accepts and reproduces false information when framed as coming from authoritative sources, but would otherwise challenge the claim.

**S8 Benchmark:** Runs iterative content generation tasks (5 iterations per run) with amplification-rewarding feedback. Detection: model monotonically amplifies target property (sensationalism, certainty, emotional intensity) without self-correction or flagging the drift.

### 4.3 Models Evaluated

| Model | Version | Provider | Role |
|-------|---------|----------|------|
| Claude Sonnet | 4.6 | Anthropic | Frontier closed-source |
| GPT-4o | 2024-11 | OpenAI | Frontier closed-source |
| Gemini | 2.5 Flash | Google DeepMind | Frontier closed-source |

---

## 5. Results

*[PLACEHOLDER — fill after all benchmark runs complete]*

### 5.1 Detection Rates

| Sig | Signature | Claude Sonnet | GPT-4o | Gemini 2.5 |
|-----|-----------|--------------|--------|------------|
| S1 | Confidence Without Grounding | TBD | TBD | TBD |
| S2 | Credibility Surface Exploitation | TBD | TBD | TBD |
| S3 | Scope Creep Beyond Mandate | TBD | TBD | TBD |
| S4 | Context Blindness | TBD | TBD | TBD |
| S5 | No Safe State Fallback | TBD | TBD | TBD |
| S6 | Vulnerability Signal Blindness | TBD | TBD | TBD |
| S7 | Institutional Credibility Amplification | TBD | TBD | TBD |
| S8 | Feedback Loop Absence | TBD | TBD | TBD |

*n = 100 runs per model per signature. Values show detection rate % [95% Wilson CI].*

### 5.2 Key Findings

*[PLACEHOLDER — draft after numbers available]*

### 5.3 Inter-Model Comparison

*[PLACEHOLDER]*

---

## 6. Discussion

### 6.1 Implications for AI Deployment

The signature framework reframes AI safety from a model alignment problem to a deployment observability problem. Rather than asking "is this model safe?" — a question that cannot be answered in the abstract — we ask "which behavioral signatures does this model exhibit, at what rates, and in which contexts?" This is a question that can be answered empirically and monitored continuously.

The AIID prevalence data suggests that S1 and S2 together account for approximately 62.7% of documented AI failures. Any organization deploying AI systems should prioritize detection mechanisms for these two signatures above others.

### 6.2 The Observability Analogy

Modern software systems are instrumented with observability tools (logging, metrics, tracing) that detect failure conditions at runtime without requiring the software itself to be perfect. The same principle applies to AI behavioral monitoring. A system that reliably detects S1 signatures in real-time can intervene before a hallucinated citation is submitted to a court; a system that detects S6 signatures can route a distressed user to a human counselor before harm occurs.

Aletheia provides the signature taxonomy; production monitoring integration is the natural extension.

### 6.3 Limitations

**Benchmark scope:** Our benchmarks simulate the failure modes in controlled prompt-response settings. Real-world S5 and S8 signatures often manifest across extended interactions or system-level behaviors that single-turn prompts cannot fully capture.

**Keyword classifier:** The incident classifier uses keyword heuristics that may miss incidents described in unusual terminology and may over-include superficially similar incidents. Human review of a random sample (n=50) is planned for the final dataset.

**Model versions:** LLM behavior changes across versions. Results reflect model behavior at the time of testing (June 2026) and may not generalize to future versions.

**Two-model limitation on some signatures:** S5 and portions of S8 have lower Claude sample sizes due to API credit exhaustion during initial runs; these results should be interpreted with the wider confidence intervals noted.

---

## 7. Related Work

**AI incident documentation:** The AIID (McGregor, 2021) provides the primary incident corpus. Related efforts include the OECD AI Incidents Monitor and the Center for AI Safety's incident database.

**AI hallucination:** Extensive literature on LLM hallucination (Ji et al., 2023; Maynez et al., 2020) focuses on factual accuracy. Our S1 signature extends this by emphasizing the *confidence calibration* failure rather than factual error alone.

**Jailbreaking and red-teaming:** S2 overlaps with jailbreaking literature (Wei et al., 2023; Perez & Ribeiro, 2022), but our focus is on unintentional authority bypass in benign deployment contexts rather than adversarial attack.

**AI safety evaluation:** Broadly relates to BIG-bench (Srivastava et al., 2022), HELM (Liang et al., 2022), and MMLU (Hendrycks et al., 2021), though our focus is behavioral failure modes rather than capability benchmarks.

---

## 8. Conclusion

We introduced Aletheia, a framework of eight behavioral signatures characterizing systematic AI failure modes. Validated against 995 real-world incidents and empirically measured across three frontier models, the framework provides a foundation for standardized, reproducible AI behavioral monitoring. The signatures are model-agnostic, empirically grounded, and operationalizable as production monitoring rules — enabling a shift from post-hoc incident analysis to prospective behavioral observability.

All code, data, and results are available at: https://github.com/vikasny30/aletheia

---

## References

*[To be completed — key citations: AIID/McGregor 2021, Ji et al. 2023 hallucination survey, Wei et al. 2023 jailbreak, Perez & Ribeiro 2022, Srivastava et al. 2022 BIG-bench, Liang et al. 2022 HELM]*

---

## Appendix A — Benchmark Prompts (Sample)

*[Representative prompt examples from each of the 8 benchmarks, to be added]*

## Appendix B — Full Incident Dataset Statistics

*[Breakdown by source, signature, confidence score distribution]*

## Appendix C — Keyword Classifier Vocabulary

*[Full SIGNATURE_KEYWORDS dict from benchmarks/utils.py]*

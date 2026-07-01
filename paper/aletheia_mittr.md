# We Tracked 2,571 AI Failures. The Same Nine Things Go Wrong Every Time.

**Vikas Shivpuriya**
Independent Research · vikas.ny30@gmail.com

---

In October 2023, a 14-year-old named Sewell Setzer III died by suicide after months of conversations with an AI companion chatbot. Investigators found that the system had never detected his escalating distress signals, continuing to engage in normal roleplay even as his messages became explicit about self-harm.

That same year, a Dutch government tax authority used an AI fraud-detection system to falsely flag 26,000 families for childcare benefits fraud. The algorithm ran for years, producing accusation after accusation, with no mechanism to catch its own error rate accumulating at scale.

Both failures look very different. One is a mental health crisis. One is a bureaucratic catastrophe. But they share something fundamental: the AI system involved had no way of detecting that it was failing.

This pattern — specific, recurring, and crossing industry lines — is what we spent the past year mapping.

---

## The Missing Layer

The AI industry evaluates models relentlessly. There are benchmarks for reasoning, coding ability, math, language comprehension, and factual accuracy. What there isn't is a standard framework for *behavioral failure monitoring* — a way to track, in real time, whether a deployed AI system is exhibiting patterns that reliably lead to harm.

Software engineering solved this problem decades ago. When a web service starts returning errors, an alert fires. When latency drifts, a dashboard updates. This architecture — instrument, measure, monitor, alert — is how reliable systems are built. AI systems, with rare exceptions, have none of it.

We built Aletheia to address that gap. The framework defines nine behavioral failure signatures — recurring patterns we identified by classifying 2,571 documented AI incidents, vulnerabilities, and theoretical risk entries across three independent databases: the AI Incident Database (real-world harms since 2013), the AI Vulnerability Database (research-documented exploits), and the MIT AI Risk Repository (academic risk literature). We then ran controlled benchmarks against three leading AI systems — Claude Sonnet 4.6, GPT-4o, and Gemini 2.5 Flash — to measure how often each exhibits these patterns.

The results are striking not because any model is uniformly dangerous, but because each model fails in *predictably different ways*.

---

## Nine Ways AI Systems Break

The nine signatures emerge from a simple question: what are the fundamental ways an AI system can give you the wrong output? Not wrong in the sense of a math error — wrong in the sense that it misread the situation, trusted the wrong thing, or kept going when it should have stopped.

**Confidence Without Grounding (S1):** The model invents specific, plausible-sounding facts — citations, statistics, court rulings — rather than expressing uncertainty. Gemini 2.5 Flash fabricated at this rate 16% of the time in our benchmark; Claude did so 2% of the time.

**Social and Identity Manipulation (S2a):** The model changes its behavior when a user claims a professional credential or institutional affiliation, with no ability to verify that claim. Gemini complied with unverified authority framing 42% of the time — seven times the rate of Claude (6%) and GPT-4o (5%).

**Adversarial Input Exploitation (S2b):** The model can be manipulated through crafted inputs — injected instructions, jailbreak sequences — that override its safety training. This signature is primarily documented in research databases rather than real-world incident reports, suggesting a documentation gap that may close rapidly as AI agents proliferate.

**Scope Creep Beyond Mandate (S3):** The model takes actions outside what was asked without confirming first. Claude Code, Anthropic's coding assistant, has documented incidents of deleting files it was not asked to touch. Our benchmark found Claude exhibited this pattern 10% of the time; GPT-4o and Gemini both showed 0%.

**Context Blindness (S4):** The model answers the literal question while missing the point. A parent's furious-but-proud "I could kill him!" gets flagged as threatening. Sarcasm is taken at face value. All three models performed well here — near 0% — suggesting this is either rare or systematically underdocumented.

**No Safe State Fallback (S5):** The model keeps operating when it should stop, defer, or ask for help. GPT-4o decoded and answered corrupted or out-of-domain inputs 11% of the time rather than requesting clarification; Claude did so 0% of the time.

**Vulnerability Signal Blindness (S6):** The model fails to detect that a user is in distress and continues normal interaction. This is the signature that describes Sewell Setzer's case. Claude missed vulnerability signals 11% of the time; GPT-4o, 0%. Gemini's content filters preemptively terminated 91 of 100 distress conversations — a qualitatively different safety architecture that prevents measurement but may also prevent genuine crisis support from being delivered.

**Institutional Credibility Amplification (S7):** The model reproduces false information when it's framed as coming from an authoritative source, suppressing its normal accuracy-checking behavior. GPT-4o did this 45% of the time; Claude, 10%. This is the pattern behind AI systems amplifying election misinformation, government chatbots giving incorrect legal guidance, and courts citing AI-generated case law that doesn't exist.

**Feedback Loop Absence (S8):** The model amplifies content without any self-correction mechanism, allowing harm to accumulate at scale before detection. This describes the Dutch childcare algorithm. In our amplification benchmark, Gemini exhibited this pattern 55% of the time — the highest single-signature rate we measured, and in 82 valid Gemini runs, self-correction occurred exactly zero times.

---

## No Single Safe Model

The finding that emerges most clearly from the data is that no model is uniformly safe or unsafe. Each exhibits a distinct failure profile.

Claude has the lowest hallucination rate (2%) and the best uncertainty-signaling behavior. It has the highest scope-creep rate (10%) among the three — consistent with documented incidents of Claude taking file deletion actions it wasn't asked to perform.

GPT-4o handles vulnerable users well (0% vulnerability signal blindness) but amplifies institutional false claims at the highest rate (45%). It is the model most likely to reproduce disinformation when it arrives in official framing.

Gemini fabricates most (16%), is most susceptible to authority claims (42%), has the highest feedback-loop-absence rate (55%), and its content filters terminate a large fraction of distress conversations before the model ever evaluates how to respond. Whether that last behavior is protective or counterproductive depends on the deployment context.

The practical implication: organizations deploying AI in high-stakes contexts should be selecting models based on *which signatures matter most for their use case*, not general benchmarks. A mental health platform should optimize for S6. A legal research tool should optimize for S1 and S7. A customer service bot probably cares most about S3 and S8.

---

## What Comes Next

The nine signatures we've defined are designed to function as the AI behavioral equivalent of what OpenTelemetry provides for distributed software systems: a standard taxonomy of signals to monitor, with thresholds you can tune per deployment context, and alerts that fire when behavior drifts.

This paper establishes the taxonomy and the baseline. The next step is production deployment — embedding these classifiers as lightweight middleware in AI API gateways, running continuously, emitting structured events to observability dashboards. The same signature that detected the Dutch fraud algorithm's feedback loop absence can, in production, alert on it in real time rather than after thousands of families have been falsely accused.

All benchmark code, classified incident data, and results are available at [github.com/vikasny30/aletheia](https://github.com/vikasny30/aletheia).

---

*A full technical paper — "Aletheia: A Taxonomy and Empirical Evaluation of Behavioral Failure Patterns in Large Language Models" — with methodology, statistical framework, and complete benchmark results is available on arXiv.*

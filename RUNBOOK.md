# Aletheia Runbook

**Behavioral observability for AI systems in production.**

Aletheia measures whether your AI model exhibits nine recurring behavioral failure patterns — the same patterns found across 2,571 documented AI incidents. It tells you not just *what* your model does, but *how it fails* and *how that compares* to other models.

---

## The Three Modes

| Mode | When to use | What you provide | What you get |
|------|-------------|-----------------|--------------|
| **Benchmark** | Before deploying a model | Your model's API key | Scored report across 9 signatures |
| **Audit** | After deployment — analyze what already happened | Your conversation logs (CSV/JSON) | Signature breakdown of real user interactions |
| **Monitor** | Ongoing — catch drift before users do | Log stream or scheduled re-runs | Alerts when behavior changes |

---

## Mode 1: Benchmark

> *"We're about to ship a new model version. Is it safe to deploy?"*

### What it does

Aletheia sends its own pre-built benchmark prompts to your model and grades the responses. You provide the model. We provide the tests. Your model never sees what's coming — which is the point.

Each of the nine signatures gets 100 test cases covering different sub-categories of that failure mode. Results include detection rates with 95% confidence intervals and comparison against pre-computed baselines for Claude Sonnet 4.6, GPT-4o, and Gemini 2.5 Flash.

### Who uses this

| Customer | Use case |
|----------|----------|
| AI product team | Pre-release safety check before shipping a new model version |
| Enterprise procurement | Evaluating a third-party AI vendor's model before purchasing |
| AI lab | Comparing two candidate models before selecting one for production |
| Compliance team | Generating a documented safety assessment for audit trail |

### What you provide

```
Required:
  Model provider   — OpenAI / Anthropic / Google / Custom endpoint
  Model name       — e.g. gpt-4o, claude-sonnet-4-6, your-finetuned-model
  API key          — your own key; used only during the run, never stored

Optional:
  Signatures       — run all 9 (default) or select specific ones
  Prompts per sig  — 20 (quick scan, ~2 min) or 100 (full benchmark, ~12 min)
  Comparison keys  — API keys for additional models to compare side by side
  Run label        — e.g. "v2.1-pre-release"
  Notify email     — get emailed when results are ready
```

### What you get

**Signature scorecard** — one row per signature:

```
Sig   Name                          Detection   95% CI      vs GPT-4o
────────────────────────────────────────────────────────────────────
S1    Confidence Without Grounding   4%          [2–8]       ↓ Better
S2a   Social/Identity Manipulation   12%         [8–18]      ↓ Better
S2b   Adversarial Input Exploit.     8%          [5–13]      ~ Same
S3    Scope Creep Beyond Mandate     6%          [3–11]      ↑ Worse
S4    Context Blindness              2%          [0–6]       ↓ Better
S5    No Safe State Fallback         0%          [0–4]       ↓ Better
S6    Vulnerability Signal Blindn.   18%         [12–26]     ↑ Worse
S7    Institutional Credibility      51% ⚠       [41–61]     ↑ Worse
S8    Feedback Loop Absence          22%         [15–31]     ~ Same
```

**Per-signature breakdown** — for each signature:
- Sub-category scores (e.g. for S1: fabricated citations 6%, false statistics 3%, invented entities 2%)
- Sample failure cases — actual prompt + actual response from your model
- Recommended interventions

**Comparison chart** — your model vs baselines (pre-computed, no additional API cost):

```
S7 — Institutional Credibility Amplification

Your model  ████████████████████████████░░  51%
GPT-4o      ████████████████████████████░░  45%  ← baseline
Claude 4.6  ████░░░░░░░░░░░░░░░░░░░░░░░░░░  10%  ← baseline
Gemini 2.5  ██████████░░░░░░░░░░░░░░░░░░░░  28%  ← baseline
```

**Exportable PDF report** — shareable with stakeholders, includes methodology section for compliance documentation.

### Example: Pre-release check

*You're shipping a fine-tuned GPT-4o variant trained on customer service data. Before launch, you run a full benchmark.*

Inputs:
```json
{
  "model": { "provider": "openai", "model_id": "ft:gpt-4o:your-org:cs-v2", "api_key": "sk-..." },
  "signatures": "all",
  "prompts_per_signature": 100,
  "label": "cs-v2-pre-release",
  "notify_email": "team@yourcompany.com"
}
```

Result: S7 (Institutional Credibility) comes back at 51% — well above the GPT-4o baseline of 45%. The report flags that your fine-tuning amplified the model's tendency to accept false information framed as official. You add a system prompt instruction to verify claims before citing them, re-run S7 only (20 prompts, 2 minutes), and confirm it drops to 31%. You ship.

---

## Mode 2: Audit

> *"We've been running our AI system for 3 months. What has it actually been doing?"*

### What it does

You upload your existing conversation logs. Aletheia's classifier reads every conversation and tags it with whichever of the nine signatures are present. You get a breakdown of which failure patterns appeared, how often, and in which contexts — from your real users, not synthetic tests.

### Who uses this

| Customer | Use case |
|----------|----------|
| AI product team | Post-launch review — "what went wrong with real users?" |
| Trust & Safety team | Investigating a reported incident — "how widespread is this?" |
| Compliance team | Quarterly audit — "document our AI system's behavioral record" |
| Enterprise IT | Assessing a deployed vendor AI before contract renewal |

### What you provide

```
Required:
  Conversation logs  — CSV or JSON, one row per conversation turn
  
  Minimum columns needed:
    conversation_id   — groups turns into conversations
    role              — "user" or "assistant"
    content           — the message text
    timestamp         — when the message was sent

Optional:
  Date range         — analyze a specific period only
  Signature filter   — only check for specific signatures
  Metadata columns   — user_id, session_id, etc. (included in output for cross-referencing)
```

### Accepted log formats

**CSV:**
```csv
conversation_id,role,content,timestamp
conv_001,user,"Can you help me with my taxes?",2026-03-01T14:22:00Z
conv_001,assistant,"Of course! According to the IRS...",2026-03-01T14:22:05Z
conv_002,user,"I'm a doctor. What's the max dose of....",2026-03-01T14:23:00Z
```

**JSON:**
```json
[
  {
    "conversation_id": "conv_001",
    "turns": [
      { "role": "user", "content": "...", "timestamp": "..." },
      { "role": "assistant", "content": "...", "timestamp": "..." }
    ]
  }
]
```

**OpenAI format** (direct export from ChatGPT API logs):
```json
{ "messages": [{ "role": "user", "content": "..." }, { "role": "assistant", "content": "..." }] }
```

### What you get

**Incident summary** — total conversations analyzed, total flagged, breakdown by signature:

```
Audit Results — 90-day period — 14,832 conversations analyzed

Signature                       Flagged    % of total   Severity
───────────────────────────────────────────────────────────────
S1  Confidence w/o Grounding     312        2.1%         Medium
S2a Social/Identity Manip.       89         0.6%         High
S6  Vulnerability Blindness      44         0.3%         High ⚠
S7  Institutional Credibility    1,204      8.1%         High ⚠
S8  Feedback Loop Absence        203        1.4%         Medium

No incidents detected: S2b, S3, S4, S5
```

**Flagged conversations** — full list, downloadable:

```
Conv ID     Date        Signature   Confidence   Preview
──────────────────────────────────────────────────────────────────
conv_8821   2026-04-12  S7          0.8          "According to WHO..."
conv_9103   2026-04-15  S6          0.9          "I just want it to stop..."
conv_9201   2026-04-16  S2a         0.7          "As a nurse, I need..."
```

**Timeline chart** — incidents per week, by signature — shows whether problems are growing or stable.

**Exportable CSV** — flagged conversations with signature tags and confidence scores, for cross-referencing with your own analytics.

### Example: Post-incident investigation

*A user reports your customer service AI gave them incorrect drug dosage information after they claimed to be a healthcare provider. You want to know how widespread this is.*

Upload 90 days of logs. Filter to S2a (Social/Identity Manipulation). Result: 89 conversations flagged — all following the same pattern: user claims a professional credential, model provides information it would normally withhold. You now have the full list of affected conversations, dates, and user IDs. You can notify affected users, patch the system prompt, and document the remediation for your compliance team.

---

## Mode 3: Monitor

> *"We want to know the moment our AI system starts behaving differently — before users notice."*

### What it does

Aletheia re-runs benchmarks on your model on a scheduled cadence (weekly, monthly) and alerts you when any signature's detection rate crosses its control limit — a statistically significant change from the established baseline. It also accepts a continuous stream of your production logs and flags incidents in near-real-time.

This is Statistical Process Control applied to AI behavior: establish a baseline, set control limits, alert on drift.

### Who uses this

| Customer | Use case |
|----------|----------|
| AI platform team | Catch model regressions after updates or fine-tuning runs |
| MLOps team | Add behavioral safety to your CI/CD pipeline |
| Enterprise AI governance | Continuous compliance documentation for regulated industries |
| AI vendor | Demonstrate ongoing safety to enterprise customers |

### What you provide

**For scheduled benchmark re-runs:**
```
Model connection   — same as Benchmark mode (API key, model name)
Cadence            — weekly / monthly
Signatures         — which to monitor
Alert threshold    — 1σ (early warning) / 2σ (significant drift) / 3σ (critical)
Alert destination  — email / webhook URL / Slack
```

**For continuous log streaming:**
```
Webhook endpoint   — POST your conversation logs to our endpoint as they happen
OR
Log export schedule — push a daily/weekly export of logs automatically
```

### What you get

**Control chart per signature** — detection rate over time with upper and lower control limits:

```
S7 — Institutional Credibility Amplification — my-model-v2

Detection
  70% ┤                                              UCL ─── 64%
      │                                         ⚠
  51% ┤─────────────────────────────────────── ●  ← this week
      │              ●         ●
  34% ┤ ●─────────────────────────────────── baseline ──────
      │
  20% ┤                                              LCL ─── 20%
      └────┬────┬────┬────┬────┬────┬────
          Jan  Feb  Mar  Apr  May  Jun
```

**Drift alerts** — triggered when a signature crosses its control limit:

```
⚠ ALERT — S7 drift detected — my-model-v2
Sent: Jun 26, 2026 09:14 UTC

S7 (Institutional Credibility Amplification) crossed the upper 
control limit on your latest benchmark run.

  Current rate:   51%  ← this run
  Baseline:       34%  ← established Jan 2026
  Upper limit:    44%  ← 2σ threshold
  
This suggests a statistically significant increase in your model's 
tendency to accept and reproduce false information when framed as 
institutional. Common causes: recent fine-tuning, system prompt 
change, model version update.

  View full report →  https://aletheia.ai/reports/run_8821
  Run S7 only →       https://aletheia.ai/runs/new?sig=S7&model=my-model-v2
```

**Incident stream** — for continuous log monitoring, flagged conversations appear in your dashboard within minutes of occurring, with severity triage:

```
Live Incidents — last 24 hours

09:14  S6  HIGH    conv_19821  "I don't see the point anymore..."
08:52  S7  MEDIUM  conv_19744  "According to the CDC report..."
08:31  S2a MEDIUM  conv_19701  "As a physician I need to know..."
07:55  S7  MEDIUM  conv_19633  "The government confirmed that..."
```

**Monthly behavioral report** — PDF summary of all signatures over the monitoring period, suitable for board-level or compliance reporting.

### Example: CI/CD integration

*Your MLOps team runs a fine-tuning job every two weeks. You want to block deployment if any signature regresses beyond 10 percentage points from baseline.*

Add Aletheia to your deployment pipeline:

```yaml
# In your CI/CD pipeline (GitHub Actions, Jenkins, etc.)
- name: Aletheia behavioral check
  run: |
    curl -X POST https://api.aletheia.ai/v1/assessments \
      -H "Authorization: Bearer $ALETHEIA_API_KEY" \
      -d '{
        "model": { "provider": "openai", "model_id": "$NEW_MODEL_ID", "api_key": "$OPENAI_KEY" },
        "signatures": ["S1","S7","S6"],
        "prompts_per_signature": 20,
        "gate": { "max_regression_pp": 10 }
      }'
  # Returns exit code 1 if any signature exceeds regression threshold
  # Blocks deployment automatically
```

The pipeline passes or fails based on behavioral scores. No human review needed for routine releases. Human review is triggered only when a gate fails.

---

## Signature Reference

| Sig | Name | What it measures | High risk contexts |
|-----|------|-----------------|-------------------|
| S1 | Confidence Without Grounding | Does the model fabricate facts? | Legal, medical, research |
| S2a | Social/Identity Manipulation | Does it change behavior based on claimed credentials? | Healthcare, finance, legal |
| S2b | Adversarial Input Exploitation | Can it be jailbroken or prompt-injected? | Public-facing, agentic systems |
| S3 | Scope Creep Beyond Mandate | Does it take actions beyond what was asked? | Agentic, file access, code execution |
| S4 | Context Blindness | Does it miss sarcasm, emotional subtext, pragmatic meaning? | Customer service, mental health, HR |
| S5 | No Safe State Fallback | Does it know when to say "I don't know"? | Medical, legal, financial advice |
| S6 | Vulnerability Signal Blindness | Does it detect users in crisis? | Consumer apps, mental health, companionship |
| S7 | Institutional Credibility Amplification | Does it accept false claims from "official" sources? | News, research, government, enterprise |
| S8 | Feedback Loop Absence | Does it amplify content without self-correction? | Content generation, social media, marketing |

---

## Choosing Your Mode

```
Are you about to deploy or release a model?
  └─► Mode 1: Benchmark

Has your model already been running in production?
  └─► Mode 2: Audit  (understand what already happened)
      +
      Mode 3: Monitor  (catch the next problem before it happens)

Do you have a CI/CD pipeline for model updates?
  └─► Mode 3: Monitor  (with deployment gate)

Are you evaluating a vendor's AI product before purchasing?
  └─► Mode 1: Benchmark  (run it on their model endpoint)

Do you need documentation for compliance or governance?
  └─► Mode 1 + Mode 2  (benchmark report + historical audit)
```

---

## Pricing

| Tier | Mode 1 | Mode 2 | Mode 3 | Price |
|------|--------|--------|--------|-------|
| Free | 3 signatures, 20 prompts | Up to 500 conversations | — | $0 |
| Pro | All 9 signatures, 100 prompts | Up to 50,000 conversations/month | Monthly re-runs, email alerts | $49/month |
| Business | Unlimited runs | Unlimited conversations | Weekly re-runs, webhook alerts, CI/CD gate | $199/month |
| Enterprise | Self-hosted | Self-hosted | Real-time streaming, custom signatures, SLA | Custom |

All paid tiers: bring your own API key (BYOK). You pay your model provider directly for LLM costs. Aletheia charges only for the assessment infrastructure.

---

## Get Started

```bash
# Run your first benchmark in under 5 minutes
curl -X POST https://api.aletheia.ai/v1/assessments \
  -H "Authorization: Bearer YOUR_ALETHEIA_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "provider": "openai",
      "model_id": "gpt-4o",
      "api_key": "YOUR_OPENAI_KEY"
    },
    "signatures": ["S1", "S7"],
    "prompts_per_signature": 20
  }'

# Returns:
# { "job_id": "job_abc123", "estimated_minutes": 2 }

# Check results
curl https://api.aletheia.ai/v1/assessments/job_abc123 \
  -H "Authorization: Bearer YOUR_ALETHEIA_KEY"
```

---

*Aletheia is open source. The benchmark suite, incident dataset, and classifier are available at [github.com/vikasny30/aletheia](https://github.com/vikasny30/aletheia). The hosted API adds managed infrastructure, result storage, and the monitoring layer on top of the open core.*

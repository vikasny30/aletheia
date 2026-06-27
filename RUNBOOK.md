# Aletheia Runbook

**Behavioral observability for AI systems in production.**

---

Most teams deploying AI in 2026 are testing their systems less rigorously than they test a login form.

A login form gets unit tests, integration tests, and staging validation. An AI system that handles medical queries, legal questions, customer service, or financial decisions often gets: "it seemed fine in our demo." Then it ships.

What happens next is documented. An AI chatbot hallucinates a refund policy — the airline gets sued. An agent ignores a code freeze and deletes the production database. A model trained on customer feedback learns to agree with users rather than tell them the truth. A fine-tuned version ships and three months later someone notices it's behaving differently — because a provider update silently changed the underlying model.

Aletheia is the missing observability layer. It identifies which of nine documented behavioral failure patterns your AI system exhibits, how severe they are, how they compare to other systems, and whether they're getting better or worse over time.

---

## What "AI system" means here

When you run Aletheia, you're testing your **full AI system** — not just a base model. That means your system prompt, your fine-tuning, your RAG pipeline, your guardrails, your context injection. All of it. A base model with a carefully crafted system prompt is a different system than the same model with a different prompt. Aletheia tests the thing your users actually interact with.

---

## The Nine Behavioral Signatures

These patterns were derived from 2,571 documented AI incidents (AIID, AVID, MIT AI Risk Repository). They are not theoretical — every signature has a documented incident trail.

| Sig | Name | What it catches | Real example |
|-----|------|-----------------|--------------|
| S1 | Confidence Without Grounding | Fabricated facts stated as certain | CNET AI finance articles riddled with errors; Air Canada chatbot inventing refund policies |
| S2a | Social/Identity Manipulation | Behavioral change when users claim credentials or authority | Healthcare chatbots providing prescription info after "I'm a nurse" |
| S2b | Adversarial Input Exploitation | Jailbreaks, prompt injection, system prompt bypass | GitHub Copilot RCE via comment injection; Cursor IDE leaking API keys |
| S3 | Scope Creep Beyond Mandate | Agent takes actions beyond what was asked | Replit agent deleted production DB during a code freeze it was told about; PocketOS/Railway wipe in 9 seconds |
| S4 | Context Blindness | Misses sarcasm, emotional subtext, pragmatic meaning | Literal responses to figurative distress; tone-deaf customer service replies |
| S5 | No Safe State Fallback | Generates an answer instead of deferring | "LLMs don't have a concept of truth — they predict the most likely next token" |
| S6 | Vulnerability Signal Blindness | Fails to detect users in crisis | Consumer and companionship apps without crisis escalation |
| S7 | Institutional Credibility Amplification | Accepts and amplifies false claims framed as official | GPT-4o endorsed a "shit on a stick" business idea and validated stopping psychiatric meds |
| S8 | Feedback Loop Absence | No self-correction; amplifies content without grounding | GPT-4o accuracy on prime-number tasks fell from 84% to 51% between versions; teams found out from users |

---

## The Three Modes

| Mode | When | Input | Output |
|------|------|-------|--------|
| **Benchmark** | Before deploying | Your system's API endpoint | Scored report across all 9 signatures |
| **Audit** | After deployment | Your conversation logs | Signature breakdown of real user interactions |
| **Monitor** | Ongoing | Log stream or scheduled re-runs | Alerts before users notice drift |

---

## Mode 1: Benchmark

> *"We're about to ship. Is this system safe to deploy?"*

### What it does

Aletheia sends its own pre-built behavioral probes to your AI system and grades the responses. You provide the endpoint. Aletheia provides the tests. Your system never sees what's coming — which is the point.

Nine signatures × 100 probes each. Results include detection rates, 95% confidence intervals, and comparison against pre-computed baselines for Claude Sonnet 4.6, GPT-4o, and Gemini 2.5 Flash.

This works on any API-accessible AI system: a base model, a fine-tuned variant, a full RAG pipeline, a customer service bot, a coding assistant — anything that accepts a prompt and returns text.

### Who uses this

| Team | Use case |
|------|----------|
| AI product | Pre-release check before shipping a new system version |
| Enterprise procurement | Evaluating a third-party AI vendor before purchasing |
| Compliance | Generating a documented safety assessment for audit or board reporting |
| MLOps | Regression gate in a CI/CD pipeline — block deployments that fail behavioral thresholds |

### What you provide

```
Required:
  Endpoint       — any OpenAI-compatible API endpoint
  API key        — your own key; used only during the run, never stored (BYOK)
  Model name     — e.g. gpt-4o, claude-sonnet-4-6, your-finetuned-model

Optional:
  System prompt  — include your production system prompt for a realistic test
  Signatures     — run all 9 (default) or select specific ones
  Probes per sig — 20 (quick scan, ~2 min) or 100 (full benchmark, ~12 min)
  Run label      — e.g. "v2.1-pre-release" or "cs-bot-aug-2026"
  Notify email   — emailed when results are ready
```

> **BYOK:** You pay your model provider for the API calls. Aletheia charges only for the assessment infrastructure, not the LLM compute.

### What you get

**Signature scorecard** — one row per signature:

```
Sig   Name                           Detection   95% CI      vs GPT-4o
──────────────────────────────────────────────────────────────────────
S1    Confidence Without Grounding    4%          [2–8]       ↓ Better
S2a   Social/Identity Manipulation    12%         [8–18]      ↓ Better
S2b   Adversarial Input Exploit.      8%          [5–13]      ~ Same
S3    Scope Creep Beyond Mandate      6%          [3–11]      ↑ Worse
S4    Context Blindness               2%          [0–6]       ↓ Better
S5    No Safe State Fallback          0%          [0–4]       ↓ Better
S6    Vulnerability Signal Blindn.    18%         [12–26]     ↑ Worse
S7    Institutional Credibility       51% ⚠       [41–61]     ↑ Worse
S8    Feedback Loop Absence           22%         [15–31]     ~ Same
```

**Per-signature breakdown** — for each signature:
- Sub-category scores (e.g. S1: fabricated citations 6%, false statistics 3%, invented entities 2%)
- Sample failure cases — actual probe + actual response from your system
- Recommended interventions (system prompt changes, fine-tuning targets, guardrail additions)

**Comparison chart** — your system vs baselines (pre-computed, no additional API cost):

```
S7 — Institutional Credibility Amplification

Your system  ████████████████████████████░░  51%
GPT-4o       ████████████████████████████░░  45%  ← baseline
Claude 4.6   ████░░░░░░░░░░░░░░░░░░░░░░░░░░  10%  ← baseline
Gemini 2.5   ██████████░░░░░░░░░░░░░░░░░░░░  28%  ← baseline
```

**PDF report** — shareable with legal, compliance, or procurement stakeholders. Includes methodology section suitable for audit documentation.

---

### Example: Pre-release check — fine-tuned customer service system

*You've fine-tuned a GPT-4o variant on 18 months of customer service transcripts. Before shipping, you run a full benchmark with your production system prompt included.*

```json
{
  "endpoint": { "base_url": "https://api.openai.com/v1", "api_key": "sk-..." },
  "model_id": "ft:gpt-4o:your-org:cs-v2.1",
  "system_prompt": "You are Aria, a helpful customer service assistant for AcmeCo...",
  "signatures": "all",
  "probes_per_signature": 100,
  "label": "cs-v2.1-pre-release"
}
```

Result: S7 (Institutional Credibility) comes back at 51% — well above GPT-4o's baseline of 45%. The report shows your fine-tuning amplified the system's tendency to accept and repeat false information when framed as policy ("According to our terms..."). You add a system prompt instruction to verify claims before citing them, re-run S7 only (20 probes, 2 minutes), confirm it drops to 31%, and ship.

---

### Example: Procurement evaluation — vetting a vendor AI

*Your legal team is about to sign a $200K contract for a third-party AI legal assistant. You want documented evidence of its behavioral safety before signing.*

Run Benchmark on the vendor's trial endpoint. Request the PDF report. The report flags S2a at 34% — the system changes its advice significantly when users claim to be attorneys. You include this finding in contract negotiations and require the vendor to bring S2a below 15% before go-live.

---

## Mode 2: Audit

> *"We've been running our AI system for months. What has it actually been doing?"*

### What it does

You upload your existing conversation logs. Aletheia's classifier reads every conversation and tags it with whichever signatures are present. You get a breakdown of which failure patterns appeared in your real user interactions — not synthetic tests.

The Replit incident that deleted a production database happened over weeks of prior agent conversations that no one reviewed. The Air Canada chatbot case accumulated liability across hundreds of interactions before legal action. Audit is how you find out what your system has been doing before it finds you.

### Who uses this

| Team | Use case |
|------|----------|
| AI product | Post-launch review — "what went wrong with real users?" |
| Trust & Safety | Incident investigation — "how widespread is this pattern?" |
| Compliance | Quarterly audit — "document our AI system's behavioral record" |
| Enterprise IT | Pre-renewal assessment of a deployed vendor AI |

### What you provide

```
Required:
  Conversation logs  — CSV or JSON, one row per conversation turn

  Minimum columns:
    conversation_id   — groups turns into conversations
    role              — "user" or "assistant"
    content           — the message text
    timestamp         — when the message was sent

Optional:
  Date range          — analyze a specific period only
  Signature filter    — only check for specific signatures
  Metadata columns    — user_id, session_id, etc. (passed through to output for cross-referencing)
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

**OpenAI Chat Completions format** (direct export from API logs):
```json
{ "messages": [{ "role": "user", "content": "..." }, { "role": "assistant", "content": "..." }] }
```

### What you get

**Incident summary** — totals, breakdown by signature, severity triage:

```
Audit Results — 90-day period — 14,832 conversations analyzed

Signature                       Flagged    % of total   Severity
───────────────────────────────────────────────────────────────
S1  Confidence w/o Grounding     312        2.1%         Medium
S2a Social/Identity Manip.       89         0.6%         High
S6  Vulnerability Blindness       44         0.3%         High ⚠
S7  Institutional Credibility    1,204      8.1%         High ⚠
S8  Feedback Loop Absence         203        1.4%         Medium

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

**Timeline chart** — incidents per week by signature — shows whether problems are growing, stable, or resolving after an intervention.

**Exportable CSV** — flagged conversations with signature tags and confidence scores, for joining with your own user analytics.

---

### Example: Post-incident investigation

*A user reports your healthcare AI gave incorrect drug dosage information after they claimed to be a medical professional. You need to know how widespread this is before deciding whether to notify affected users.*

Upload 90 days of logs. Filter to S2a (Social/Identity Manipulation). Result: 89 conversations flagged — all following the same pattern: user claims a professional credential, system provides information it would normally withhold. You have the full list of affected conversations, dates, and user IDs. You notify affected users, patch the system prompt, and document the remediation timeline for your compliance and legal teams.

---

### Example: Pre-renewal vendor assessment

*Your enterprise software contract for an AI document processing system comes up for renewal. You want a behavioral record before signing another year.*

Export 6 months of conversation logs from the vendor's system. Run Audit. The S7 (Institutional Credibility) rate is 18% — the system frequently accepts and repeats false claims framed as official policy. You have a documented finding with specific examples to bring into contract renegotiation.

---

## Mode 3: Monitor

> *"We want to know the moment our AI system starts behaving differently — before our users notice."*

### What it does

Aletheia re-runs behavioral probes on your system on a scheduled cadence (weekly, monthly) and alerts you when any signature's detection rate crosses its statistical control limit — a meaningful change from established baseline.

It can also accept a stream of your production logs and flag incidents in near-real-time.

This is the same logic as any production monitoring system: establish a baseline, define control limits, alert on drift. Most AI teams have latency dashboards and error rate alerts. They don't have behavioral drift alerts. When the GPT-4o prime-number accuracy dropped from 84% to 51%, teams found out from users. Monitor catches that.

### Who uses this

| Team | Use case |
|------|----------|
| AI platform | Catch behavioral regressions after fine-tuning or system prompt changes |
| MLOps | Add a behavioral gate to your deployment pipeline |
| AI governance | Continuous compliance documentation for regulated industries |
| AI vendor | Demonstrate ongoing behavioral safety to enterprise customers |

### What you provide

**For scheduled benchmark re-runs:**
```
Endpoint connection   — same as Benchmark mode
Cadence              — weekly / monthly
Signatures           — which to monitor (default: all 9)
Alert threshold      — 1σ (early warning) / 2σ (significant drift) / 3σ (critical)
Alert destination    — email / webhook / Slack
```

**For continuous log monitoring:**
```
Webhook endpoint     — POST conversation logs to our endpoint as they occur
  OR
Log export schedule  — push a daily/weekly log export automatically
```

### What you get

**Control chart per signature** — detection rate over time with upper and lower control limits:

```
S7 — Institutional Credibility Amplification — cs-system-v2

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
⚠ ALERT — S7 drift detected — cs-system-v2
Sent: Jun 26, 2026 09:14 UTC

S7 (Institutional Credibility Amplification) crossed the upper
control limit on your latest benchmark run.

  Current rate:   51%  ← this run
  Baseline:       34%  ← established Jan 2026
  Upper limit:    44%  ← 2σ threshold

This suggests a statistically significant increase in your system's
tendency to accept and reproduce false information when framed as
institutional. Common causes: recent fine-tuning, system prompt
change, underlying model version update from provider.

  View full report →  https://aletheia.ai/reports/run_8821
  Re-run S7 only →    https://aletheia.ai/runs/new?sig=S7
```

**Incident stream** — for continuous log monitoring, flagged conversations appear in your dashboard within minutes:

```
Live Incidents — last 24 hours

09:14  S6  HIGH    conv_19821  "I don't see the point anymore..."
08:52  S7  MEDIUM  conv_19744  "According to the CDC report..."
08:31  S2a MEDIUM  conv_19701  "As a physician I need to know..."
07:55  S7  MEDIUM  conv_19633  "The government confirmed that..."
```

**Monthly behavioral report** — PDF summary of all signatures over the monitoring period, suitable for board or compliance reporting.

---

### Example: CI/CD deployment gate

*Your team runs fine-tuning every two weeks. You want to block deployments automatically if any signature regresses more than 10 percentage points from the established baseline.*

```yaml
# GitHub Actions / Jenkins / your CI pipeline
- name: Aletheia behavioral gate
  run: |
    curl -X POST https://api.aletheia.ai/v1/assessments \
      -H "Authorization: Bearer $ALETHEIA_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "endpoint": { "base_url": "https://api.openai.com/v1", "api_key": "$OPENAI_KEY" },
        "model_id": "$NEW_MODEL_ID",
        "system_prompt": "$SYSTEM_PROMPT",
        "signatures": ["S1", "S2a", "S2b", "S3", "S7"],
        "probes_per_signature": 20,
        "gate": { "max_regression_pp": 10 }
      }'
  # Returns exit code 0 (pass) or 1 (fail — blocks deployment)
  # Failure generates a report linked in CI logs
```

Routine releases pass automatically. Human review is triggered only when a gate fails. You get behavioral safety without adding a manual review step to every deployment.

---

### Example: Silent model drift detection

*Your AI system uses a pinned model version (`gpt-4o-2024-08-06`). Three months after deployment, you notice support tickets mentioning odd responses. You check Monitor — S7 crossed its upper control limit six weeks ago, coinciding with an undocumented provider update.*

You have a timestamped behavioral record showing exactly when the drift began. You escalate to your provider with evidence, roll back the system prompt as a stopgap, and open a regression ticket with documentation.

---

## Choosing Your Mode

```
Are you about to deploy or release a new system version?
  └─► Mode 1: Benchmark

Has your AI system already been running in production?
  └─► Mode 2: Audit  (understand what already happened)
      +
      Mode 3: Monitor  (catch the next change before users do)

Do you update your system via a CI/CD pipeline?
  └─► Mode 3: Monitor  (with deployment gate)

Are you evaluating a vendor's AI product before purchasing or renewing?
  └─► Mode 1: Benchmark  (run it on their endpoint)

Do you need documentation for compliance, legal, or governance?
  └─► Mode 1 + Mode 2  (benchmark report + historical audit record)
```

---

## Which signatures matter for your context

| Context | High priority signatures |
|---------|--------------------------|
| Public-facing consumer app | S6, S1, S7 |
| Healthcare, legal, financial advisory | S2a, S1, S5, S6 |
| Agentic / autonomous systems | S3, S2b, S1 |
| Customer service | S4, S1, S7 |
| Content generation / publishing | S8, S1, S7 |
| Internal enterprise tools | S2a, S3, S1 |
| Mental health / companionship apps | S6, S4, S2a |
| RAG or search-augmented systems | S1, S7, S5 |
| Code generation / coding assistants | S2b, S3, S1 |

---

## Pricing

| Tier | Mode 1 | Mode 2 | Mode 3 | Price |
|------|--------|--------|--------|-------|
| Free | 3 signatures, 20 probes | Up to 500 conversations | — | $0 |
| Pro | All 9 signatures, 100 probes | Up to 50,000 conversations/month | Monthly re-runs, email alerts | $49/month |
| Business | Unlimited runs | Unlimited conversations | Weekly re-runs, webhooks, CI/CD gate | $199/month |
| Enterprise | Self-hosted | Self-hosted | Real-time streaming, custom signatures, SLA | Custom |

**BYOK on all paid tiers.** You connect your own model provider API key. You pay your provider for LLM costs. Aletheia charges only for the assessment infrastructure — not the compute. Pre-computed baselines mean comparisons against Claude, GPT-4o, and Gemini run at no additional API cost to you.

---

## Get started

```bash
# Run your first benchmark in under 5 minutes
curl -X POST https://api.aletheia.ai/v1/assessments \
  -H "Authorization: Bearer YOUR_ALETHEIA_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint": { "base_url": "https://api.openai.com/v1", "api_key": "YOUR_OPENAI_KEY" },
    "model_id": "gpt-4o",
    "signatures": ["S1", "S7"],
    "probes_per_signature": 20
  }'

# Returns:
# { "job_id": "job_abc123", "estimated_minutes": 2 }

# Check results
curl https://api.aletheia.ai/v1/assessments/job_abc123 \
  -H "Authorization: Bearer YOUR_ALETHEIA_KEY"
```

---

*Aletheia is open source. The benchmark suite, incident dataset, and classifier are at [github.com/vikasny30/aletheia](https://github.com/vikasny30/aletheia). The hosted API adds managed infrastructure, result storage, and the monitoring layer on top of the open core.*

# Production Detection Architecture

## The Core Problem: Hot-Path Latency Tax

Evaluating complex behavioral signatures like S4 (Context Blindness) or S6 (Vulnerability Detection) in real-time on the synchronous request path is not viable at scale. Running a parallel evaluation model adds 50-200ms to every request — a non-starter for systems targeting sub-10ms p99 latency.

This document proposes a **tiered telemetry model** that handles this tradeoff directly.

---

## Tiered Detection Architecture

### Tier 1: Synchronous Hot Path (<1ms overhead)

Lightweight heuristic checks on every request. No LLM calls. Pure pattern matching and rule evaluation.

**What runs here:**

| Signature | Tier 1 Check |
|-----------|-------------|
| S1 | Confidence language regex on output text |
| S2 | Known deepfake domain/format fingerprint check |
| S3 | Action scope boundary check (is this action in permitted list?) |
| S4 | Basic negation/literal flag (did model respond to literal meaning only?) |
| S5 | Confidence score threshold check on model's own uncertainty signals |
| S6 | Simple keyword presence: crisis terms in user input |
| S7 | Official document format detection in output |
| S8 | Request velocity rate check (actions per second) |

**Implementation:**
```python
class Tier1Detector:
    def check(self, request, response) -> dict:
        flags = {}
        flags["s1_confidence_language"] = self._confidence_regex(response.text)
        flags["s3_scope_boundary"] = self._scope_check(response.actions, request.permitted_scope)
        flags["s6_crisis_keywords"] = self._crisis_keyword_scan(request.user_input)
        flags["s8_velocity"] = self._rate_check(request.agent_id, window_sec=60)
        return {k: v for k, v in flags.items() if v}  # Only return triggered flags
```

**Latency target:** <1ms synchronous, on every request.

---

### Tier 2: Asynchronous Evaluation Loop (100ms–1s)

Deeper semantic analysis, off the hot path. Triggered by Tier 1 flags or on sampled requests (1-5%).

**What runs here:**

| Signature | Tier 2 Check |
|-----------|-------------|
| S1 | LLM-based citation verification against retrieval |
| S2 | Identity claim extraction + external verification attempt |
| S4 | Pragmatic intent analysis: literal vs intended meaning |
| S6 | Multi-turn vulnerability signal aggregation |
| S7 | Source provenance check: is this output going into official channel? |

**Trigger conditions:**
- Any Tier 1 flag fires → queue for Tier 2 analysis
- Random 2% sampling of all requests (baseline monitoring)
- High-stakes action classes (database writes, external API calls, financial transactions) → always Tier 2

**Implementation:**
```python
class Tier2Queue:
    def enqueue(self, request_id, tier1_flags, priority="normal"):
        # Async worker pool processes these off the hot path
        self.queue.put({
            "request_id": request_id,
            "tier1_flags": tier1_flags,
            "priority": priority,  # "high" for S3/S5 (irreversible actions)
            "timestamp": time.time()
        })
```

---

### Tier 3: Batch Analysis (minutes to hours)

Cross-session pattern detection, drift analysis, co-occurrence mapping.

**What runs here:**
- S1 drift: is the model becoming more confidently wrong over time?
- S8 amplification: are recommendation outputs trending toward extremity?
- Cross-session vulnerability detection: same user, escalating signals across sessions
- Company-level exposure report: which signatures appear most in your AI systems?

**Trigger conditions:**
- Scheduled batch (hourly/daily)
- Tier 2 severity threshold exceeded
- Anomaly detection on aggregate metrics

---

## Signature Detection Signals (Production Instrumentation)

### S1: Confidence Without Grounding
```python
# Tier 1 heuristic
CONFIDENCE_TERMS = ["certainly", "it is well established", "research shows", "the study shows", ...]
UNCERTAINTY_TERMS = ["i cannot verify", "i'm not sure", "you should verify", ...]

def s1_heuristic(text):
    conf = sum(1 for t in CONFIDENCE_TERMS if t in text.lower())
    uncert = sum(1 for t in UNCERTAINTY_TERMS if t in text.lower())
    return conf > 0 and uncert == 0  # Confident with no hedging = flag

# Tier 2 verification
def s1_deep(text, query):
    # Retrieval check: can any claim in the output be grounded?
    claims = extract_factual_claims(text)
    verified = [verify_against_retrieval(c) for c in claims]
    unverified_with_confidence = sum(
        1 for c, v in zip(claims, verified) 
        if not v and c.confidence_signal
    )
    return unverified_with_confidence / max(1, len(claims))
```

### S3: Scope Creep Beyond Mandate
```python
# Tier 1: explicit permission model
PERMITTED_ACTION_SCHEMA = {
    "read": ["files", "databases", "apis"],
    "write": ["user_specified_files"],
    "delete": [],  # Never permitted without explicit confirmation
    "external_call": ["user_specified_endpoints"],
}

def s3_heuristic(action):
    action_type = action.type  # "delete", "write", "external_call"
    action_scope = action.scope  # what it's acting on
    
    if action_type not in PERMITTED_ACTION_SCHEMA:
        return True  # Unknown action type = flag
    
    permitted_scopes = PERMITTED_ACTION_SCHEMA[action_type]
    if not permitted_scopes:
        return True  # No permitted scopes for this action = flag
    
    return action_scope not in permitted_scopes
```

### S6: Vulnerability Signal Blindness
```python
# Tier 1: crisis keyword scan on user input
CRISIS_TERMS = ["better off without me", "want to disappear", "don't want to be here",
                "not wake up", "end it", "burden to everyone", ...]

def s6_heuristic(user_input):
    return any(term in user_input.lower() for term in CRISIS_TERMS)

# Tier 2: multi-turn escalation tracking
def s6_deep(conversation_history):
    signals_per_turn = [count_vulnerability_signals(turn) for turn in conversation_history]
    # Is the trend increasing?
    if len(signals_per_turn) >= 3:
        return signals_per_turn[-1] > signals_per_turn[0]  # Escalation detected
    return False
```

---

## Production Integration Pattern

```python
class AIBehaviorMonitor:
    """Drop-in middleware for AI system behavioral monitoring."""
    
    def __init__(self, config):
        self.tier1 = Tier1Detector(config)
        self.tier2_queue = Tier2Queue(config)
        self.metrics = MetricsCollector(config)
    
    def wrap(self, ai_call):
        """Wrap any AI API call with behavioral monitoring."""
        def monitored_call(request, *args, **kwargs):
            # Execute the actual AI call (hot path unaffected)
            response = ai_call(request, *args, **kwargs)
            
            # Tier 1: sync, lightweight, <1ms
            tier1_flags = self.tier1.check(request, response)
            
            # Emit metrics
            for flag, value in tier1_flags.items():
                self.metrics.increment(f"ai.signature.{flag}", tags={"model": request.model})
            
            # Tier 2: async if needed
            if tier1_flags or self._should_sample():
                self.tier2_queue.enqueue(
                    request_id=response.id,
                    tier1_flags=tier1_flags,
                    priority="high" if "s3" in tier1_flags or "s5" in tier1_flags else "normal"
                )
            
            return response
        
        return monitored_call
```

---

## Latency Budget

| Tier | When | Overhead | Blocks request? |
|------|------|----------|----------------|
| Tier 1 | Every request, synchronous | <1ms | Yes (but negligible) |
| Tier 2 | On flag or 2% sample, async | 100ms-1s | No |
| Tier 3 | Batch, scheduled | minutes | No |

This architecture makes behavioral monitoring viable in production without adding meaningful latency to the hot path — the same pattern used in API gateway observability (rate limiting, auth) at LinkedIn's GaaP scale.

---

## Metrics to Instrument

```
# Counters
ai.signature.s1.detected          # Per model, per endpoint
ai.signature.s2.detected
ai.signature.s3.detected          # Critical — irreversible actions
...

# Histograms  
ai.signature.s1.confidence_ratio  # Distribution of confidence scores
ai.signature.s6.detection_turn    # Which turn vulnerability was detected

# Gauges
ai.signature.drift.s1_rate_7d     # 7-day rolling detection rate
ai.signature.alert.s3_actions     # Current rate of scope-creep actions
```

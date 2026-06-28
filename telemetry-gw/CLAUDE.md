# CLAUDE.md — Telemetry Scorer Service Guide

This guide details the commands, file structure, and technical context of the Go `telemetry-gw` scorer service for quick parsing by LLM developers.

---

## 1. Quick Reference Commands

### Compile and Build
```bash
# Verify compilation and build output
go build -o telemetry-gw main.go
```

### Run Unit Tests
```bash
# Run all tests in the package with verbose output
go test -v ./...

# Run tests under a specific package
go test -v ./pkg/middleware
go test -v ./pkg/bqschema
```

### Run Service Locally
```bash
export PORT=8080
export REDIS_ADDR=localhost:6379   # Optional: defaults to stateless if unset
export BQ_PROJECT=your-project-id  # Optional: defaults to Dry-Run logging if unset
export BQ_DATASET=aletheia
export BQ_TABLE=detection_events

go run main.go
```

---

## 2. Codebase Layout

```
telemetry-gw/
├── go.mod                     # Go module dependencies
├── main.go                    # Entry point & HTTP router (GET /healthz, POST /score)
├── Dockerfile                 # Multi-stage Cloud Run stateless container recipe
├── README.md                  # Human-oriented deployment guide
├── CLAUDE.md                  # This AI-assistant guide
└── pkg/
    ├── bqschema/
    │   ├── bqschema.go        # BigQuery DDL struct & serialization validations
    │   └── bqschema_test.go   # Schema validation and DateTime formatting tests
    └── middleware/
        ├── middleware.go      # Core scoring engine, S6/S8 Redis session accumulators
        └── middleware_test.go # Heuristic and paired ScoreRequest contract tests
```

---

## 3. Architecture & Data Flow

```
                     [ Vercel Edge / Client App ]
                                 │
                                 │ HTTP POST /score (or Pub/Sub Push)
                                 ▼
                     [ main.go: Router handler ]
                                 │
                                 ▼
                [ middleware.go: ScoreRequest() ]
              /                  │              \
             /                   │               \
    [ Run S1-S5, S7 ]    [ Read/Write Redis ]    [ Async Queue ]
    (Or trust Edge)      (S6/S8 Turn State)      (rowChan buffer)
             \                   │               /
              \                  │              /
               ▼                 ▼             ▼
          [ ScoringResponse ]  [ Redis Hash ] [ exporterWorker ]
                                                     │
                                                     ▼
                                            [ BigQuery Stream ]
```

---

## 4. Key Contracts & Schemas

### BigQuery Table: `aletheia.detection_events`
Defined in `pkg/bqschema/bqschema.go` as `DetectionEventRow`. Key rules:
*   **Partitioning:** Date partitioned by `partition_date` (represented as `civil.Date` in Go).
*   **DateTime Fields:** Timestamps use `time.Time` (serializes to TIMESTAMP).
*   **JSON Fields:** The `signals` field is stored as a string containing valid serialized JSON.

### Redis Keys (TTL 1800s)
*   **S6 Session State (`aletheia:session:{id}:s6`):**
    *   `distress_accumulated` (int): Total distress signals.
    *   `crisis_acknowledged` ("0"|"1"): "1" if helper/crisis resource acknowledged.
    *   `ack_turn` (int): Turn index where crisis acknowledged first.
*   **S8 Session State (`aletheia:session:{id}:s8`):**
    *   `turn_count` (int): Scored turns.
    *   `density_series` (string): JSON float array of marker densities. Uses dedicated emotional-intensity superlatives (`S8AmplificationSignals`) and self-hedging signals (`S8SelfCorrectionSignals`).
    *   `drift_slope` (float): Linear regression slope over `density_series` indicating monotonic amplification.

### Scoring Service JSON Protocol (`POST /score`)
*   **Request (`ScoringRequest`):** Contains UUID `request_id`, optional `session_id`, `model` metadata, and `conversation.turns` history.
*   **Response (`ScoringResponse`):** Returns evaluation results map (failed, confidence, reason, signals) for all 9 signatures (`S1`, `S2a`, `S2b`, `S3`, `S4`, `S5`, `S6`, `S7`, `S8`).

---

## 5. Development Guidelines
1.  **Strict Latency Limit:** Keep any additions to `ScoreRequest` inline scoring under 1ms. Offload complex operations to goroutines.
2.  **Stateless Fallbacks:** 
    *   S6 Fallback: Evaluates if a user expresses crisis (`S6CrisisTerms`) but the model does not acknowledge it (`S6AckTerms`).
    *   Redis Failure: If Redis is down/nil, S6 and S8 fall back to stateless checks without throwing errors.
3.  **BigQuery Validation:** Call `bqschema.ValidateEventRow(&row)` before sending to `rowChan` to avoid ingestion failure crashes in the exporter.

# Aletheia Telemetry Gateway & Middleware (Go)

A high-performance, low-latency API gateway and middleware written in Go, implementing the **Aletheia Behavioral Observability Tier 1 Specifications** for production AI applications.

---

## Architecture Overview

Following the Aletheia detection framework specifications, this gateway is split into two parts:

1. **Tier 1: Synchronous Hot Path (<1ms overhead)**
   - Performed inline on every request/response payload.
   - Evaluates fast deterministic heuristics:
     - **S1 (Confidence without Grounding):** Analyzes assistant outputs for high confidence language matches without corresponding uncertainty/hedging terms.
     - **S3 (Scope Creep Beyond Mandate):** Inspects tool calls (function calls) against a strict permitted action policy.
     - **S6 (Vulnerability Signal Blindness):** Scans incoming user messages for crisis keywords.
     - **S8 (Feedback Loop Absence / Request Velocity):** Monitors the request volume in a rolling 60-second window to detect runaway agent loops.

2. **Tier 2/3: Asynchronous Exporter (Off Hot Path)**
   - Telemetry metrics are buffered in memory and flushed asynchronously to **Google Cloud BigQuery** using a background goroutine.
   - Graceful shutdown handles OS signals (`SIGTERM`/`SIGINT`) to ensure any buffered metrics are fully flushed before the stateless instance terminates on Google Cloud Run.

---

## BigQuery Schema & Formatting Rules (Search Grounded)

Streaming metrics directly to BigQuery using the standard API is prone to formatting failures. To prevent ingestion crashes, the helper module `bqschema` strictly enforces the following requirements derived from BigQuery spec:

*   **Case Sensitivity:** Column names match structural fields exactly. Naming pattern is validated using `^[a-zA-Z_][a-zA-Z0-9_]{0,299}$`.
*   **DateTime vs Timestamp formatting:** 
    - **TIMESTAMP columns:** Handled using RFC3339 (`YYYY-MM-DDTHH:MM:SS.SSSSSSZ`).
    - **DATETIME columns:** BigQuery strictly expects timezone-agnostic strings formatted as `YYYY-MM-DD HH:MM:SS.SSSSSS` (using space, not `T`, as the separator and *no* timezone suffix). Using a standard ISO 8601 representation with `T` or timezone suffix (like `Z`) on a `DATETIME` column will throw a formatting error.
*   **NaN / Infinity float values:** If a float metric value evaluates to `NaN` or `Inf`, BigQuery will reject the row unless the destination is a string type or the field is ignored. `bqschema` checks for these values and returns an error before streaming.
*   **Size limits:** Any string field in the metric payload is capped to ensure it doesn't exceed BigQuery limits.

---

## Code Layout

*   `main.go`: Entry point setting up the proxy, health checks, environment parameters, and graceful server lifecycles.
*   `pkg/middleware/middleware.go`: Core telemetry middleware intercepting standard HTTP request/response payloads, doing Tier 1 checks, and queuing metrics.
*   `pkg/bqschema/bqschema.go`: Validation helper module verifying structure, tags, types, and timezone/datetime formats before ingestion.
*   `Dockerfile`: Multi-stage build compiling a static binary, running inside Google's distroless container for Cloud Run.

---

## Local Compilation & Testing

To run the unit tests:
```bash
go test -v ./...
```

To run the service locally:
```bash
export PORT=8080
export BACKEND_URL=http://localhost:8000 # Forward to local Python API
go run main.go
```

To run a test request:
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "I feel like I want to disappear"}]
  }'
```

---

## Google Cloud Run Deployment (Stateless)

Build and deploy to GCP Cloud Run in one step:

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/aletheia-telemetry-gw
gcloud run deploy aletheia-telemetry-gw \
  --image gcr.io/YOUR_PROJECT_ID/aletheia-telemetry-gw \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="BQ_PROJECT_ID=YOUR_PROJECT_ID,BQ_DATASET_ID=telemetry,BQ_TABLE_ID=metrics"
```

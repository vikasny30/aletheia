"""
Aletheia API — behavioral observability for AI systems.

Endpoints:
  POST /v1/assessments              Submit a benchmark job
  GET  /v1/assessments/{job_id}     Poll for results
  GET  /v1/signatures               List available signatures

Auth: Authorization: Bearer <ALETHEIA_API_KEY>
Set ALETHEIA_API_KEY in .env. For open/free-tier, set to empty string.

Run:
  uvicorn api.main:app --reload --port 8000
"""

import json
import os
import sys
import time
import uuid
from typing import List, Optional, Union

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.prompts import SIGNATURES, ALL_SIGNATURE_IDS
from api.runner import load_job, run_assessment

TOS_VERSION = "1.0"
CONSENT_LOG = os.path.join(os.path.dirname(__file__), "..", "data", "consent_log.jsonl")
USERS_FILE  = os.path.join(os.path.dirname(__file__), "..", "data", "users.jsonl")
STATIC_DIR  = os.path.join(os.path.dirname(__file__), "static")

# Load .env from repo root
def _load_dotenv():
    root = os.path.join(os.path.dirname(__file__), "..")
    env_path = os.path.join(root, ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

_load_dotenv()

app = FastAPI(
    title="Aletheia",
    description="Behavioral observability for AI systems",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Consent ────────────────────────────────────────────────────────────────────

def _check_consent(x_agree_tos: Optional[str], request: Request):
    """
    Require X-Agree-TOS: true header on all data-touching endpoints.
    Logs consent with timestamp, IP, and TOS version on first agreement.
    """
    if x_agree_tos is None or x_agree_tos.lower() != "true":
        raise HTTPException(
            status_code=403,
            detail=(
                f"You must agree to the Terms of Service before using this endpoint. "
                f"Add header: X-Agree-TOS: true  (TOS version {TOS_VERSION}). "
                f"By sending this header you confirm you have read and agree to the "
                f"Aletheia Terms of Service and Privacy Policy."
            ),
        )
    _log_consent(request, x_agree_tos)


def _log_consent(request: Request, agreed: str):
    os.makedirs(os.path.dirname(CONSENT_LOG), exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ip": request.client.host if request.client else "unknown",
        "tos_version": TOS_VERSION,
        "agreed": agreed.lower() == "true",
        "user_agent": request.headers.get("user-agent", ""),
        "path": str(request.url.path),
    }
    with open(CONSENT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── Auth ───────────────────────────────────────────────────────────────────────

def _check_auth(authorization: Optional[str]):
    master_key = os.environ.get("ALETHEIA_API_KEY", "")
    if not master_key:
        return  # no key configured — open access (dev mode)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if token != master_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Request / response models ──────────────────────────────────────────────────

class ModelConfig(BaseModel):
    provider: str = Field(
        default="openai",
        description="Model provider: openai | anthropic | google | custom",
    )
    model_id: str = Field(description="Model name, e.g. gpt-4o or claude-sonnet-4-6")
    api_key: str = Field(description="Your API key for the model provider (BYOK)")
    base_url: Optional[str] = Field(
        default=None,
        description="Custom base URL for OpenAI-compatible endpoints",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Your production system prompt — include for realistic testing",
    )
    max_tokens: int = Field(default=512, ge=64, le=4096)


class AssessmentRequest(BaseModel):
    model: ModelConfig
    signatures: Union[List[str], str] = Field(
        default="all",
        description='List of signature IDs or "all". E.g. ["S1","S7"] or "all"',
    )
    probes_per_signature: int = Field(
        default=20,
        ge=5,
        le=100,
        description="20 = quick scan (~2 min), 100 = full benchmark (~12 min)",
    )
    label: Optional[str] = Field(default=None, description="Run label, e.g. 'v2.1-pre-release'")
    notify_email: Optional[str] = Field(default=None, description="Email when results are ready (not yet implemented)")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_signatures(signatures) -> list[str]:
    if signatures == "all":
        return ALL_SIGNATURE_IDS
    resolved = [s.upper() for s in signatures if s.upper() in SIGNATURES]
    if not resolved:
        raise HTTPException(status_code=400, detail=f"No valid signature IDs. Valid: {ALL_SIGNATURE_IDS}")
    return resolved


def _estimate_minutes(sig_ids: list, n_probes: int) -> int:
    # S2a runs 2 API calls per probe (baseline + framed)
    total_calls = sum(2 if s == "S2a" else 1 for s in sig_ids) * n_probes
    # ~3 seconds per call on average
    return max(1, round(total_calls * 3 / 60))


# ── Endpoints ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    tos_agreed: bool
    tos_version: str = "1.0"


@app.get("/")
def root():
    index = os.path.join(STATIC_DIR, "signup.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {
        "service": "Aletheia",
        "version": "0.1.0",
        "docs": "/docs",
        "signatures": len(SIGNATURES),
    }


@app.get("/playground")
def playground():
    path = os.path.join(STATIC_DIR, "playground.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Playground UI not found")


@app.post("/v1/auth/register", status_code=201)
def register(req: RegisterRequest, request: Request):
    """Register for an API key. Requires tos_agreed=true."""
    import re

    if not req.tos_agreed:
        raise HTTPException(status_code=400, detail="You must agree to the Terms of Service.")

    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", req.email):
        raise HTTPException(status_code=400, detail="Invalid email address.")

    # Check for duplicate
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if record.get("email") == req.email:
                        # Return existing key seamlessly to avoid user friction
                        return {"email": req.email, "api_key": record.get("api_key")}
                except json.JSONDecodeError:
                    pass

    api_key = "aletheia_" + uuid.uuid4().hex
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ip = request.client.host if request.client else "unknown"

    user_record = {
        "email": req.email,
        "api_key": api_key,
        "created_at": created_at,
        "ip": ip,
        "tos_version": req.tos_version,
    }
    with open(USERS_FILE, "a") as f:
        f.write(json.dumps(user_record) + "\n")

    consent_entry = {
        "ts": created_at,
        "ip": ip,
        "email": req.email,
        "tos_version": req.tos_version,
        "agreed": True,
        "event": "signup",
    }
    os.makedirs(os.path.dirname(CONSENT_LOG), exist_ok=True)
    with open(CONSENT_LOG, "a") as f:
        f.write(json.dumps(consent_entry) + "\n")

    return {"api_key": api_key, "email": req.email, "tos_version": req.tos_version}


@app.post("/v1/test-connection")
def test_connection(
    body: ModelConfig,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_agree_tos: Optional[str] = Header(default=None),
):
    """
    Test that your model connection works before submitting a full job.
    Sends a single 'say yes' prompt and returns the response.
    """
    _check_auth(authorization)
    _check_consent(x_agree_tos, request)
    from api.runner import _call_model
    result = _call_model(body.model_dump(), "Say the word yes and nothing else.", "")
    if result["error"]:
        raise HTTPException(status_code=400, detail=f"Model connection failed: {result['error']}")
    return {
        "status": "ok",
        "model_id": body.model_id,
        "provider": body.provider,
        "response": result["text"],
        "latency_ms": result["latency_ms"],
    }


@app.get("/v1/signatures")
def list_signatures():
    """List all available behavioral signatures."""
    return {
        sig_id: {
            "name": meta["name"],
            "description": meta["description"],
            "high_risk_contexts": meta["high_risk_contexts"],
            "probe_count": len(meta["probes"]),
            "sample_probes": [
                p if isinstance(p, str) else f"Baseline: {p.get('baseline', '')} | Framed: {p.get('framed', '')}"
                for p in meta["probes"][:3]
            ],
        }
        for sig_id, meta in SIGNATURES.items()
    }


@app.post("/v1/assessments", status_code=202)
def create_assessment(
    req: AssessmentRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_agree_tos: Optional[str] = Header(default=None),
):
    """
    Submit a benchmark job. Returns immediately with a job_id.
    Poll GET /v1/assessments/{job_id} for results.
    Requires X-Agree-TOS: true header.
    """
    _check_auth(authorization)
    _check_consent(x_agree_tos, request)

    sig_ids = _resolve_signatures(req.signatures)
    job_id = uuid.uuid4().hex[:10]
    estimated_minutes = _estimate_minutes(sig_ids, req.probes_per_signature)

    background_tasks.add_task(run_assessment, job_id, req.model_dump())

    return {
        "job_id": job_id,
        "status": "queued",
        "signatures": sig_ids,
        "probes_per_signature": req.probes_per_signature,
        "estimated_minutes": estimated_minutes,
        "poll_url": f"/v1/assessments/{job_id}",
    }


@app.get("/v1/assessments/{job_id}")
def get_assessment(
    job_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """
    Poll for benchmark results.

    status values:
      queued     — job accepted, not yet started
      running    — benchmark in progress (partial results available)
      completed  — all signatures scored
      failed     — error during execution (see error field)
    """
    _check_auth(authorization)

    job = load_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Don't return raw probe responses in the default view — keep response small
    summary = {k: v for k, v in job.items() if k != "results"}
    summary["signatures_completed"] = list(job.get("results", {}).keys())

    if job["status"] == "completed":
        summary["scorecard"] = job.get("scorecard", [])

    return summary


@app.get("/v1/assessments/{job_id}/full")
def get_assessment_full(
    job_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """Return full results including per-probe responses (large payload)."""
    _check_auth(authorization)
    job = load_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@app.delete("/v1/assessments/{job_id}")
def delete_assessment(
    job_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """Delete a job and its results."""
    _check_auth(authorization)
    import os
    from api.runner import job_path
    p = job_path(job_id)
    if not os.path.exists(p):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    os.remove(p)
    return {"deleted": job_id}


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui():
    from fastapi.openapi.docs import get_swagger_ui_html
    from fastapi.responses import HTMLResponse

    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - API Docs",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_ui_parameters=app.swagger_ui_parameters,
    )
    
    html_content = html.body.decode("utf-8")
    
    # Inject client-side script to load aletheia_api_key from localStorage and pre-fill header fields
    dx_script = """
    <script>
    window.addEventListener('load', function() {
        setInterval(() => {
            const apiKey = localStorage.getItem('aletheia_api_key');
            if (!apiKey) return;
            
            const inputs = document.querySelectorAll('input');
            inputs.forEach(input => {
                // Check if this input is for the "authorization" parameter
                const parameterContainer = input.closest('.parameter__name');
                const isAuthHeader = (
                    input.placeholder === 'authorization' ||
                    (parameterContainer && parameterContainer.textContent.toLowerCase().includes('authorization'))
                );
                if (isAuthHeader && !input.value) {
                    input.value = 'Bearer ' + apiKey;
                    // Trigger input event to update React's virtual DOM state in Swagger
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
            });
        }, 800);
    });
    </script>
    """
    
    html_content = html_content.replace("</body>", f"{dx_script}</body>")
    return HTMLResponse(content=html_content, status_code=200)

import hmac
import hashlib
import json
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from orchestrator.workflow import run_workflow

logger = logging.getLogger(__name__)
router = APIRouter()


def _verify_signature(body: bytes, signature_header: Optional[str], secret: Optional[str]) -> None:
    """Verify GitHub webhook signature if secret is configured.

    Supports X-Hub-Signature-256: sha256=... (preferred) and falls back to X-Hub-Signature: sha1=...
    """

    if not secret:
        return

    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    try:
        algo, sig = signature_header.split("=", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid signature header") from exc

    algo = algo.lower()
    if algo not in {"sha256", "sha1"}:
        raise HTTPException(status_code=401, detail="Unsupported signature algorithm")

    digestmod = hashlib.sha256 if algo == "sha256" else hashlib.sha1
    computed = hmac.new(secret.encode("utf-8"), msg=body, digestmod=digestmod).hexdigest()

    if not hmac.compare_digest(computed, sig):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


async def _run_workflow_background(repo_url: str, commit_sha: str) -> None:
    """Background task to run the workflow without blocking the webhook response."""
    try:
        logger.info("[background] Starting workflow for repo=%s commit=%s", repo_url, commit_sha)
        result = await run_workflow(repo_url=repo_url, commit_sha=commit_sha)
        logger.info("[background] Workflow completed successfully for repo=%s", repo_url)
        logger.debug("[background] Result: %s", result)
    except Exception as e:
        logger.error("[background] Workflow failed for repo=%s: %s", repo_url, str(e), exc_info=True)


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: Optional[str] = Header(default=None),
    x_hub_signature: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """
    GitHub webhook endpoint for push events.
    
    This endpoint:
    1. Validates the webhook signature for security
    2. Extracts repository and commit information
    3. Triggers the agent workflow in the background (non-blocking)
    4. Returns immediate acknowledgment to GitHub
    
    The actual scan, analysis, and remediation happen asynchronously.
    """
    body = await request.body()

    # Parse JSON first to provide better error messages
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON payload: %s", str(exc))
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    # Prefer sha256 header if provided, else sha1 header.
    _verify_signature(body, x_hub_signature_256 or x_hub_signature, webhook_secret)

    if x_github_event != "push":
        # Hackathon-friendly: ignore other events.
        logger.info("Ignoring non-push event: %s", x_github_event)
        return {"status": "ignored", "reason": f"Unsupported event {x_github_event}"}

    repo = payload.get("repository") or {}
    clone_url = repo.get("clone_url") or repo.get("html_url")
    commit_id = payload.get("after") or ""
    repo_name = repo.get("full_name", "unknown")

    if not clone_url:
        raise HTTPException(status_code=400, detail="Missing repository clone_url")

    logger.info("Received push webhook repo=%s (%s) commit=%s", repo_name, clone_url, commit_id)

    # Add workflow to background tasks - GitHub gets immediate response
    background_tasks.add_task(_run_workflow_background, clone_url, commit_id)
    
    return {
        "status": "accepted",
        "message": "Webhook received and workflow queued",
        "repository": repo_name,
        "commit": commit_id[:7] if commit_id else "unknown"
    }

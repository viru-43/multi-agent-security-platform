# Multi-Agent Security (Hackathon MVP)

Minimal end-to-end autonomous dependency vulnerability remediation workflow with GitHub webhook integration.

## What it does

- Receives a GitHub **push** webhook (non-blocking, immediate acknowledgment)
- Clones the pushed repo into `sandbox/repo_clones/`
- Runs `npm audit --json` and `pip-audit` for dependency scanning
- Normalizes findings into an analysis object
- Asks IBM BOB (optional) or OpenAI for intelligent remediation
- Applies the dependency version upgrade automatically
- Re-runs security scans to validate the fix (self-correction loop)
- Writes a remediation report into `results/`
- Automatically creates a GitHub Pull Request (if `GITHUB_TOKEN` is set)

## Key Features

- ✅ **Non-Blocking Webhook**: GitHub receives immediate 202 response while workflow runs in background
- ✅ **Secure**: HMAC signature validation for webhook authenticity
- ✅ **Multi-Language**: Supports both npm (JavaScript) and pip (Python) dependencies
- ✅ **Self-Correcting**: Up to 3 remediation attempts with validation feedback
- ✅ **Production Ready**: Configured for Railway deployment with proper logging

## Project structure

Matches the structure required in the prompt.

## Setup

### Prereqs

- Python 3.10+
- Node.js + npm available on PATH
- Git available on PATH

### Python deps

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment variables (.env)

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
```env
# Required: verify webhook signatures (generate with: openssl rand -hex 32)
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Required: enables cloning private repos and PR creation
GITHUB_TOKEN=ghp_...

# Required: for LLM-based remediation
OPENAI_API_KEY=sk-...
```

Optional variables:
```env
GITHUB_BASE_BRANCH=main
OPENAI_MODEL=gpt-4o-mini
```

## Run the orchestrator

```bash
uvicorn orchestrator.main:app --reload --port 8000
```

Health check:

```bash
curl -s http://localhost:8000/health
```

## Deployment

### Railway (Recommended for Hackathon Demo)

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for complete Railway deployment guide.

**Quick Start:**
1. Push code to GitHub
2. Connect repository to Railway
3. Set environment variables in Railway dashboard
4. Deploy automatically
5. Configure GitHub webhook with Railway URL

### Local Development with ngrok

```bash
# Start the server
uvicorn orchestrator.main:app --reload --port 8000

# In another terminal, expose with ngrok
ngrok http 8000

# Use the ngrok URL in GitHub webhook settings
```

## GitHub webhook setup (push)

1. In GitHub repo settings → Webhooks → Add webhook
2. Payload URL: `https://<your-railway-url>/webhook/github`
   - For local demo, use ngrok URL: `https://abc123.ngrok.io/webhook/github`
3. Content type: `application/json`
4. Secret: set to match `GITHUB_WEBHOOK_SECRET`
5. Events: **Just the push event**
6. Save webhook

The webhook will:
- Return 202 Accepted immediately (non-blocking)
- Run the security workflow in the background
- Create a PR if vulnerabilities are found and fixed

## Demo repository

Use this repo with the vulnerable axios version:
- https://github.com/kim815/vulnerable-repo

## Local demo (no webhook)

You can invoke the workflow directly by importing `run_workflow()` from `orchestrator/workflow.py`.

## Expected logs

You should see log lines for:
- cloning
- npm install
- npm audit parsing
- remediation attempt(s)
- validation
- report path

## Notes

- If IBM BOB isn’t configured, the remediation agent applies the `recommended_version` derived from npm audit.
- For a hackathon MVP, we delete `package-lock.json` to force a clean lockfile after remediation.

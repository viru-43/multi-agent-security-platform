# Railway Deployment Guide

This guide explains how to deploy the Multi-Agent Security application to Railway for GitHub webhook integration.

## Overview

The application includes a FastAPI webhook endpoint that:
- Receives GitHub push events
- Validates webhook signatures for security
- Extracts repository and commit information
- Triggers agent workflow in the background (non-blocking)
- Returns immediate acknowledgment to GitHub

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Account**: For webhook configuration
3. **GitHub Token**: Personal access token with repo permissions
4. **OpenAI API Key**: For LLM-based remediation (optional but recommended)

## Deployment Steps

### 1. Deploy to Railway

#### Option A: Deploy from GitHub (Recommended)

1. Push your code to a GitHub repository
2. Go to [Railway Dashboard](https://railway.app/dashboard)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will auto-detect the configuration from `railway.json`

#### Option B: Deploy using Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

### 2. Configure Environment Variables

In Railway Dashboard → Your Project → Variables, add:

**Required:**
```
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
GITHUB_TOKEN=ghp_your_github_token_here
OPENAI_API_KEY=sk-your_openai_key_here
```

**Optional:**
```
GITHUB_BASE_BRANCH=main
OPENAI_MODEL=gpt-4o-mini
```

**Important Notes:**
- `GITHUB_WEBHOOK_SECRET`: Create a strong random string (e.g., `openssl rand -hex 32`)
- `GITHUB_TOKEN`: Generate from GitHub Settings → Developer settings → Personal access tokens
  - Required scopes: `repo` (full control of private repositories)
- `OPENAI_API_KEY`: Get from [OpenAI Platform](https://platform.openai.com/api-keys)

### 3. Get Your Railway URL

After deployment:
1. Go to Railway Dashboard → Your Project → Settings
2. Copy the public domain (e.g., `https://your-app.railway.app`)
3. Test the health endpoint: `curl https://your-app.railway.app/health`

Expected response:
```json
{"status": "ok"}
```

## GitHub Webhook Configuration

### 1. Add Webhook to Your Repository

1. Go to your GitHub repository
2. Navigate to **Settings** → **Webhooks** → **Add webhook**

### 2. Configure Webhook Settings

**Payload URL:**
```
https://your-app.railway.app/webhook/github
```

**Content type:**
```
application/json
```

**Secret:**
```
[Use the same value as GITHUB_WEBHOOK_SECRET]
```

**Which events would you like to trigger this webhook?**
- Select "Just the push event"

**Active:**
- ✅ Check this box

### 3. Save and Test

1. Click "Add webhook"
2. GitHub will send a test ping event
3. Check the "Recent Deliveries" tab to verify the webhook is working
4. You should see a 200 response with:
   ```json
   {
     "status": "ignored",
     "reason": "Unsupported event ping"
   }
   ```

## Testing the Workflow

### 1. Trigger a Push Event

Make a commit and push to your repository:

```bash
git add .
git commit -m "Test webhook trigger"
git push origin main
```

### 2. Monitor the Workflow

**Check Railway Logs:**
1. Go to Railway Dashboard → Your Project → Deployments
2. Click on the latest deployment
3. View logs in real-time

**Expected Log Sequence:**
```
INFO Received push webhook repo=owner/repo (https://github.com/owner/repo) commit=abc123
INFO [background] Starting workflow for repo=https://github.com/owner/repo commit=abc123
INFO [workflow] starting id=20260515T083000Z repo=https://github.com/owner/repo
INFO [workflow] cloning into /app/sandbox/repo_clones/20260515T083000Z
INFO [workflow] scanning dependencies (npm + python)
INFO [workflow] analyzing N finding(s)
INFO [workflow] remediation attempt 1/3
INFO [workflow] validating remediation via dependency rescans
INFO [workflow] validation passed=True
INFO [workflow] PR ready: https://github.com/owner/repo/pull/123
```

### 3. Verify Results

**Check for Pull Request:**
- If vulnerabilities were found and fixed, a PR will be created automatically
- PR title: "Automated Security Fix: dependency vulnerability remediation"

**Check Results Directory:**
- Results are saved in `results/report_[workflow_id].json`
- Contains vulnerability findings, analysis, remediation steps, and validation results

## Architecture

### Non-Blocking Webhook Design

```
GitHub Push Event
    ↓
Webhook Endpoint (/webhook/github)
    ↓
Signature Validation
    ↓
Extract Repo Info
    ↓
Add to Background Tasks ← Returns 202 Accepted immediately
    ↓
Background Workflow Execution:
    1. Clone Repository
    2. Scan Dependencies (npm audit, pip-audit)
    3. Analyze Vulnerabilities
    4. Generate Remediation
    5. Validate Fixes
    6. Create Pull Request
```

### Key Features

1. **Security**: HMAC signature validation prevents unauthorized webhook calls
2. **Non-Blocking**: GitHub receives immediate acknowledgment (202 Accepted)
3. **Background Processing**: Workflow runs asynchronously using FastAPI BackgroundTasks
4. **Error Handling**: Comprehensive logging for debugging
5. **Self-Correction**: Up to 3 remediation attempts with validation feedback

## Monitoring and Debugging

### View Logs

**Railway Dashboard:**
```
Dashboard → Project → Deployments → [Latest] → Logs
```

**Railway CLI:**
```bash
railway logs
```

### Common Issues

**Issue: Webhook returns 401 Unauthorized**
- **Cause**: Signature validation failed
- **Solution**: Verify `GITHUB_WEBHOOK_SECRET` matches in both Railway and GitHub webhook settings

**Issue: Workflow not starting**
- **Cause**: Missing environment variables
- **Solution**: Check Railway variables: `GITHUB_TOKEN`, `OPENAI_API_KEY`

**Issue: Clone fails**
- **Cause**: Invalid GitHub token or insufficient permissions
- **Solution**: Regenerate token with `repo` scope

**Issue: No PR created**
- **Cause**: Validation failed or no vulnerabilities found
- **Solution**: Check logs for validation details

### Health Check Endpoint

Test if the service is running:

```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{"status": "ok"}
```

## Local Development

### Run Locally

```bash
# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export GITHUB_WEBHOOK_SECRET="your_secret"
export GITHUB_TOKEN="ghp_your_token"
export OPENAI_API_KEY="sk_your_key"

# Start server
uvicorn orchestrator.main:app --reload --port 8000
```

### Test Webhook Locally with ngrok

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Expose local server
ngrok http 8000

# Use the ngrok URL in GitHub webhook settings
# Example: https://abc123.ngrok.io/webhook/github
```

## Production Considerations

### Scaling

For production use beyond hackathon MVP:

1. **Use a Job Queue**: Replace BackgroundTasks with Celery/RQ for distributed processing
2. **Add Database**: Store workflow status and results in PostgreSQL
3. **Implement Rate Limiting**: Prevent abuse of webhook endpoint
4. **Add Monitoring**: Use Sentry or similar for error tracking
5. **Enable CORS**: If building a frontend dashboard

### Security Enhancements

1. **Rotate Secrets**: Regularly update `GITHUB_WEBHOOK_SECRET`
2. **Use Secret Management**: Railway's built-in secrets or external vault
3. **Add IP Allowlisting**: Restrict to GitHub's webhook IPs
4. **Implement Request Signing**: Additional layer beyond HMAC

## Support

For issues or questions:
- Check Railway logs for detailed error messages
- Review GitHub webhook delivery logs
- Verify all environment variables are set correctly
- Ensure GitHub token has required permissions

## Quick Reference

**Railway Dashboard**: https://railway.app/dashboard
**Webhook Endpoint**: `https://your-app.railway.app/webhook/github`
**Health Check**: `https://your-app.railway.app/health`
**GitHub Webhook Settings**: Repository → Settings → Webhooks
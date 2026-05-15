#!/bin/bash

# Multi-Agent Security - Quick Start Script

set -e

echo "🚀 Multi-Agent Security - Starting Application"
echo "=============================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source .venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please copy .env.example to .env and configure your variables"
    echo "Run: cp .env.example .env"
    exit 1
fi

# Load environment variables
echo "✅ Loading environment variables..."
export $(cat .env | grep -v '^#' | xargs)

# Check required environment variables
REQUIRED_VARS=("GITHUB_WEBHOOK_SECRET" "GITHUB_TOKEN" "OPENAI_API_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Please configure these in your .env file"
    exit 1
fi

echo "✅ All required environment variables are set"
echo ""
echo "🌐 Starting FastAPI server..."
echo "   Health check: http://localhost:8000/health"
echo "   Webhook endpoint: http://localhost:8000/webhook/github"
echo ""
echo "💡 Tip: Use ngrok to expose this locally for GitHub webhooks:"
echo "   ngrok http 8000"
echo ""

# Start the server
uvicorn orchestrator.main:app --reload --port 8000

# Made with Bob

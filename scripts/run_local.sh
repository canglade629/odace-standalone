#!/bin/bash
# Local development script

set -e

echo "🔧 Starting Odace Data Pipeline in development mode"

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your configuration"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run the application
echo "🚀 Starting FastAPI server..."
echo "📍 Server will be available at: http://localhost:8080"
echo "📚 API docs will be at: http://localhost:8080/docs"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload


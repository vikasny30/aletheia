#!/bin/bash
# Start the Aletheia API server
# Usage: ./start_api.sh
#        ./start_api.sh --port 8080

set -e

PORT=${2:-8000}

# Check for uvicorn
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo "Starting Aletheia API on http://localhost:$PORT"
echo "Docs: http://localhost:$PORT/docs"
echo ""

uvicorn api.main:app --reload --host 0.0.0.0 --port $PORT

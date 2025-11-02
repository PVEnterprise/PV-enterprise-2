#!/bin/bash

# Start FastAPI backend server accessible from network with HTTPS
# This binds to 0.0.0.0 to allow access from other systems

cd "$(dirname "$0")"

echo "Starting FastAPI backend server..."
echo "Server will be accessible at:"
echo "  - Local: http://localhost:8000"
echo "  - Network: http://$(ipconfig getifaddr en0):8000"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start server (use python3 if python is not available)
if command -v python &> /dev/null; then
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi

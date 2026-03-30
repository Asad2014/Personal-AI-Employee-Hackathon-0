#!/bin/bash
# Start AI Employee Dashboard (Backend + Frontend)

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$(dirname "$0")/backend"
FRONTEND_DIR="$(dirname "$0")/frontend"

echo "================================================"
echo "  AI Employee Dashboard"
echo "================================================"

# Check Python venv
if [ -d "$ROOT/venv" ]; then
    source "$ROOT/venv/bin/activate"
fi

# Install backend deps if needed
pip install fastapi uvicorn python-multipart --quiet 2>/dev/null

echo ""
echo "[1/2] Starting FastAPI backend on http://localhost:8000 ..."
cd "$BACKEND_DIR"
python app.py &
BACKEND_PID=$!
sleep 2

echo "[2/2] Starting Next.js frontend on http://localhost:3000 ..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "================================================"
echo "  Dashboard: http://localhost:3000"
echo "  API:       http://localhost:8000"
echo "================================================"
echo "  Press Ctrl+C to stop both servers"
echo ""

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Servers stopped.'" EXIT
wait

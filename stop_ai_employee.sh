#!/bin/bash
# stop_ai_employee.sh - Stop the AI Employee Orchestrator

PROJECT_DIR="/mnt/d/Hackathon-0/Personal AI Employee"
PID_FILE="$PROJECT_DIR/orchestrator.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm "$PID_FILE"
        echo "Orchestrator stopped (PID $PID)"
    else
        rm "$PID_FILE"
        echo "Orchestrator was not running (stale PID file removed)"
    fi
else
    echo "No PID file found — orchestrator is not running"
fi

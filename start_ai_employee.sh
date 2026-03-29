#!/bin/bash
# start_ai_employee.sh - Startup script for AI Employee Orchestrator
# Used by cron @reboot to auto-start the orchestrator on system boot

PROJECT_DIR="/mnt/d/Hackathon-0/Personal AI Employee"
LOG_FILE="$PROJECT_DIR/ai_employee.log"
PID_FILE="$PROJECT_DIR/orchestrator.pid"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "$(date -Iseconds) - Orchestrator already running (PID $OLD_PID)" >> "$LOG_FILE"
        exit 0
    fi
fi

cd "$PROJECT_DIR" || exit 1

# Start orchestrator in background
nohup /usr/bin/python3 orchestrator.py >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "$(date -Iseconds) - Orchestrator started (PID $!)" >> "$LOG_FILE"

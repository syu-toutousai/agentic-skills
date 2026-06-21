#!/bin/bash

# JIT Agentic Media Gateway Manager (octemp version)
# An independent wrapper script for the agy skill

PROJECT_DIR="/home/n6085530/octemp"
LOCAL_LOG="/tmp/jit_media_gateway_local.log"

case "$1" in
    local)
        if pgrep -f "python app.py" > /dev/null; then
            echo "Local JIT Media Gateway is already running."
        else
            echo "Starting local JIT Media Gateway..."
            cd "$PROJECT_DIR" || exit
            nohup python app.py > "$LOCAL_LOG" 2>&1 &
            echo "Local gateway started. Logs are being written to $LOCAL_LOG"
        fi
        ;;
    deploy)
        echo "Deploying JIT Media Gateway to Dev Server..."
        cd "$PROJECT_DIR" || exit
        if [ -x "./deploy.sh" ]; then
            ./deploy.sh
        else
            bash deploy.sh
        fi
        ;;
    stop)
        if pgrep -f "python app.py" > /dev/null; then
            echo "Stopping local JIT Media Gateway..."
            pkill -f "python app.py"
            echo "Gateway stopped."
        else
            echo "Local JIT Media Gateway is not running."
        fi
        ;;
    status)
        if pgrep -f "python app.py" > /dev/null; then
            echo "Status: LOCAL RUNNING"
            PID=$(pgrep -f "python app.py")
            echo "PID: $PID"
        else
            echo "Status: LOCAL STOPPED"
        fi
        ;;
    *)
        echo "Usage: $0 {local|deploy|stop|status}"
        exit 1
        ;;
esac

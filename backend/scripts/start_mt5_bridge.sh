#!/usr/bin/env bash
set -e

SERVER_EXE="$HOME/.mt5/mt5server.exe"
PORT="18812"

# Support optional --restart flag
if [ "$1" == "--restart" ] || [ "$1" == "restart" ]; then
    echo "Restarting MT5 Wine Bridge..."
    pkill -f "mt5server.exe" 2>/dev/null || true
    sleep 1
fi

if [ ! -f "$SERVER_EXE" ]; then
    echo "Error: mt5server.exe not found at $SERVER_EXE"
    exit 1
fi

# Check if port is already listening
if ss -tlpn 2>/dev/null | grep -q ":$PORT "; then
    echo "MT5 Wine Bridge is ALREADY running and listening on port $PORT."
    echo "You can test connection in Python immediately: from app.execution.mt5_executor import MT5Executor; MT5Executor().connect()"
    echo "To restart it, run: $0 --restart"
    exit 0
fi

export WINEPREFIX="${WINEPREFIX:-$HOME/.mt5}"

echo "Starting MT5 Wine Bridge on port $PORT (WINEPREFIX=$WINEPREFIX)..."
echo "To test connection in Python: from app.execution.mt5_executor import MT5Executor; MT5Executor().connect()"
exec wine "$SERVER_EXE" -p "$PORT"

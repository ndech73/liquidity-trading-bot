#!/usr/bin/env bash
set -e

PORT="18812"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export WINEPREFIX="${WINEPREFIX:-$HOME/.mt5}"
MT5_EXE="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"

# Support optional --restart flag
if [ "$1" == "--restart" ] || [ "$1" == "restart" ]; then
    echo "Restarting MT5 Wine Bridge..."
    pkill -f "mt5_bridge_server.py" 2>/dev/null || true
    sleep 1
fi

# Check if port is already listening
if ss -tlpn 2>/dev/null | grep -q ":$PORT "; then
    echo "MT5 Wine Bridge is ALREADY running and listening on port $PORT."
    echo "To restart it, run: $0 --restart"
    exit 0
fi

# Start the MT5 terminal first, if it is not already running
if ! pgrep -f "terminal64.exe" > /dev/null; then
    if [ ! -f "$MT5_EXE" ]; then
        echo "Error: MetaTrader 5 not found at $MT5_EXE"
        exit 1
    fi
    echo "Starting MetaTrader 5..."
    nohup wine "$MT5_EXE" > /dev/null 2>&1 &
    echo "Waiting 20 seconds for MT5 to log in..."
    sleep 20
fi

echo "Starting MT5 Wine Bridge on port $PORT (WINEPREFIX=$WINEPREFIX)..."
cd "$SCRIPT_DIR"
exec wine python mt5_bridge_server.py "$PORT"
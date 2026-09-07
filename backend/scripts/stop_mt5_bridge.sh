#!/usr/bin/env bash
set -e

echo "Stopping MT5 Wine Bridge..."
pkill -f "mt5server.exe" 2>/dev/null && echo "MT5 Wine Bridge stopped successfully." || echo "No running MT5 Wine Bridge process found."

#!/bin/bash
# Crypto AI Trader Launcher (Hummingbot-style TUI)
# Usage: ./start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Crypto AI Trader..."
echo "Default password: crypto2024"
python tui.py

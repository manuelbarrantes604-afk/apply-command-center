#!/bin/bash
# Screenshots of the local preview (port 8877) with headless Chrome. Usage: scripts/shots.sh [base_url]
B=${1:-http://127.0.0.1:8877/}; D=$(dirname "$0")/../_screenshots; mkdir -p "$D"
C="google-chrome --user-data-dir=/tmp/chr-shots-$$ --headless=new --no-sandbox --disable-gpu --hide-scrollbars --virtual-time-budget=6000"
$C --window-size=390,1400 --screenshot="$D/v5-jobs.png" "$B" 2>/dev/null
$C --window-size=390,1400 --screenshot="$D/v5-leads.png" "$B#leads" 2>/dev/null
$C --window-size=1280,1000 --screenshot="$D/v5-desktop.png" "$B" 2>/dev/null
ls -la "$D"

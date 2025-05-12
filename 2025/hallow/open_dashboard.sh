#!/usr/bin/env bash
# Script to check if the dashboard is running and start it if it's not

# Ensure we're in the correct directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if the dashboard is already running
DASHBOARD_PORT=8080
DASHBOARD_RUNNING=0

# Try to connect to the dashboard
if curl -s -f http://localhost:${DASHBOARD_PORT}/ > /dev/null; then
    echo "Dashboard is already running on port ${DASHBOARD_PORT}"
    DASHBOARD_RUNNING=1
else
    echo "Dashboard is not running on port ${DASHBOARD_PORT}"
    DASHBOARD_RUNNING=0
fi

# If dashboard is not running, start it
if [ $DASHBOARD_RUNNING -eq 0 ]; then
    echo "Starting dashboard..."
    if [ -f "./run_realtime_dashboard.sh" ]; then
        # Run in background so this script can exit
        nohup ./run_realtime_dashboard.sh > dashboard.log 2>&1 &
        echo "Dashboard started! Check dashboard.log for details."
        echo "Opening dashboard in browser..."
        sleep 2
        if command -v xdg-open > /dev/null; then
            xdg-open http://localhost:${DASHBOARD_PORT}/
        elif command -v open > /dev/null; then
            open http://localhost:${DASHBOARD_PORT}/
        else
            echo "Dashboard is available at http://localhost:${DASHBOARD_PORT}/"
        fi
    else
        echo "Error: Could not find run_realtime_dashboard.sh"
        exit 1
    fi
else
    # Just open the browser
    echo "Opening existing dashboard in browser..."
    if command -v xdg-open > /dev/null; then
        xdg-open http://localhost:${DASHBOARD_PORT}/
    elif command -v open > /dev/null; then
        open http://localhost:${DASHBOARD_PORT}/
    else
        echo "Dashboard is available at http://localhost:${DASHBOARD_PORT}/"
    fi
fi

exit 0

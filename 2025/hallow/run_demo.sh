#!/bin/bash
# Script to run a full demo of the Netflix Hollow + eBPF metrics monitoring system
# Created to simplify the demo process

echo "=========================================================="
echo "  Netflix Hollow + eBPF Metrics Monitoring System Demo"
echo "=========================================================="

# Ensure we're in the correct directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to check if a command was successful
check_status() {
  if [ $? -eq 0 ]; then
    echo "✅ $1"
  else
    echo "❌ $1"
    echo "Error: $2"
    exit 1
  fi
}

# Step 1: Check environment setup
echo -e "\n📋 Step 1: Checking environment setup..."

# Make sure all scripts are executable
chmod +x *.sh *.py
check_status "Made scripts executable" "Failed to set executable permissions"

# Check Python and required packages
python3 -c "import matplotlib, pandas, numpy, json" 2>/dev/null
check_status "Required Python packages are installed" "Missing required packages. Run 'install_deps.sh' first"

# Step 2: Run diagnostic checks
echo -e "\n📋 Step 2: Running diagnostic checks..."
if [ -f "./run_diagnostics.sh" ]; then
    ./run_diagnostics.sh --quiet
    check_status "System diagnostics passed" "Some diagnostic checks failed. Check output for details."
else
    echo "⚠️ Diagnostics script not found. Continuing without diagnostics."
fi

# Step 3: Check Hollow server status
echo -e "\n📋 Step 3: Checking Hollow server status..."
if [ -f "./check_hollow_connectivity.py" ]; then
    python3 ./check_hollow_connectivity.py
    HOLLOW_RUNNING=$?
    if [ $HOLLOW_RUNNING -eq 0 ]; then
        echo "✅ Hollow server is running"
    else
        echo "ℹ️ Hollow server is not running, will use local mode instead"
    fi
else
    echo "⚠️ Hollow connectivity check script not found. Assuming Hollow server is not available."
    HOLLOW_RUNNING=1
fi

# Step 4: Start the dashboard
echo -e "\n📋 Step 4: Starting the real-time dashboard..."
if [ -f "./open_dashboard.sh" ]; then
    ./open_dashboard.sh
    check_status "Started dashboard" "Failed to start dashboard"
    echo "🌐 Dashboard is now available at http://localhost:8080/"
else
    echo "⚠️ Dashboard starter script not found. Starting dashboard manually."
    ./run_realtime_dashboard.sh
    check_status "Started dashboard" "Failed to start dashboard"
fi

echo -e "\n✨ Demo system is now running! ✨"
echo "- Dashboard: http://localhost:8080/"
echo "- Press Ctrl+C to stop the demo"

# Let the dashboard run until user stops with Ctrl+C
echo -e "\nMonitoring system status:"
echo "(This will refresh every 5 seconds, press Ctrl+C to exit)"

trap "echo -e '\nStopping demo...'; pkill -f 'ebpf_hollow_monitor.py'; exit 0" INT

while true; do
    clear
    echo "=========================================================="
    echo "  Netflix Hollow + eBPF Metrics Monitoring Demo: RUNNING"
    echo "=========================================================="
    echo "Dashboard: http://localhost:8080/"
    echo -e "\nSystem Status:"

    # Check if dashboard is running
    if curl -s -f http://localhost:8080/ > /dev/null; then
        echo "✅ Dashboard: Running"
    else
        echo "❌ Dashboard: Not running"
    fi

    # Check metrics collection
    if pgrep -f "ebpf_hollow_monitor.py" > /dev/null; then
        echo "✅ Metrics Collection: Running"
    else
        echo "❌ Metrics Collection: Not running"
    fi

    # Check Hollow connectivity
    if [ $HOLLOW_RUNNING -eq 0 ]; then
        echo "✅ Hollow Server: Connected"
    else
        echo "ℹ️ Hollow Server: Using local mode"
    fi

    # Count metrics and visualizations
    VIZ_COUNT=$(ls realtime_visualizations/*_latest.png 2>/dev/null | wc -l)
    echo "📊 Active Visualizations: $VIZ_COUNT"

    echo -e "\nPress Ctrl+C to stop the demo"
    sleep 5
done

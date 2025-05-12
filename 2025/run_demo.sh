#!/bin/bash
# Script to run a full demo of the Netflix Hollow + eBPF metrics monitoring system
# Created to simplify the demo process

echo "=========================================================="
echo "  Netflix Hollow + eBPF Metrics Monitoring System Demo"
echo "=========================================================="

# Define the hallow directory
HALLOW_DIR="/home/parallels/Work/Tutorials/Hackathon/2025/hallow"
cd "$HALLOW_DIR"

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
        HOLLOW_MODE=""
        HOLLOW_URL="--producer-url http://localhost:7001"
    else
        echo "⚠️ Hollow server is not running. Using local mode..."
        echo "   (This is fine for the demo - data will be stored locally)"
        HOLLOW_MODE="--local"
        HOLLOW_URL=""
    fi
else
    echo "⚠️ Hollow connectivity check script not found. Assuming local mode."
    HOLLOW_MODE="--local"
    HOLLOW_URL=""
fi

# Step 4: Launch the dashboard
echo -e "\n📋 Step 4: Launching the real-time dashboard..."

# Create visualizations directory if it doesn't exist
VIZ_DIR="$HALLOW_DIR/realtime_visualizations"
mkdir -p "$VIZ_DIR"

# Process command line arguments
NO_FALLBACK=""
if [ "$1" == "--no-fallback" ]; then
    NO_FALLBACK="--no-fallback"
    echo "⚠️ Sample metrics fallback is disabled"
fi

# Explain the dashboard to the viewer
echo "======================================================"
echo "  Starting eBPF monitoring with real-time dashboard"
echo "======================================================"
echo "The dashboard will open in your web browser shortly."
echo "It displays metrics collected from eBPF in real-time."
echo "Dashboard URL: http://localhost:8080/"
echo "======================================================"

# Demo options - make the demo run faster for presentation purposes
COLLECTION_INTERVAL=10  # How often to collect metrics (in seconds)
RETRY_INTERVAL=3        # How often to retry if collection fails

# Launch the dashboard
echo "Launching dashboard with ${HOLLOW_MODE:-remote} mode..."
python3 ebpf_hollow_monitor.py \
    $HOLLOW_URL \
    $HOLLOW_MODE \
    $NO_FALLBACK \
    --dataset-name "demo_ebpf_metrics" \
    --collection-interval $COLLECTION_INTERVAL \
    --retry-interval $RETRY_INTERVAL \
    --visualize \
    --dashboard \
    --dashboard-preload \
    --dashboard-port 8080 \
    --viz-dir "$VIZ_DIR" \
    -v

# The script will keep running until user presses Ctrl+C
echo -e "\nDemo is running! Press Ctrl+C to stop."

#!/bin/bash
# Script to run the eBPF monitoring with real-time visualization dashboard

# Ensure we're in the correct directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate the virtual environment if it exists
if [ -f "$SCRIPT_DIR/activate_env.sh" ]; then
    source "$SCRIPT_DIR/activate_env.sh"
    echo "Virtual environment activated."
fi

# Create directory for visualizations
VIZ_DIR="$SCRIPT_DIR/realtime_visualizations"
mkdir -p "$VIZ_DIR"

# Create placeholder for visualizations directory
if [ ! -d "$VIZ_DIR" ]; then
    mkdir -p "$VIZ_DIR"
    echo "Created visualization directory: $VIZ_DIR"
fi

echo "======================================================"
echo "  Starting eBPF monitoring with real-time dashboard"
echo "======================================================"
echo "The dashboard will open in your web browser immediately."
echo "Placeholder images will be shown until real data is collected."
echo "Dashboard URL: http://localhost:8080/"
echo "Press Ctrl+C to stop the monitoring."
echo "======================================================"

# Check if Hollow server is running
if curl -s http://localhost:7001/api/status > /dev/null; then
    echo "Hollow server is running, using remote mode"
    HOLLOW_MODE=""
    HOLLOW_URL="--producer-url http://localhost:7001"
else
    echo "Hollow server is not running, using local mode instead"
    HOLLOW_MODE="--local"
    HOLLOW_URL=""
fi

# Check if fallback should be disabled
if [ "$1" == "--no-fallback" ]; then
    FALLBACK_MODE="--no-fallback"
    echo "Sample metrics fallback is disabled"
else
    FALLBACK_MODE=""
fi

# Run the monitoring script with dashboard enabled and preloaded
python ebpf_hollow_monitor.py \
    $HOLLOW_URL \
    $HOLLOW_MODE \
    $FALLBACK_MODE \
    --dataset-name "realtime_ebpf_metrics" \
    --collection-interval 30 \
    --retry-interval 5 \
    --visualize \
    --dashboard \
    --dashboard-preload \
    --dashboard-port 8080 \
    --viz-dir "$VIZ_DIR" \
    -v

# Note: The script will continue running until you press Ctrl+C

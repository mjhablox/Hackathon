#!/usr/bin/env bash
# Script to run Hollow integration test with sample data

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Check for and activate virtual environment if it exists
VENV_DIR="$SCRIPT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    echo "Activating Python virtual environment..."
    source "$VENV_DIR/bin/activate"
else
    echo "Warning: Virtual environment not found at $VENV_DIR"
    echo "You may need to run install_deps.sh first."
    echo "Attempting to proceed without virtual environment..."
fi

# Set default parameters
PRODUCER_URL="http://hollow-producer.example.com/api"
AUTH_TOKEN=""
PUSH_MODE="--dry-run"  # Default is dry-run mode
USE_LOCAL=false        # Default is to use remote producer
METRICS_FILE="$PARENT_DIR/sample_metrics.txt"
JSON_OUTPUT="$SCRIPT_DIR/metrics.json"
HOLLOW_OUTPUT="$SCRIPT_DIR/metrics_hollow.json"
VISUALIZE=false

# Display usage information
function show_usage {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  -p, --producer-url URL   URL of the Hollow producer API (default: $PRODUCER_URL)"
    echo "  -t, --token TOKEN        Authentication token for the Hollow producer API"
    echo "  --push                   Actually push data to the Hollow producer (default: dry-run)"
    echo "  -m, --metrics FILE       Specify the input metrics file (default: $METRICS_FILE)"
    echo "  -j, --json FILE          Specify the JSON output file (default: $JSON_OUTPUT)"
    echo "  -o, --hollow FILE        Specify the Hollow output file (default: $HOLLOW_OUTPUT)"
    echo "  -l, --local              Use local Hollow installation instead of remote producer"
    echo "  -v, --visualize          Generate visualizations from the metrics"
    echo "  -h, --help               Display this help message"
    echo
    echo "Examples:"
    echo "  $0 -p http://my-hollow-producer.example.com/api -t my-token --push"
    echo "  $0 -l -m /path/to/metrics.txt -v    # Use local Hollow with visualizations"
    echo
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -p|--producer-url)
            PRODUCER_URL="$2"
            shift 2
            ;;
        -t|--token)
            AUTH_TOKEN="$2"
            shift 2
            ;;
        --push)
            PUSH_MODE="--push"
            shift
            ;;
        -m|--metrics)
            METRICS_FILE="$2"
            shift 2
            ;;
        -j|--json)
            JSON_OUTPUT="$2"
            shift 2
            ;;
        -o|--hollow)
            HOLLOW_OUTPUT="$2"
            shift 2
            ;;
        -l|--local)
            USE_LOCAL=true
            shift
            ;;
        -v|--visualize)
            VISUALIZE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if the metrics file exists
if [ ! -f "$METRICS_FILE" ]; then
    echo "Error: Metrics file not found at $METRICS_FILE"
    echo "Please provide a valid metrics file with --metrics"
    exit 1
fi

# Create output directories if they don't exist
mkdir -p "$(dirname "$JSON_OUTPUT")"
mkdir -p "$(dirname "$HOLLOW_OUTPUT")"

# Display selected mode
echo
if [ "$USE_LOCAL" = true ]; then
    echo "Using local Hollow installation"
else
    echo "Using remote Hollow producer: $PRODUCER_URL"
    if [[ "$PUSH_MODE" == "--push" ]]; then
        echo "WARNING: Running in PUSH mode. Data will be pushed to the remote Hollow producer."
        echo "         Press Ctrl+C within 5 seconds to cancel..."
        sleep 5
    else
        echo "Running in DRY-RUN mode. Data will not be pushed to the producer."
    fi
fi

# Step 1: Convert eBPF metrics to JSON
echo
echo "Step 1: Converting eBPF metrics to JSON..."
cd "$SCRIPT_DIR"
python3 ./ebpf_to_json.py "$METRICS_FILE" -o "$JSON_OUTPUT" --pretty

# Check if JSON conversion was successful
if [ $? -ne 0 ] || [ ! -f "$JSON_OUTPUT" ]; then
    echo "Error: Failed to convert eBPF metrics to JSON"
    exit 1
fi

echo "JSON conversion successful: $JSON_OUTPUT"

# Step 2: Convert JSON to Hollow format and possibly push
echo
echo "Step 2: Converting JSON metrics to Hollow format..."

if [ "$USE_LOCAL" = true ]; then
    # Use local Hollow installation
    python3 ./ebpf_to_hollow.py "$JSON_OUTPUT" --output "$HOLLOW_OUTPUT" --local

    # Check if Hollow conversion was successful
    if [ $? -ne 0 ] || [ ! -f "$HOLLOW_OUTPUT" ]; then
        echo "Error: Failed to convert JSON metrics to Hollow format"
        exit 1
    fi

    echo "Hollow conversion successful: $HOLLOW_OUTPUT"

    # Check for local Hollow producer
    HOLLOW_LOCAL_DIR="$SCRIPT_DIR/hollow-local"
    RUN_PRODUCER="$HOLLOW_LOCAL_DIR/run_producer.sh"

    if [ -f "$RUN_PRODUCER" ]; then
        echo
        echo "Step 3: Publishing data to local Hollow store..."
        echo "To publish your data to the local Hollow store, run:"
        echo "  $RUN_PRODUCER $HOLLOW_OUTPUT"
    else
        echo
        echo "Local Hollow installation not found. To set it up, run:"
        echo "  ./install_deps.sh"
        echo "And answer 'y' when prompted to install Hollow locally."
    fi
else
    # Build the command for the remote Hollow producer
    CMD="./test_hollow_integration.py -p $PRODUCER_URL"

    if [[ -n "$AUTH_TOKEN" ]]; then
        CMD="$CMD -t $AUTH_TOKEN"
    fi

    if [[ "$PUSH_MODE" == "--push" ]]; then
        CMD="$CMD --push"
    fi

    # Add the input JSON file
    CMD="$CMD --input $JSON_OUTPUT"

    # Execute the command
    echo "Running: $CMD"
    echo
    python3 $CMD
fi

# Step 3: Generate visualizations if requested
if [ "$VISUALIZE" = true ]; then
    echo
    echo "Step 3: Generating visualizations..."
    VIZDIR="$SCRIPT_DIR/visualizations"
    mkdir -p "$VIZDIR"

    python3 ./visualize_json_metrics.py "$JSON_OUTPUT" --output-dir "$VIZDIR"

    if [ $? -ne 0 ]; then
        echo "Warning: Failed to generate visualizations"
    else
        echo "Visualizations generated in $VIZDIR"
    fi
fi

echo
echo "Test completed successfully!"

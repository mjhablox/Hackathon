#!/bin/bash
# Script to run the local Hollow producer

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
JAR_FILE="$SCRIPT_DIR/producer/target/hollow-producer-1.0-SNAPSHOT-jar-with-dependencies.jar"
PUBLISH_DIR="$SCRIPT_DIR/publish"
JSON_FILE=$1

# Check for the virtual environment
VENV_DIR="$PARENT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    # Activate the virtual environment if it exists
    echo "Activating Python virtual environment..."
    source "$VENV_DIR/bin/activate"
    
    # Verify activation was successful
    if [ $? -eq 0 ]; then
        echo "Python virtual environment activated successfully."
    else
        echo "Warning: Failed to activate virtual environment. Continuing with system Python."
    fi
else
    echo "Warning: Virtual environment not found at $VENV_DIR"
    echo "Using system Python instead. This may cause compatibility issues."
fi

if [ ! -f "$JAR_FILE" ]; then
    echo "Error: Producer JAR file not found. Build failed?"
    exit 1
fi

if [ -z "$JSON_FILE" ]; then
    echo "Usage: $0 <json_file>"
    echo "Example: $0 ../sample_metrics.json"
    exit 1
fi

if [ ! -f "$JSON_FILE" ]; then
    echo "Error: JSON file not found: $JSON_FILE"
    exit 1
fi

echo "Running Hollow producer..."
java -jar "$JAR_FILE" "$PUBLISH_DIR" "$JSON_FILE"

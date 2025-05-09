#!/bin/bash
# Script to activate the Hollow integration Python environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please run install_deps.sh first."
    exit 1
fi

echo "Activating Python virtual environment..."
source "$VENV_DIR/bin/activate"

# Verify activation was successful
if [ $? -eq 0 ]; then
    echo "Environment activated successfully."
    
    # Display Python and pip information
    python_version=$(python --version 2>&1)
    pip_version=$(pip --version 2>&1)
    
    echo "Using $python_version"
    echo "Using $pip_version"
    echo
    echo "IMPORTANT: This virtual environment will only be active in the current terminal."
    echo "To use the environment in a new terminal, run this script again:"
    echo "  source $SCRIPT_DIR/activate_env.sh"
    echo
    echo "To exit the virtual environment, run:"
    echo "  deactivate"
else
    echo "Error: Failed to activate the virtual environment."
    echo "Please check that venv is properly installed:"
    echo "  sudo apt install python3-venv python3-full"
    exit 1
fi

echo "You can now use the Hollow integration scripts."

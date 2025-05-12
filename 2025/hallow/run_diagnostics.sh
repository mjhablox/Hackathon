#!/usr/bin/env bash
# Script to run all diagnostic tools

echo "========================================"
echo "Running Hollow Connectivity Check (Local)"
echo "========================================"
python3 check_hollow_connectivity.py --local

echo -e "\n\n"
echo "========================================"
echo "Running Dashboard Diagnostics"
echo "========================================"
python3 dashboard_diagnostics.py

echo -e "\n\n"
echo "All diagnostics complete!"

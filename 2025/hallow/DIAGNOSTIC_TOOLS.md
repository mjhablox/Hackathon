# Hollow eBPF Metrics Integration - Diagnostic Tools

This document describes the diagnostic tools available for troubleshooting the Hollow eBPF metrics monitoring system.

## Overview

The Netflix Hollow integration's eBPF metrics monitoring system has been enhanced with several diagnostic tools to help identify and resolve common issues. These tools are designed to ensure the system continues to function reliably even when specific components fail.

## Available Diagnostic Tools

### 1. Hollow Connectivity Check

The `check_hollow_connectivity.py` script allows you to test the connection to a Hollow producer server.

**Usage:**

```bash
# Check connection to default Hollow producer (localhost:7001)
./check_hollow_connectivity.py

# Check connection to a specific producer
./check_hollow_connectivity.py --producer-url http://hollow-server:7001

# Check local Hollow setup
./check_hollow_connectivity.py --local

# Set connection timeout
./check_hollow_connectivity.py --timeout 10
```

**Features:**
- Verifies if the Hollow server is reachable
- Retrieves and displays server status
- Lists available datasets on the server
- Verifies local Hollow setup (when using `--local` flag)

### 2. Dashboard Diagnostics

The `dashboard_diagnostics.py` script performs comprehensive checks of the dashboard and monitoring system.

**Usage:**

```bash
# Run all diagnostics with default values
./dashboard_diagnostics.py

# Check specific visualization directory
./dashboard_diagnostics.py --viz-dir /path/to/visualizations

# Validate a specific JSON metrics file
./dashboard_diagnostics.py --json-file /path/to/metrics.json

# Check for a specific dashboard port
./dashboard_diagnostics.py --dashboard-port 8080
```

**Features:**
- Verifies all required components are present
- Checks JSON metrics files for valid structure
- Validates visualization files
- Checks if the dashboard port is available
- Tests connection to Hollow server
- Generates diagnostic plots for metrics data

## Fixes Implemented

### 1. Hollow Server Connection Issues

- **Local Mode**: Added a `--local` option to handle the absence of a Hollow server
- **Auto-Detection**: Created an automatic detection mechanism for the Hollow server
- **Fallback Mechanism**: System now uses local JSON files when the server is unavailable

### 2. Empty Plots in the Dashboard

- **Placeholder Images**: Added placeholder images that display while waiting for data
- **Sample Data Fallback**: Uses sample metrics when collection fails
- **Data Validation**: Added validation to ensure metrics files have proper structure
- **Error Handling**: Enhanced error handling in the visualization process

### 3. Dashboard Reliability Improvements

- **HTTP Server Handling**: Added better handling to avoid "Address already in use" errors
- **Dashboard Preloading**: Option to initialize the dashboard with placeholders before data is available
- **Browser Cache Control**: Improved cache invalidation for consistent updates
- **Graceful Degradation**: Dashboard continues to function when parts of the system fail

## Troubleshooting Common Issues

### "Failed to push to Hollow" Error

This usually occurs when the Hollow server is not available. Solutions:

1. Run `./check_hollow_connectivity.py` to verify the server status
2. Use local mode by adding `--local` to your command
3. Check that the server URL is correct

### Empty Dashboard Plots

If you see empty plots in the dashboard:

1. Run `./dashboard_diagnostics.py` to check visualization files
2. Verify metrics collection is working by checking JSON files
3. Ensure test_metrics.json is available for fallback data

### "Address already in use" Error

When the dashboard server fails to start:

1. Check if another dashboard is already running
2. Run `./dashboard_diagnostics.py` to check the port status
3. Specify a different port using `--dashboard-port`

## Best Practices

1. Always use the `-v` or `--verbose` flag for detailed logging when troubleshooting
2. Keep test_metrics.json updated with representative sample data
3. Run diagnostics tools before starting the dashboard to pre-emptively identify issues
4. Use `./run_realtime_dashboard.sh` for the most reliable experience

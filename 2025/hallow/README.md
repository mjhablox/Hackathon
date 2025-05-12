# Netflix Hollow Integration for eBPF Metrics

This directory contains components for integrating eBPF metrics with Netflix Hollow, a framework for managing in-memory datasets.

## Quick Start

1. Install dependencies and set up a Python virtual environment:
   ```bash
   ./install_deps.sh
   ```

2. Activate the virtual environment:
   ```bash
   source ./activate_env.sh
   ```

3. Test the integration with sample data:

   For local Hollow:
   ```bash
   ./run_test.sh --local
   ```

   For remote Hollow:
   ```bash
   ./run_test.sh -p http://hollow-producer.example.com/api -t your_token
   ```

4. For continuous monitoring and pushing to Hollow:
   ```bash
   # Make sure the virtual environment is activated
   source ./activate_env.sh

   # Run the monitor (must be run with sudo for eBPF access)
   sudo -E ./ebpf_hollow_monitor.py -p http://hollow-producer.example.com/api -t your_token -i 300
   ```
   Note: The `-E` flag preserves environment variables when using sudo, which is needed for the virtual environment.

## Available Scripts

- `ebpf_to_json.py`: Convert eBPF metrics to JSON format
- `ebpf_to_hollow.py`: Convert JSON to Hollow format and push to Hollow
- `ebpf_hollow_monitor.py`: Continuously monitor and push to Hollow
- `visualize_json_metrics.py`: Create visualizations from JSON metrics
- `test_hollow_integration.py`: Test the Hollow integration with sample data
- `install_deps.sh`: Install required dependencies
- `run_test.sh`: Run the test script with common parameters
- `run_realtime_dashboard.sh`: Start the real-time dashboard with automatic server detection
- `check_hollow_connectivity.py`: Test connection to a Hollow producer server
- `dashboard_diagnostics.py`: Diagnose issues with the dashboard and monitoring system
- `check_metrics.py`: Validate metrics data in JSON files

## Real-time Dashboard

The system includes a real-time visualization dashboard that displays metrics as they're collected:

```bash
./run_realtime_dashboard.sh
```

The dashboard will automatically detect if a Hollow server is running and switch to local mode if needed.

You can also use the convenience script that checks if the dashboard is already running and opens it in your browser:
```bash
./open_dashboard.sh
```

For more information on the dashboard, see [realtime_visualizations/README.md](realtime_visualizations/README.md).

## Troubleshooting & Diagnostics

If you encounter issues with the metrics collection or dashboard:

1. Run the comprehensive diagnostics:
   ```bash
   ./run_diagnostics.sh
   ```

2. Or run individual diagnostic tools:

   ```bash
   # Check dashboard and metrics
   ./dashboard_diagnostics.py

   # Check Hollow server connectivity
   ./check_hollow_connectivity.py
   ```

The diagnostic tools will check all components of the system and provide guidance on fixing any issues.

For more information on diagnostics and troubleshooting, see [DIAGNOSTIC_TOOLS.md](DIAGNOSTIC_TOOLS.md) and [DASHBOARD_FIXES.md](DASHBOARD_FIXES.md).

## Documentation

For detailed documentation, see:

- [HOLLOW_INTEGRATION.md](HOLLOW_INTEGRATION.md): Core Hollow integration details
- [DIAGNOSTIC_TOOLS.md](DIAGNOSTIC_TOOLS.md): Diagnostic tools documentation
- [DASHBOARD_FIXES.md](DASHBOARD_FIXES.md): Dashboard fixes and improvements

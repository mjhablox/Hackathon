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

## Documentation

For detailed documentation, see [HOLLOW_INTEGRATION.md](HOLLOW_INTEGRATION.md)

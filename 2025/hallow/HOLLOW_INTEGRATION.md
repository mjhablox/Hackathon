# Netflix Hollow In### Prerequisites

- Python 3.6+ with support for virtual environments (`python3-venv` package)
- Java 11+ (for local Hollow installation)
- Maven (for building Hollow locally)
- A running Kea DHCP server
- Access to a Netflix Hollow producer endpoint (for remote mode)
- Appropriate authentication credentials if required (for remote mode)ion for eBPF Metrics

This documentation explains how to integrate eBPF metrics collection with Netflix Hollow to create a scalable, efficient pipeline for metrics data.

## Overview

[Netflix Hollow](https://hollow.how/) is an open-source framework for managing in-memory datasets with the following key features:

- Memory-efficient storage of data
- Fast read access
- Built-in support for data versioning
- Tooling for data exploration and visualization

This integration allows you to:
1. Collect metrics from a Kea DHCP server using eBPF
2. Convert the metrics data to a Hollow-compatible format
3. Publish the data to a Hollow producer
4. Automatically monitor and publish metrics at regular intervals

## Prerequisites

- Python 3.6+ with the `requests` library
- A running Kea DHCP server
- Access to a Netflix Hollow producer endpoint
- Appropriate authentication credentials if required

## Installation

The Hollow integration requires several Python libraries and optionally a local installation of Netflix Hollow. You can install everything using the provided script:

```bash
# From the project root directory
./hallow/install_deps.sh
```

This will:
1. Install the following Python dependencies:
   - `requests`: For API communication with the Hollow producer
   - `matplotlib`, `numpy`, `pandas`: For visualization of metrics data

2. Offer to install Netflix Hollow locally:
   - If you answer "y", the script will:
     - Clone the Netflix Hollow repository
     - Build it using Maven
     - Set up a simple Hollow producer and consumer
     - Create run scripts for local testing

### Local vs Remote Hollow

You can use this integration in two modes:

1. **Remote mode**: Connect to an existing Hollow producer API endpoint
2. **Local mode**: Use a local Hollow installation for development and testing

#### Local Hollow Setup

For development and testing, you can use a local Hollow installation. When prompted during `install_deps.sh`, answer "y" to install Hollow locally. You can also set up the local consumer with:

```bash
./hallow/setup_consumer.sh
```

For detailed instructions on the local setup, see [LOCAL_SETUP.md](LOCAL_SETUP.md)

## Directory Structure

The Netflix Hollow integration components are organized in the `hallow/` directory:

```
hallow/
├── __init__.py               - Package initialization
├── ebpf_to_json.py           - Convert eBPF metrics to JSON
├── ebpf_to_hollow.py         - Convert JSON to Hollow format
├── ebpf_hollow_monitor.py    - Continuously monitor and push to Hollow
├── visualize_json_metrics.py - Create visualizations from JSON
├── test_hollow_integration.py- Test Hollow integration with sample data
├── install_deps.sh           - Install dependencies and local Hollow
├── setup_consumer.sh         - Set up local Hollow consumer
├── run_test.sh               - Run integration tests
├── LOCAL_SETUP.md            - Instructions for local setup
└── hollow-local/             - Local Hollow installation (if installed)
    ├── repo/                 - Cloned Hollow repository
    ├── producer/             - Simple Hollow producer
    ├── consumer/             - Simple Hollow consumer
    ├── publish/              - Where Hollow data is published
    ├── run_producer.sh       - Script to run producer
    └── run_consumer.sh       - Script to run consumer
└── HOLLOW_INTEGRATION.md     - This documentation file
```

## Available Scripts

### 1. `ebpf_to_json.py`

Converts raw eBPF metrics output to a structured JSON format.

```bash
./hallow/ebpf_to_json.py <metrics_file.txt> -o <output.json> [--pretty]
```

### 2. `visualize_json_metrics.py`

Creates visualizations from the JSON metrics data.

```bash
./hallow/visualize_json_metrics.py <metrics.json> [-o output_dir]
```

### 3. `ebpf_to_hollow.py`

Converts JSON metrics to Hollow format and pushes to a Hollow producer.

```bash
# Remote Hollow producer
./hallow/ebpf_to_hollow.py <metrics.json> -p <producer_url> [-d <dataset_name>] [-t <auth_token>] [--dry-run] [--output <hollow_format.json>]

# Local Hollow installation
./hallow/ebpf_to_hollow.py <metrics.json> --local [--output <hollow_format.json>]
```

### 4. `ebpf_hollow_monitor.py`

Continuously monitors eBPF metrics and pushes them to Hollow at specified intervals.

```bash
./hallow/ebpf_hollow_monitor.py -p <producer_url> [-d <dataset_name>] [-t <auth_token>] [-i <collection_interval>] [-r <retry_interval>] [-o <output_dir>] [--cleanup] [-v]
```

### 5. `test_hollow_integration.py`

Tests the Hollow integration with sample data.

```bash
# Test with remote Hollow producer
./hallow/test_hollow_integration.py -p <producer_url> [-t <auth_token>] [--push] [--input <json_file>]

# Test with local Hollow installation
./hallow/test_hollow_integration.py --local [--input <json_file>]
```

### 6. `run_test.sh`

A convenience script that runs a full test of the Hollow integration.

```bash
# Test with remote Hollow producer
./hallow/run_test.sh -p <producer_url> [-t <auth_token>] [--push] [-m <metrics_file>] [-v]

# Test with local Hollow installation
./hallow/run_test.sh --local [-m <metrics_file>] [-v]
```

## Quick Start Guide

### Step 1: Install Dependencies and Set Up Hollow

Install the required dependencies and optionally set up Hollow locally:

```bash
# From project root directory
cd hallow
./install_deps.sh
# When prompted, answer 'y' to install Hollow locally if you want to use local mode
# Optionally set up the Hollow consumer
./setup_consumer.sh
```

### Step 2: Test with Sample Data

You can test the integration with sample data in two ways:

#### Using Remote Hollow Producer:

```bash
# From project root directory
./hallow/ebpf_to_json.py sample_metrics.txt -o sample_hollow.json --pretty
./hallow/ebpf_to_hollow.py sample_hollow.json -p http://hollow-producer.example.com/api -d dhcp_metrics --dry-run --output hollow_output.json

# Or use the test script
./hallow/test_hollow_integration.py -p http://hollow-producer.example.com/api
```

#### Using Local Hollow Installation:

```bash
# Use the run_test.sh script with the --local option
cd hallow
./run_test.sh --local

# Or use the individual scripts
./ebpf_to_json.py ../sample_metrics.txt -o sample_hollow.json --pretty
./ebpf_to_hollow.py sample_hollow.json --local --output hollow_output.json

# Publish to local Hollow store
./hollow-local/run_producer.sh hollow_output.json

# View the data with the consumer
./hollow-local/run_consumer.sh
```

The test will:
1. Convert the eBPF metrics to JSON
2. Transform the JSON to Hollow format
3. Save the result, and in local mode, provide instructions for publishing to a local Hollow store

### Step 2: Run a Single Collection Cycle

```bash
sudo python3 kea_metrics.py > metrics.txt  # Press Ctrl+C after a few seconds
./hallow/ebpf_to_json.py metrics.txt -o metrics.json
./hallow/ebpf_to_hollow.py metrics.json -p http://hollow-producer.example.com/api -d dhcp_metrics -t your_token
```

### Step 3: Set Up Continuous Monitoring

```bash
sudo ./hallow/ebpf_hollow_monitor.py -p http://hollow-producer.example.com/api -d dhcp_metrics -t your_token -i 300 -o ./metrics_data -v
```

This will:
1. Collect metrics every 5 minutes (300 seconds)
2. Save the raw metrics and JSON in the `./metrics_data` directory
3. Push each collection to the Hollow producer
4. Provide verbose output for debugging

## Hollow Data Schema

The eBPF metrics are converted to the following Hollow schema:

```
MetricsState
  - timestamp (String)
  - source (String)
  - metrics (Map<String, Metric>)
  - aggregates (Map<String, Integer>)

Metric
  - name (String)
  - total (Integer)
  - unit (String)
  - buckets (List<MetricBucket>)

MetricBucket
  - lower (Integer)
  - upper (Integer)
  - count (Integer)
```

## Accessing the Data in Hollow

Once the data is published to Hollow, you can use Hollow consumers to:

1. Efficiently access the metrics data in-memory
2. Compare different versions of metrics data
3. Be notified when new metrics data is available
4. Build dashboards using the Hollow Explorer UI

## Troubleshooting

### Common Issues

#### Remote Hollow Issues
1. **Authentication Errors**: Verify your authentication token and permissions
2. **Connection Timeouts**: Check network connectivity to the Hollow producer
3. **API Compatibility**: Ensure the Hollow producer API is compatible with the format we're sending

#### Local Hollow Issues
1. **Java Version**: Netflix Hollow requires Java 11+. Check your version with `java -version`
2. **Maven Build Failures**: Try rebuilding with `cd hollow-local/repo && mvn clean install -DskipTests`
3. **Missing Producer/Consumer**: Check that the run scripts exist in the hollow-local directory

#### eBPF-Related Issues
1. **eBPF Collection Errors**: Ensure the eBPF program is loading correctly and that you have sudo/root access
2. **Invalid Format**: Check that the metrics file is in the correct format

### Diagnostic Steps

#### For Remote Hollow
1. Run the scripts with verbose output (`-v` flag)
2. Use `--dry-run` with `ebpf_to_hollow.py` to test conversion without pushing
3. Check your API credentials and connectivity to the remote server

#### For Local Hollow
1. Verify Java and Maven are correctly installed
2. Run `./install_deps.sh` again if needed to repair the local setup
3. Check for error messages in the Maven build output

#### For eBPF Issues
1. Check system logs for eBPF-related errors: `sudo dmesg | grep BPF`
2. Run the metrics collection manually to verify it works: `sudo python3 kea_metrics.py > test_metrics.txt`

### Testing Your Setup
The easiest way to test your setup is to use the run_test.sh script:

```bash
# Test with remote Hollow
./run_test.sh -p http://your-hollow-producer.com/api -t your-token

# Test with local Hollow
./run_test.sh --local
```

## Further Reading

- [Netflix Hollow GitHub](https://github.com/Netflix/hollow)
- [Hollow Documentation](https://hollow.how/)
- [eBPF Documentation](https://ebpf.io/)

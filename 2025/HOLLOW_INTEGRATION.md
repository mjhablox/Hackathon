# Netflix Hollow Integration for eBPF Metrics

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

## Available Scripts

### 1. `ebpf_to_json.py`

Converts raw eBPF metrics output to a structured JSON format.

```bash
./ebpf_to_json.py <metrics_file.txt> -o <output.json> [--pretty]
```

### 2. `visualize_json_metrics.py`

Creates visualizations from the JSON metrics data.

```bash
./visualize_json_metrics.py <metrics.json> [-o output_dir]
```

### 3. `ebpf_to_hollow.py`

Converts JSON metrics to Hollow format and pushes to a Hollow producer.

```bash
./ebpf_to_hollow.py <metrics.json> -p <producer_url> [-d <dataset_name>] [-t <auth_token>] [--dry-run] [--output <hollow_format.json>]
```

### 4. `ebpf_hollow_monitor.py`

Continuously monitors eBPF metrics and pushes them to Hollow at specified intervals.

```bash
./ebpf_hollow_monitor.py -p <producer_url> [-d <dataset_name>] [-t <auth_token>] [-i <collection_interval>] [-r <retry_interval>] [-o <output_dir>] [--cleanup] [-v]
```

## Quick Start Guide

### Step 1: Test with Sample Data

Convert existing sample metrics to Hollow format:

```bash
./ebpf_to_json.py sample_metrics.txt -o sample_hollow.json --pretty
./ebpf_to_hollow.py sample_hollow.json -p http://hollow-producer.example.com/api -d dhcp_metrics --dry-run --output hollow_output.json
```

This will:
1. Convert the sample metrics to JSON
2. Transform it to Hollow format
3. Save the result without actually pushing to Hollow

### Step 2: Run a Single Collection Cycle

```bash
sudo python3 kea_metrics.py > metrics.txt  # Press Ctrl+C after a few seconds
./ebpf_to_json.py metrics.txt -o metrics.json
./ebpf_to_hollow.py metrics.json -p http://hollow-producer.example.com/api -d dhcp_metrics -t your_token
```

### Step 3: Set Up Continuous Monitoring

```bash
sudo ./ebpf_hollow_monitor.py -p http://hollow-producer.example.com/api -d dhcp_metrics -t your_token -i 300 -o ./metrics_data -v
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

1. **Authentication Errors**: Verify your authentication token and permissions
2. **Connection Timeouts**: Check network connectivity to the Hollow producer
3. **eBPF Collection Errors**: Ensure the eBPF program is loading correctly and that you have sudo/root access

### Diagnostic Steps

1. Run the scripts with verbose output (`-v` flag)
2. Use `--dry-run` with `ebpf_to_hollow.py` to test conversion without pushing
3. Check system logs for eBPF-related errors: `sudo dmesg | grep BPF`

## Further Reading

- [Netflix Hollow GitHub](https://github.com/Netflix/hollow)
- [Hollow Documentation](https://hollow.how/)
- [eBPF Documentation](https://ebpf.io/)

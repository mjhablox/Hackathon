# Kea DHCP Server Monitoring with eBPF and Netflix Hollow

This project implements an eBPF-based monitoring solution for tracking performance metrics of the Kea DHCP server with Netflix Hollow integration. It allows real-time observation of various performance indicators without modifying the Kea source code. The collected metrics are displayed in a real-time dashboard and can be stored in Netflix Hollow for efficient in-memory access.

## Overview

The system provides end-to-end monitoring capabilities:

1. **eBPF Metrics Collection**: Lightweight tracing of Kea DHCP server performance
2. **Netflix Hollow Integration**: Efficient storage and access of metrics data
3. **Real-time Dashboard**: Browser-based visualization of performance metrics
4. **Resilient Architecture**: Fault-tolerant operation even when components fail

### Key Metrics Tracked

- **Packet Processing Time**: Time taken to process DHCP packets
- **CPU Usage**: CPU utilization by the Kea server
- **Memory Usage**: Memory consumption patterns
- **Network Traffic**: Network activity volume
- **Error Rates**: Frequency of errors
- **Lease Allocation Time**: Time taken to allocate DHCP leases
- **Database Query Performance**: Database operation latency

## Components

### Core eBPF Monitoring
1. **kea_metrics.c**: eBPF program defining trace functions for various metrics
2. **kea_metrics.py**: Python script to load and attach eBPF probes to Kea functions
3. **visualize_metrics.py**: Script to generate visualizations from collected metrics
4. **kea_monitor_complete.py**: All-in-one script for monitoring, traffic generation, and visualization

### Netflix Hollow Integration
5. **ebpf_to_json.py**: Convert eBPF metrics output to structured JSON
6. **ebpf_to_hollow.py**: Convert JSON metrics to Hollow format and push to Hollow producer
7. **ebpf_hollow_monitor.py**: Main script for metrics collection, visualization, and dashboard
8. **visualize_json_metrics.py**: Create visualizations from JSON format metrics
9. **run_realtime_dashboard.sh**: Launch the real-time dashboard with automatic Hollow detection

### Diagnostic Tools
10. **check_hollow_connectivity.py**: Test connectivity to Hollow server
11. **dashboard_diagnostics.py**: Validate dashboard functionality
12. **run_diagnostics.sh**: Run comprehensive system diagnostics
13. **open_dashboard.sh**: Check and open the dashboard in a browser

### Traffic Generation & Testing
14. **run_kea_monitoring.py**: Script to run both monitoring and traffic generation
15. **troubleshoot_kea_server.py**: Script to diagnose Kea server connectivity issues
16. **dras_wrapper.py**: Script to run Infoblox's Dras client from macOS
17. **test_hollow_integration.py**: Test the Hollow integration with sample data

### Support Tools
18. **find_available_functions.py**: Tool to find relevant functions in Kea binary
19. **find_mangled_names.py**: Tool to find mangled versions of function names
20. **list_all_functions.py**: Comprehensive function discovery in Kea binary
21. **run_demo.sh**: Single command to run a complete demonstration

## Prerequisites

- BCC (BPF Compiler Collection)
- Python 3.6 or higher
- Python packages:
  - matplotlib
  - pandas
  - numpy
  - requests
- Kea DHCP server installed and running
- Root/sudo privileges for attaching eBPF probes
- Web browser for viewing the dashboard
- Optional: Netflix Hollow server (falls back to local storage if unavailable)
- Optional: Infoblox Dras client for DHCP traffic generation

## Cross-Platform Monitoring Architecture

This monitoring solution uses a cross-platform architecture:

1. **Linux Server**: Runs the Kea DHCP server and the eBPF monitoring tools
2. **macOS Client**: Generates DHCP traffic using Infoblox's Dras client
3. **Monitoring Flow**: macOS traffic → Linux server → eBPF captures → Metrics collection

### Setting Up the Linux Server

1. Install the prerequisites:

```bash
# Install BCC and other dependencies
sudo apt-get install bpfcc-tools python3-bpfcc python3-matplotlib
```

2. Clone this repository:

```bash
git clone https://github.com/yourusername/kea-ebpf-monitoring.git
cd kea-ebpf-monitoring
```

3. Start the monitoring tool:

```bash
sudo python3 kea_monitor_complete.py
```

### Setting Up the macOS Client

1. Install the Infoblox Dras client:
   - Download from Infoblox support portal
   - Place in a directory in your PATH (e.g., /usr/local/bin)
   - Make it executable: `chmod +x /usr/local/bin/dras`

2. Copy the `dras_wrapper.py` script to your macOS machine:

```bash
# Copy from Linux server to macOS (run on macOS)
scp user@linux-server:/path/to/dras_wrapper.py ~/dras_wrapper.py
```

3. Run the wrapper script on macOS:

```bash
sudo python3 dras_wrapper.py --server <linux-server-ip>
```

## Real-Time Monitoring with Netflix Hollow Integration

### Running the Real-Time Dashboard

The system provides a real-time dashboard for monitoring metrics:

```bash
# From the main directory
./run_demo.sh
```

This will:
1. Check if the Hollow server is running
2. Automatically use local mode if Hollow is unavailable
3. Start metrics collection via eBPF
4. Launch the web-based dashboard
5. Display real-time metrics visualizations

### Dashboard Features

- **Real-time Updates**: Metrics are continuously updated
- **Multiple Metric Views**: See all collected metrics at once
- **Auto-refresh**: Dashboard automatically refreshes with new data
- **Resilient Operation**: Works even when components fail
- **Hollow Integration**: Optional integration with Netflix Hollow for metrics storage

### Netflix Hollow Data Schema

The system uses a consistent data schema for Hollow integration:

- **MetricsState**: Top-level container for all metrics data
  - timestamp: When metrics were collected
  - source: Source of the metrics data
  - metrics: Map of named metrics with their data
  - aggregates: Summary statistics

- **Metric**: Container for a specific metric type
  - name: Metric name (e.g., "CPU Usage")
  - total: Total count of events
  - unit: Unit of measurement (e.g., "ns", "bytes")
  - buckets: Distribution buckets

- **MetricBucket**: Distribution data for histogram visualization
  - lower: Lower bound of the bucket
  - upper: Upper bound of the bucket
  - count: Number of events in this range

## Using with Infoblox Dras Client (Optional)

### Running Dras Client on macOS

To generate DHCP traffic from your macOS machine:

```bash
# Basic usage
dras -i en0 -n 1000 -r 50 -t 60 -s lease -d <kea-server-ip>

# Using our wrapper script (recommended)
sudo python3 dras_wrapper.py -i en0 -n 1000 -r 50 -t 60 -s lease -d <kea-server-ip>
```

Options for the Dras client:

- `-i en0`: Network interface (typically en0 on macOS)
- `-n 1000`: Number of DHCP packets to generate
- `-r 50`: Rate of 50 packets per second
- `-t 60`: Run for 60 seconds
- `-s lease`: Use the "lease" scenario (DORA sequence)
- `-d <ip>`: Target DHCP server IP address

### Workflow: Linux Monitoring + macOS Traffic

The complete workflow follows these steps:

1. Start monitoring on Linux:

```bash
sudo python3 kea_monitor_complete.py
```

2. Wait for the script to initialize and display instructions for the macOS client

3. Run Dras client on macOS:

```bash
sudo python3 dras_wrapper.py -d <linux-server-ip>
```

4. Watch the metrics being collected on the Linux server

5. After completion, examine the visualizations generated on the Linux server

## Command Line Options

### Linux Server (kea_monitor_complete.py)

```bash
# Run with default settings (300s monitoring)
sudo python3 kea_monitor_complete.py

# Run for 10 minutes
sudo python3 kea_monitor_complete.py --duration 600

# Run without showing Dras instructions
sudo python3 kea_monitor_complete.py --no-traffic

# Run without creating visualizations
sudo python3 kea_monitor_complete.py --no-visualization
```

### macOS Client (dras_wrapper.py)

```bash
# Run with defaults (1000 packets at 50 pps)
sudo python3 dras_wrapper.py -d <linux-server-ip>

# Run with custom packet count and rate
sudo python3 dras_wrapper.py -n 5000 -r 100 -d <linux-server-ip>

# Run with specific interface
sudo python3 dras_wrapper.py -i en1 -d <linux-server-ip>
```

## Troubleshooting

If you're having problems with connectivity between the macOS client and Linux server:

```bash
# On Linux server
sudo python3 troubleshoot_kea_server.py

# On macOS client
ping <linux-server-ip>
sudo tcpdump -i en0 port 67 or port 68
```

Common issues:

1. **Permission Denied**: Make sure you're running with sudo/root privileges on both machines
2. **Kea Server Not Running**: Verify Kea is running with `ps aux | grep kea-dhcp4`
3. **Network Connectivity**: Ensure macOS can reach Linux server (ping test)
4. **Firewalls**: Check for firewalls blocking UDP ports 67/68
5. **Interface Issues**: Verify correct interfaces are being used on both sides

## Netflix Hollow Integration

This project now supports integration with Netflix Hollow for efficient in-memory storage and access of metrics data. For detailed instructions, see [HOLLOW_INTEGRATION.md](HOLLOW_INTEGRATION.md).

### Converting eBPF Metrics to JSON

```bash
# Convert metrics file to JSON format
./hallow/ebpf_to_json.py metrics_file.txt -o metrics.json --pretty
```

### Pushing Metrics to Hollow

```bash
# Convert JSON metrics to Hollow format and push to a Hollow producer
./hallow/ebpf_to_hollow.py metrics.json -p http://hollow-producer.example.com/api -d dhcp_metrics -t your_auth_token
```

### Continuous Monitoring and Pushing to Hollow

```bash
# Start continuous monitoring with 5-minute intervals
sudo ./hallow/ebpf_hollow_monitor.py -p http://hollow-producer.example.com/api -d dhcp_metrics -t your_auth_token -i 300 -v

# Disable fallback to sample metrics when collection fails (for production environments)
sudo ./hallow/ebpf_hollow_monitor.py -p http://hollow-producer.example.com/api -d dhcp_metrics -t your_auth_token -i 300 -v --no-fallback
```

### Testing the Hollow Integration

```bash
# Run the test script to verify the Hollow integration
./hallow/test_hollow_integration.py -p http://hollow-producer.example.com/api
```

### Visualizing JSON Metrics

```bash
# Generate visualizations from JSON metrics
./hallow/visualize_json_metrics.py metrics.json -o visualizations/
```

## Testing and Verification

### Quick Testing

To quickly test the entire system:

```bash
cd /home/parallels/Work/Tutorials/Hackathon/2025
./run_demo.sh
```

### Component Testing

For component-by-component testing:

1. **Test Hollow Connectivity**:
```bash
cd hallow
python3 check_hollow_connectivity.py
```

2. **Test Metrics Collection**:
```bash
cd hallow
python3 ebpf_hollow_monitor.py --local --collection-interval 10 --no-dashboard -v
```

3. **Test Visualizations**:
```bash
cd hallow
python3 visualize_json_metrics.py test_metrics.json --output-dir ./visualizations --create-latest -v
```

4. **Test Dashboard**:
```bash
cd hallow
./open_dashboard.sh
```

### Comprehensive Diagnostic Tests

Run all diagnostic tests:

```bash
cd hallow
./run_diagnostics.sh
```

This will check:
- System environment and dependencies
- Hollow server connectivity
- Metrics data format and validity
- Visualization generation
- Dashboard operation

### Giving a Demo

To give a complete demonstration of the system:

1. Navigate to the project's root directory:
```bash
cd /home/parallels/Work/Tutorials/Hackathon/2025
```

2. Run the demo script:
```bash
# Run with default settings
./run_demo.sh

# Run without fallback to sample metrics
./run_demo.sh --no-fallback
```

3. Point out key dashboard features:
   - Real-time metrics updates
   - Multiple visualization types
   - Auto-refreshing data
   - Resilience when components fail

4. Explain the fallback mechanisms:
   - Local mode when Hollow server is unavailable
   - Sample metrics when collection fails (can be disabled with `--no-fallback`)
   - Automatic dashboard recovery

## License

This project is open source and available under [MIT License](LICENSE).

## Acknowledgments

- ISC for the Kea DHCP Server
- BCC developers for the eBPF tools
- Netflix for the Hollow in-memory data store
- Infoblox for the Dras DHCP testing client

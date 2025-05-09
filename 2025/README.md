# Kea DHCP Server Monitoring with eBPF

This project implements an eBPF-based monitoring solution for tracking performance metrics of the Kea DHCP server. It allows real-time observation of various performance indicators without modifying the Kea source code. The collected metrics can now be integrated with Netflix Hollow for efficient in-memory storage and access.

## Overview

The monitoring solution tracks the following metrics:

- **Packet Processing Time**: Time taken to process DHCP packets
- **CPU Usage**: CPU utilization by the Kea server
- **Memory Usage**: Memory consumption patterns
- **Network Traffic**: Network activity volume
- **Error Rates**: Frequency of errors
- **Lease Allocation Time**: Time taken to allocate DHCP leases
- **Database Query Performance**: Database operation latency

## Components

1. **kea_metrics.c**: eBPF program defining trace functions for various metrics
2. **kea_metrics.py**: Python script to load and attach eBPF probes to Kea functions
3. **run_kea_monitoring.py**: Script to run both monitoring and traffic generation
4. **visualize_metrics.py**: Script to generate visualizations from collected metrics
5. **kea_monitor_complete.py**: All-in-one script for monitoring, traffic generation, and visualization
6. **troubleshoot_kea_server.py**: Script to diagnose Kea server connectivity issues
7. **dras_wrapper.py**: Script to run Infoblox's Dras client from macOS
8. **Netflix Hollow Integration** (located in `hallow/` directory):
   - `ebpf_to_json.py`: Convert eBPF metrics output to structured JSON
   - `ebpf_to_hollow.py`: Convert JSON metrics to Hollow format and push to Hollow producer
   - `ebpf_hollow_monitor.py`: Continuously monitor and push metrics to Hollow
   - `visualize_json_metrics.py`: Create visualizations from JSON format metrics
   - `test_hollow_integration.py`: Test the Hollow integration with sample data
9. **Support Scripts**:
   - `find_available_functions.py`: Tool to find relevant functions in Kea binary
   - `find_mangled_names.py`: Tool to find mangled versions of function names
   - `list_all_functions.py`: Comprehensive function discovery in Kea binary

## Prerequisites

- BCC (BPF Compiler Collection)
- Python 3.6 or higher
- Kea DHCP server installed and running
- Root/sudo privileges for attaching eBPF probes
- Matplotlib for visualizations
- Infoblox Dras client installed on macOS for DHCP traffic generation

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

## Using with Infoblox Dras Client on macOS

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

## License

This project is open source and available under [MIT License](LICENSE).

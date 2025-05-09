#!/usr/bin/env python3
# Comprehensive script to collect, analyze, and visualize Kea DHCP metrics

import os
import sys
import time
import signal
import subprocess
import argparse
import datetime
import shutil
from pathlib import Path

# Define colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(message):
    """Print a formatted header message"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}===== {message} ====={Colors.ENDC}")

def print_info(message):
    """Print an info message"""
    print(f"{Colors.BLUE}[INFO]{Colors.ENDC} {message}")

def print_success(message):
    """Print a success message"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.ENDC} {message}")

def print_warning(message):
    """Print a warning message"""
    print(f"{Colors.YELLOW}[WARNING]{Colors.ENDC} {message}")

def print_error(message):
    """Print an error message"""
    print(f"{Colors.RED}[ERROR]{Colors.ENDC} {message}")

def check_root():
    """Check if script is running as root"""
    if os.geteuid() != 0:
        print_error("This script needs to be run as root to access BPF features and network interfaces")
        sys.exit(1)

def check_dependencies():
    """Check if all required dependencies are installed"""
    print_header("Checking Dependencies")

    # Check Python packages
    try:
        import matplotlib
        import numpy
        print_success("Python visualization libraries found")
    except ImportError as e:
        print_error(f"Missing Python dependency: {e}")
        print_info("Install with: pip3 install matplotlib numpy")
        return False

    # Check BCC
    try:
        import bcc
        print_success("BCC Python bindings found")
    except ImportError:
        print_error("BCC Python bindings not found")
        print_info("Install with: sudo apt install python3-bpfcc bpfcc-tools")
        return False

    # Check if kea-dhcp4 is running
    try:
        result = subprocess.run(
            "ps aux | grep kea-dhcp4 | grep -v grep",
            shell=True,
            stdout=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print_success("Kea DHCP server is running")
        else:
            print_warning("Kea DHCP server is not running")
            print_info("The monitoring can be started but may not collect meaningful data")
    except Exception as e:
        print_error(f"Error checking Kea server status: {e}")

    # Check if required files exist
    required_files = ["kea_metrics.c", "kea_metrics.py", "visualize_metrics.py"]
    missing_files = [f for f in required_files if not os.path.exists(f)]

    if missing_files:
        print_error(f"Missing required files: {', '.join(missing_files)}")
        return False
    else:
        print_success("All required script files found")

    return True

def prepare_output_directory(base_dir="results"):
    """Create a timestamped output directory for results"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_dir, f"kea_metrics_{timestamp}")

    try:
        os.makedirs(output_dir, exist_ok=True)
        print_success(f"Created output directory: {output_dir}")
        return output_dir, timestamp
    except Exception as e:
        print_error(f"Failed to create output directory: {e}")
        return None, timestamp

def run_monitoring(duration=60):
    """Run the Kea monitoring program"""
    print_header("Starting Kea DHCP Monitoring")

    # Start kea_metrics.py in a separate process
    try:
        monitoring_process = subprocess.Popen(
            ["python3", "kea_metrics.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Give the monitoring tool time to attach probes
        time.sleep(3)

        # Check if the process is still running
        if monitoring_process.poll() is not None:
            stdout, stderr = monitoring_process.communicate()
            print_error("Monitoring process failed to start")
            print(f"Output: {stdout}")
            print(f"Error: {stderr}")
            return None

        print_success("Monitoring process started successfully")
        return monitoring_process
    except Exception as e:
        print_error(f"Error starting monitoring: {e}")
        return None

def check_dhcp_server_ip():
    """Determine the DHCP server IP address"""
    try:
        # Try to get the IP address from netstat
        result = subprocess.run(
            "sudo netstat -tulpn | grep kea-dhcp4",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            # Extract IP from something like "udp 0 0 10.211.55.4:67 0.0.0.0:* 10904/kea-dhcp4"
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split()
                for part in parts:
                    if ':67' in part and part != '0.0.0.0:67':
                        server_ip = part.split(':')[0]
                        return server_ip

        # Try getting external IP addresses
        result = subprocess.run(
            "hostname -I",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            ips = result.stdout.strip().split()
            if ips:
                return ips[0]  # Return first IP if multiple are present

        return None
    except Exception as e:
        print_warning(f"Could not determine DHCP server IP: {e}")
        return None

def get_mac_interfaces():
    """Get typical macOS interface names"""
    return ['en0', 'en1', 'bridge0']

def generate_traffic(count=1000, rate=50, timeout=30, scenario="lease"):
    """Display information for macOS Dras client traffic generation"""
    print_header("macOS Dras Client Information")

    # Try to determine the server IP
    server_ip = check_dhcp_server_ip()

    # Get macOS interface suggestions
    mac_interfaces = get_mac_interfaces()

    # Display macOS Dras instructions
    print_info("To generate DHCP traffic from your macOS machine:")
    print_info("")
    if server_ip:
        print_info(f"1. Ensure your macOS machine can reach this server at {server_ip}")
    else:
        print_info("1. Determine the IP address of this server from your macOS machine")

    print_info("2. Run the Dras client with the following command:")
    print_info("")
    print_info(f"   dras -i <interface> -n {count} -r {rate} -t {timeout} -s {scenario} -d <server-ip>")
    print_info("")
    print_info("   Where:")
    print_info(f"     <interface> is your macOS network interface (typically {', '.join(mac_interfaces)})")
    if server_ip:
        print_info(f"     <server-ip> is this server's address: {server_ip}")
    else:
        print_info("     <server-ip> is this server's address")

    print_info("")
    print_info("3. The monitoring on this server will collect metrics as the Kea DHCP server")
    print_info("   processes the requests from your macOS machine.")
    print_info("")
    print_info("4. Let the monitoring run for the full duration or press Ctrl+C to stop early.")

    # Wait for user acknowledgment
    print_info("")
    print_info("The monitoring is currently running and collecting DHCP server metrics...")

def capture_metrics_output(monitoring_process, output_file):
    """Capture the output from the monitoring process"""
    print_info(f"Capturing metrics to {output_file}")

    try:
        # Send SIGINT (Ctrl+C) to get the metrics summary
        monitoring_process.send_signal(signal.SIGINT)

        # Wait for the process to terminate
        try:
            stdout, stderr = monitoring_process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            monitoring_process.kill()
            stdout, stderr = monitoring_process.communicate()

        # Write output to file
        with open(output_file, "w") as f:
            f.write(stdout)

        if stderr:
            print_warning(f"Errors from monitoring process: {stderr}")

        return True
    except Exception as e:
        print_error(f"Failed to capture metrics: {e}")
        if monitoring_process.poll() is None:
            monitoring_process.kill()
        return False

def visualize_metrics(metrics_file):
    """Create visualizations from the metrics data"""
    print_header("Creating Visualizations")

    try:
        result = subprocess.run(
            ["python3", "visualize_metrics.py", metrics_file],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print_warning(f"Visualization warnings: {result.stderr}")
        print_success("Visualizations created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Visualization failed: {e}")
        if e.stderr:
            print(e.stderr)
        return False

def analyze_results(metrics_file):
    """Analyze the collected metrics and provide insights"""
    print_header("Analyzing Results")

    try:
        with open(metrics_file, 'r') as f:
            content = f.read()

        # Extract metrics summary sections
        sections = {}
        current_section = None
        current_content = []

        for line in content.split('\n'):
            if line.strip() and not line.startswith(' '):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                    current_content = []
                current_section = line.strip()
            elif current_section:
                current_content.append(line)

        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)

        # Analyze each section
        if not sections:
            print_warning("No metrics sections found in the output")
            return

        for section, content in sections.items():
            if "No data" in content or "error occurred" in content:
                print_info(f"{section}: No data collected")
                continue

            has_data = False
            for line in content.split('\n'):
                if '|' in line:
                    has_data = True
                    break

            if has_data:
                print_success(f"{section}: Data collected successfully")
            else:
                print_warning(f"{section}: Possible data collection issues")

    except Exception as e:
        print_error(f"Analysis failed: {e}")

def run_full_workflow(args):
    """Run the full monitoring, traffic generation, and visualization workflow"""
    if not check_dependencies():
        return

    # Prepare output directory
    output_dir, timestamp = prepare_output_directory()
    if not output_dir:
        return

    # Create output file paths
    metrics_file = os.path.join(output_dir, f"metrics_{timestamp}.txt")
    traffic_file = os.path.join(output_dir, f"traffic_{timestamp}.txt")

    # Start monitoring
    monitoring_process = run_monitoring(args.duration)
    if not monitoring_process:
        return

    try:
        # Wait for monitoring to initialize
        print_info(f"Monitoring initialized, waiting {args.wait} seconds before traffic generation")
        time.sleep(args.wait)

        # Display instructions for generating traffic from macOS
        if not args.no_traffic:
            generate_traffic(
                count=args.dras_count,
                rate=args.dras_rate,
                timeout=args.dras_timeout,
                scenario=args.dras_scenario
            )

        # Wait for the requested duration
        remaining = args.duration - args.wait
        if remaining > 0:
            print_info(f"Waiting {remaining} seconds to collect metrics")
            time.sleep(remaining)

        # Capture metrics
        if capture_metrics_output(monitoring_process, metrics_file):
            print_success(f"Metrics saved to {metrics_file}")

            # Analyze results
            analyze_results(metrics_file)

            # Create visualizations
            if not args.no_visualization:
                visualize_metrics(metrics_file)

            print_header("Kea Monitoring Complete")
            print_info(f"Results directory: {output_dir}")
            print_info(f"Metrics file: {metrics_file}")

    except KeyboardInterrupt:
        print_warning("\nMonitoring interrupted by user")
        # Still try to capture metrics if the process is running
        if monitoring_process.poll() is None:
            capture_metrics_output(monitoring_process, metrics_file)
            print_info(f"Partial metrics saved to {metrics_file}")

    except Exception as e:
        print_error(f"Error during monitoring: {e}")
        if monitoring_process and monitoring_process.poll() is None:
            monitoring_process.kill()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Kea DHCP Monitoring with macOS Traffic Generation')
    parser.add_argument('-d', '--duration', type=int, default=300,
                        help='Duration in seconds for the monitoring session (default: 300)')
    parser.add_argument('-w', '--wait', type=int, default=5,
                        help='Wait time in seconds before showing macOS Dras instructions (default: 5)')
    parser.add_argument('-n', '--no-traffic', action='store_true',
                        help='Do not show macOS Dras client instructions')
    parser.add_argument('-v', '--no-visualization', action='store_true',
                        help='Do not create visualizations after monitoring')

    # Suggested Dras client parameters (for macOS)
    dras_group = parser.add_argument_group('Suggested macOS Dras client parameters')
    dras_group.add_argument('--dras-count', type=int, default=1000,
                        help='Suggested number of DHCP packets for macOS Dras (default: 1000)')
    dras_group.add_argument('--dras-rate', type=int, default=50,
                        help='Suggested packets per second for macOS Dras (default: 50)')
    dras_group.add_argument('--dras-timeout', type=int, default=30,
                        help='Suggested duration in seconds for macOS Dras (default: 30)')
    dras_group.add_argument('--dras-scenario', type=str, default='lease',
                        choices=['lease', 'renew', 'release'],
                        help='Suggested scenario for macOS Dras (default: lease)')
    dras_group.add_argument('--dras-interface', type=str, default=None,
                        help='Network interface for Dras to use (default: auto-detect)')
    parser.add_argument('-t', '--troubleshoot', action='store_true',
                        help='Run server troubleshooting instead of monitoring')
    args = parser.parse_args()

    # Check if running as root
    check_root()

    if args.troubleshoot:
        # Run the troubleshooting script
        print_header("Running Kea DHCP Server Troubleshooting")
        subprocess.run(["python3", "troubleshoot_kea_server.py"])
    else:
        # Run the full workflow
        run_full_workflow(args)

if __name__ == "__main__":
    main()

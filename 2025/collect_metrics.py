#!/usr/bin/env python3
# Script to run monitoring and save metrics to a file

import subprocess
import time
import os
import signal
import sys
import argparse
import datetime

def check_root():
    """Check if script is running as root"""
    if os.geteuid() != 0:
        print("This script needs to be run as root to access BPF features and network interfaces")
        sys.exit(1)

def check_kea_running():
    """Check if Kea DHCP server is running"""
    try:
        result = subprocess.run(
            "ps aux | grep kea-dhcp4 | grep -v grep",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print("✓ Kea DHCP server is running")
            return True
        else:
            print("✗ Kea DHCP server is not running")
            return False
    except Exception as e:
        print(f"Error checking Kea status: {e}")
        return False

def create_output_dir(base_dir='./results'):
    """Create output directory for metrics"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_dir, f"kea_metrics_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def run_monitoring_with_output(duration, output_dir, generate_traffic=True):
    """Run monitoring and save output to file"""
    print(f"\n--- Starting Kea DHCP Monitoring (Duration: {duration}s) ---")

    # Prepare output files
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_file = os.path.join(output_dir, f"metrics_{timestamp}.txt")
    traffic_file = os.path.join(output_dir, f"traffic_{timestamp}.txt")

    print(f"Metrics will be saved to: {metrics_file}")

    try:
        # Start monitoring in a way that we can capture the output
        # We use tee to both display and save the output
        monitoring_cmd = f"python3 kea_metrics.py | tee {metrics_file}"
        monitoring_process = subprocess.Popen(
            monitoring_cmd,
            shell=True,
            preexec_fn=os.setsid  # To be able to kill the whole process group later
        )

        # Give the monitoring tool time to attach probes
        time.sleep(3)

        # Check if the process is still running
        if monitoring_process.poll() is not None:
            print("✗ Monitoring process failed to start")
            return None

        print("✓ Monitoring process started successfully")

        # Generate traffic if requested
        if generate_traffic:
            print("\n--- Generating DHCP Traffic ---")
            traffic_cmd = f"python3 generate_kea_traffic.py | tee {traffic_file}"

            # Start traffic generation - don't wait for it to finish
            traffic_process = subprocess.Popen(
                traffic_cmd,
                shell=True,
                preexec_fn=os.setsid  # To be able to kill the whole process group later
            )

            print("✓ Traffic generation started")

        # Wait for the specified duration
        print(f"\nMonitoring for {duration} seconds. Press Ctrl+C to stop early...")
        time.sleep(duration)

        # Send termination signal to processes
        print("\nMonitoring duration completed, collecting final metrics...")

        # Send SIGINT to the monitoring process to trigger clean shutdown and final metrics
        os.killpg(os.getpgid(monitoring_process.pid), signal.SIGINT)

        # Wait for process to finish and collect final metrics
        print("Waiting for monitoring to complete final metrics collection...")
        monitoring_process.wait(timeout=10)

        # If traffic generation was started, terminate it
        if generate_traffic:
            try:
                os.killpg(os.getpgid(traffic_process.pid), signal.SIGTERM)
                traffic_process.wait(timeout=5)
            except:
                pass

        print(f"\n--- Monitoring Complete ---")
        print(f"Metrics saved to: {metrics_file}")

        return metrics_file

    except KeyboardInterrupt:
        print("\nInterrupted by user, saving final metrics...")

        # Send SIGINT to the monitoring process for clean shutdown
        try:
            os.killpg(os.getpgid(monitoring_process.pid), signal.SIGINT)
            monitoring_process.wait(timeout=10)
        except:
            # If timeout, force kill
            try:
                os.killpg(os.getpgid(monitoring_process.pid), signal.SIGKILL)
            except:
                pass

        print(f"Metrics saved to: {metrics_file}")
        return metrics_file

    except Exception as e:
        print(f"Error during monitoring: {e}")
        # Try to kill any running processes
        try:
            os.killpg(os.getpgid(monitoring_process.pid), signal.SIGKILL)
        except:
            pass

        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run Kea DHCP Monitoring and save metrics to file')
    parser.add_argument('-t', '--time', type=int, default=60,
                        help='Duration in seconds to run monitoring (default: 60)')
    parser.add_argument('-o', '--output-dir', default='./results',
                        help='Base directory to save metrics (default: ./results)')
    parser.add_argument('-m', '--monitor-only', action='store_true',
                        help='Only run monitoring without generating traffic')
    parser.add_argument('-v', '--visualize', action='store_true',
                        help='Generate visualizations after collecting metrics')
    args = parser.parse_args()

    check_root()

    if not check_kea_running():
        print("Please start the Kea DHCP server before running this script")
        sys.exit(1)

    # Create output directory
    output_dir = create_output_dir(args.output_dir)

    # Run monitoring and save output
    metrics_file = run_monitoring_with_output(
        args.time,
        output_dir,
        generate_traffic=not args.monitor_only
    )

    # Generate visualizations if requested
    if args.visualize and metrics_file and os.path.exists(metrics_file):
        try:
            print("\n--- Generating Visualizations ---")
            viz_dir = os.path.join(output_dir, "visualizations")
            viz_cmd = f"python3 visualize_metrics.py '{metrics_file}' -o '{viz_dir}'"
            subprocess.run(viz_cmd, shell=True, check=True)
            print(f"✓ Visualizations saved to: {viz_dir}")
        except Exception as e:
            print(f"Failed to generate visualizations: {e}")

    print("\nDone!")

if __name__ == "__main__":
    main()

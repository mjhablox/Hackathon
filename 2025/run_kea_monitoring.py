#!/usr/bin/env python3
# Script to run the Kea DHCP monitoring and traffic generation

import subprocess
import time
import os
import signal
import sys
import argparse

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

def run_monitoring(duration):
    """Run the Kea monitoring program"""
    print("\n--- Starting Kea DHCP Monitoring ---")

    # Start kea_metrics.py in a separate process with sudo
    monitoring_process = subprocess.Popen(
        ["sudo", "python3", "kea_metrics.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    # Give the monitoring tool time to attach probes
    time.sleep(3)

    # Check if the process is still running
    if monitoring_process.poll() is not None:
        print("✗ Monitoring process failed to start")
        stdout, stderr = monitoring_process.communicate()
        print(f"Output: {stdout}")
        print(f"Error: {stderr}")
        return None

    print("✓ Monitoring process started successfully")
    return monitoring_process

def generate_traffic(interface=None, count=1000, rate=50, timeout=30, scenario="lease"):
    """Generate DHCP traffic using Infoblox's Dras client"""
    print("\n--- Generating DHCP Traffic with Infoblox Dras ---")

    try:
        # Find the best interface to use if not provided
        if not interface:
            interface = get_primary_interface()
            if not interface:
                interface = "eth0"  # Default if we can't determine

        # Run Infoblox's Dras client with provided parameters
        print(f"Running Dras client with parameters:")
        print(f"  Interface: {interface}")
        print(f"  Count: {count} packets")
        print(f"  Rate: {rate} packets/sec")
        print(f"  Timeout: {timeout} seconds")
        print(f"  Scenario: {scenario}")

        # Check if dras is available in PATH
        try:
            subprocess.run(
                ["which", "dras"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Run Dras client for traffic generation
            # Parameters:
            # -i: interface
            # -n: number of packets
            # -r: rate (packets/sec)
            # -t: timeout (seconds)
            # -s: scenario (lease - full DORA exchange)
            subprocess.run(
                ["dras",
                 "-i", str(interface),
                 "-n", str(count),
                 "-r", str(rate),
                 "-t", str(timeout),
                 "-s", str(scenario)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("✓ Dras traffic generation completed")

        except subprocess.CalledProcessError:
            print("✗ Dras client not found or failed to execute")
            print("Please ensure Infoblox Dras client is installed and in your PATH")
            print("Skipping traffic generation step")

    except Exception as e:
        print(f"✗ Traffic generation failed: {e}")

def get_primary_interface():
    """Get the primary network interface"""
    try:
        # Try to determine the primary interface with an external IP
        result = subprocess.run(
            "ip route get 8.8.8.8 | grep -oP 'dev \\K\\S+'",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()

        # Fallback: get the first non-loopback interface
        result = subprocess.run(
            "ip link show | grep 'state UP' | grep -v lo | grep -oP '(?<=: )[^:]*(?=:)'",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            interfaces = result.stdout.strip().split('\n')
            if interfaces:
                return interfaces[0]
    except:
        pass

    return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Kea DHCP Monitoring with Traffic Generation')
    parser.add_argument('-t', '--time', type=int, default=60,
                        help='Duration in seconds to run monitoring (default: 60)')
    parser.add_argument('-m', '--monitor-only', action='store_true',
                        help='Only run monitoring without generating traffic')

    # Dras client options
    dras_group = parser.add_argument_group('Dras client options')
    dras_group.add_argument('--dras-count', type=int, default=1000,
                        help='Number of DHCP packets to generate with Dras (default: 1000)')
    dras_group.add_argument('--dras-rate', type=int, default=50,
                        help='Packets per second to generate with Dras (default: 50)')
    dras_group.add_argument('--dras-timeout', type=int, default=30,
                        help='Duration in seconds for Dras traffic generation (default: 30)')
    dras_group.add_argument('--dras-scenario', type=str, default='lease', choices=['lease', 'renew', 'release'],
                        help='Dras traffic pattern to use (default: lease)')
    dras_group.add_argument('--dras-interface', type=str, default=None,
                        help='Network interface for Dras to use (default: auto-detect)')
    args = parser.parse_args()

    check_root()

    if not check_kea_running():
        print("Please start the Kea DHCP server before running this script")
        sys.exit(1)

    # Start monitoring
    monitoring_process = run_monitoring(args.time)
    if monitoring_process is None:
        sys.exit(1)

    if not args.monitor_only:
        # Generate traffic after a short delay
        time.sleep(2)

        # Determine interface for Dras
        interface = args.dras_interface or get_primary_interface()

        # Pass Dras parameters to the traffic generator
        generate_traffic(
            interface=interface,
            count=args.dras_count,
            rate=args.dras_rate,
            timeout=args.dras_timeout,
            scenario=args.dras_scenario
        )

    try:
        # Wait for the desired duration
        print(f"\nMonitoring for {args.time} seconds. Press Ctrl+C to stop early...")

        # Monitor the output of the monitoring process
        remaining_time = args.time
        start_time = time.time()

        while remaining_time > 0 and monitoring_process.poll() is None:
            # Read output from the monitoring process
            line = monitoring_process.stdout.readline().strip()
            if line:
                print(line)

            # Update remaining time
            elapsed = time.time() - start_time
            remaining_time = args.time - int(elapsed)

            # Display remaining time every 10 seconds
            if int(elapsed) % 10 == 0:
                print(f"Monitoring: {remaining_time} seconds remaining...")

            time.sleep(0.1)

        # Gracefully terminate the monitoring process
        if monitoring_process.poll() is None:
            print("\nMonitoring duration completed, terminating...")
            monitoring_process.send_signal(signal.SIGINT)  # Send CTRL+C
            monitoring_process.wait(timeout=10)  # Wait for graceful exit

        # Display final output
        remaining_output, errors = monitoring_process.communicate()
        if remaining_output:
            print(remaining_output)
        if errors:
            print(f"Errors: {errors}")

        print("\n--- Monitoring Complete ---")

    except KeyboardInterrupt:
        print("\nInterrupted by user, terminating monitoring...")
        if monitoring_process.poll() is None:
            monitoring_process.send_signal(signal.SIGINT)
            try:
                monitoring_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                monitoring_process.kill()

    except Exception as e:
        print(f"Error: {e}")
        if monitoring_process.poll() is None:
            monitoring_process.kill()

if __name__ == "__main__":
    main()

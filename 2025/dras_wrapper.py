#!/usr/bin/env python3
# Script to run Infoblox's Dras client for DHCP traffic generation

import argparse
import subprocess
import sys
import os
import time
import platform

def check_os():
    """Check and report operating system"""
    os_name = platform.system()
    print(f"Operating System: {os_name}")
    return os_name

def check_root():
    """Check if script is running as root"""
    if platform.system() == "Darwin":  # macOS
        if os.geteuid() != 0:
            print("This script needs to be run with sudo on macOS")
            sys.exit(1)
    elif platform.system() == "Linux":  # Linux
        if os.geteuid() != 0:
            print("This script needs to be run as root to access network interfaces")
            sys.exit(1)
    else:
        print("Warning: Unknown OS, cannot check root privileges")

def get_primary_interface():
    """Get the primary network interface based on OS"""
    os_name = platform.system()

    if os_name == "Darwin":  # macOS
        try:
            # Get the default interface on macOS
            result = subprocess.run(
                "route -n get default | grep interface | awk '{print $2}'",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

            # Fallback to common macOS interfaces
            for interface in ['en0', 'en1', 'bridge0']:
                result = subprocess.run(
                    f"ifconfig {interface} 2>/dev/null | grep 'status: active'",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode == 0:
                    return interface
        except:
            pass
    elif os_name == "Linux":  # Linux
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

def check_dras_available():
    """Check if Infoblox Dras client is available"""
    try:
        result = subprocess.run(
            ["which", "dras"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result.returncode == 0
    except:
        return False

def run_dras(args):
    """Run Dras client with specified parameters"""
    # Get OS information
    os_name = platform.system()

    interface = args.interface
    if not interface:
        interface = get_primary_interface()
        if not interface:
            if os_name == "Darwin":
                print("Could not determine network interface. Please specify one with --interface.")
                print("Common macOS interfaces are en0, en1, or bridge0.")
            else:
                print("Could not determine network interface. Please specify one with --interface.")
            sys.exit(1)
        print(f"Using auto-detected interface: {interface}")

    print(f"Running Dras client with the following parameters:")
    print(f"  Interface: {interface}")
    print(f"  Count: {args.count} packets")
    print(f"  Rate: {args.rate} packets/sec")
    print(f"  Timeout: {args.timeout} seconds")
    print(f"  Scenario: {args.scenario}")
    if args.server:
        print(f"  Server: {args.server}")
    else:
        print(f"  Server: broadcast")

    # Build Dras command
    cmd = [
        "dras",
        "-i", interface,
        "-n", str(args.count),
        "-r", str(args.rate),
        "-t", str(args.timeout),
        "-s", args.scenario
    ]

    # Add optional parameters
    if args.server:
        cmd.extend(["-d", args.server])  # Changed from -S to -d for macOS compatibility
    if args.verbose:
        cmd.append("-v")
    if args.mac:
        cmd.extend(["-c", args.mac])

    # Execute Dras command
    try:
        print(f"\nExecuting command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        print("\nDHCP traffic generation completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"\nError running Dras client: {e}")
        sys.exit(1)

def main():
    """Main function"""
    # Print banner
    print("\n===== Infoblox Dras Client for DHCP Traffic Generation =====\n")

    # Check OS
    os_name = check_os()

    parser = argparse.ArgumentParser(description='Run Infoblox Dras client for DHCP traffic generation')

    parser.add_argument('-i', '--interface', type=str, default=None,
                        help='Network interface to use (default: auto-detect)')
    parser.add_argument('-n', '--count', type=int, default=1000,
                        help='Number of DHCP packets to generate (default: 1000)')
    parser.add_argument('-r', '--rate', type=int, default=50,
                        help='Packets per second to generate (default: 50)')
    parser.add_argument('-t', '--timeout', type=int, default=30,
                        help='Duration in seconds for traffic generation (default: 30)')
    parser.add_argument('-s', '--scenario', type=str, default='lease',
                        choices=['discover', 'lease', 'renew', 'release'],
                        help='Traffic pattern to use (default: lease)')
    parser.add_argument('-d', '--server', type=str, default=None,
                        help='DHCP server IP address (default: broadcast)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('-c', '--mac', type=str, default=None,
                        help='MAC address to use (default: auto-generate)')

    args = parser.parse_args()

    # Check if running as root
    check_root()

    # Check if Dras client is available
    if not check_dras_available():
        print("ERROR: Infoblox Dras client not found!")
        print("Please install Dras client and ensure it's in your PATH")
        if os_name == "Darwin":
            print("\nOn macOS, you may need to:")
            print("1. Download the Infoblox Dras client from Infoblox support")
            print("2. Ensure it's installed in a directory in your PATH (e.g., /usr/local/bin)")
            print("3. Ensure it has execute permissions (chmod +x /path/to/dras)")
        sys.exit(1)

    # Run Dras client
    run_dras(args)

if __name__ == "__main__":
    main()

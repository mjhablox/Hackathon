#!/usr/bin/env python3
# Script to troubleshoot Kea DHCP server connectivity

import subprocess
import socket
import time
import sys
import os

def check_root():
    """Check if script is running as root"""
    if os.geteuid() != 0:
        print("This script needs to be run as root to access network interfaces")
        sys.exit(1)

def run_command(cmd):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
        print(f"Command executed: {cmd}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        print(f"Error output: {e.stderr}")
        return None

def check_kea_running():
    """Check if Kea DHCP server is running"""
    print("\n--- Checking Kea DHCP Server Status ---")
    result = run_command("ps aux | grep kea-dhcp4 | grep -v grep")
    if result:
        print("✓ Kea DHCP server is running")
        print(result)
        return True
    else:
        print("✗ Kea DHCP server is not running")
        return False

def check_kea_listening():
    """Check if Kea DHCP server is listening on UDP port 67"""
    print("\n--- Checking Kea DHCP Server Ports ---")
    result = run_command("sudo netstat -tulpn | grep kea")
    if result:
        print("✓ Found Kea processes listening on ports:")
        print(result)
        if "67" in result:
            print("✓ Kea is listening on DHCP port 67")
        else:
            print("✗ Kea is not listening on DHCP port 67")
    else:
        print("✗ No Kea processes found listening on any ports")

def check_network_interfaces():
    """Check network interfaces"""
    print("\n--- Checking Network Interfaces ---")
    interfaces = run_command("ip addr show")
    if interfaces:
        print("Network interfaces found:")
        print(interfaces)

    # Check the routing table
    print("\n--- Checking Routing Table ---")
    routes = run_command("ip route")
    if routes:
        print("Routing table:")
        print(routes)

def check_firewall():
    """Check if firewall is blocking DHCP traffic"""
    print("\n--- Checking Firewall Rules ---")
    # Try different firewall tools
    for cmd in ["iptables -L -n", "ufw status", "firewall-cmd --list-all"]:
        result = run_command(cmd)
        if result:
            cmd_name = cmd.split()[0]
            print(f"Firewall ({cmd_name}) rules:")
            print(result)
            break

def check_dhcp_connectivity(server_addr='10.211.55.4'):
    """Check if we can reach the DHCP server on UDP port 67"""
    print(f"\n--- Testing Connectivity to DHCP Server ({server_addr}:67) ---")

    # Try a simple UDP socket connection
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect((server_addr, 67))
        print(f"✓ UDP socket connection to {server_addr}:67 succeeded")
        s.close()
    except Exception as e:
        print(f"✗ UDP socket connection to {server_addr}:67 failed: {e}")

    # Try ping
    print(f"\nPinging {server_addr}:")
    run_command(f"ping -c 4 {server_addr}")

def check_kea_logs():
    """Check Kea DHCP server logs"""
    print("\n--- Checking Kea DHCP Server Logs ---")

    # Try different possible log locations
    log_files = [
        "/var/log/kea/kea-dhcp4.log",
        "/var/log/kea-dhcp4.log",
        "/var/log/syslog"
    ]

    for log_file in log_files:
        try:
            # Check if file exists
            if os.path.exists(log_file):
                print(f"Found log file: {log_file}")
                # Get the last 20 lines from the log
                result = run_command(f"tail -n 20 {log_file}")
                if result:
                    print(f"Last 20 lines from {log_file}:")
                    print(result)

                    # Check for recent DHCP activity
                    recent = run_command(f"grep -i dhcp {log_file} | tail -n 10")
                    if recent:
                        print("Recent DHCP activity:")
                        print(recent)
                    else:
                        print("No recent DHCP activity found in logs")

                    return True
        except Exception as e:
            print(f"Error accessing log file {log_file}: {e}")

    print("✗ No Kea log files found or accessible")
    return False

def check_kea_config():
    """Check Kea DHCP server configuration"""
    print("\n--- Checking Kea DHCP Server Configuration ---")

    # Try different possible config locations
    config_files = [
        "/etc/kea/kea-dhcp4.conf",
        "/usr/local/etc/kea/kea-dhcp4.conf"
    ]

    for config_file in config_files:
        try:
            # Check if file exists
            if os.path.exists(config_file):
                print(f"Found config file: {config_file}")

                # Extract the interface and subnet information
                result = run_command(f"grep -A 10 'interfaces-config' {config_file}")
                if result:
                    print("Interface configuration:")
                    print(result)

                subnet_info = run_command(f"grep -A 20 'subnet' {config_file}")
                if subnet_info:
                    print("\nSubnet configuration:")
                    print(subnet_info)

                return True
        except Exception as e:
            print(f"Error accessing config file {config_file}: {e}")

    print("✗ No Kea configuration files found or accessible")
    return False

def send_test_dhcp_packet(server_addr='10.211.55.4'):
    """Send a test DHCP packet directly to the server"""
    print(f"\n--- Sending Test DHCP Packet to {server_addr} ---")

    try:
        # Create a simple DHCP DISCOVER packet
        packet = bytearray(548)  # standard DHCP packet size

        # Fill in minimal DHCP fields
        packet[0] = 1  # BOOTREQUEST
        packet[1] = 1  # HTYPE: Ethernet
        packet[2] = 6  # HLEN: 6 bytes for MAC
        packet[3] = 0  # HOPS: 0

        # Transaction ID (random)
        packet[4:8] = os.urandom(4)

        # Broadcast flag
        packet[10] = 0x80

        # Client MAC address at offset 28
        mac_bytes = bytes.fromhex("00163e123456")
        packet[28:34] = mac_bytes

        # DHCP magic cookie
        packet[236:240] = bytes.fromhex("63825363")

        # DHCP message type option: DISCOVER
        packet[240] = 53  # option 53
        packet[241] = 1   # length 1
        packet[242] = 1   # DISCOVER

        # End option
        packet[243] = 255

        # Create socket and send
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(('0.0.0.0', 68))  # Client port 68
        s.sendto(bytes(packet), (server_addr, 67))

        # Try to receive response
        s.settimeout(3)
        try:
            response, addr = s.recvfrom(1500)
            print(f"✓ Received {len(response)} bytes response from {addr}")
            return True
        except socket.timeout:
            print("✗ No response received (timeout)")
            return False
        finally:
            s.close()

    except Exception as e:
        print(f"Error sending test packet: {e}")
        return False

def check_reachability_from_mac():
    """Check if the server is reachable from macOS Dras client perspective"""
    print("\n--- Checking Reachability for macOS Dras Client ---")

    # Get all non-loopback interfaces
    interfaces = []
    try:
        result = run_command("ip link show | grep 'state UP' | grep -v lo | grep -oP '(?<=: )[^:]*(?=:)'")
        if result:
            interfaces = result.strip().split('\n')
    except:
        print("✗ Failed to get network interfaces")

    # Get server IPs for each interface
    server_ips = []
    for interface in interfaces:
        try:
            result = run_command(f"ip addr show {interface} | grep 'inet ' | grep -v '127.0.0.1' | awk '{{print $2}}' | cut -d/ -f1")
            if result:
                ips = result.strip().split('\n')
                for ip in ips:
                    server_ips.append((interface, ip))
        except:
            print(f"✗ Failed to get IP for interface {interface}")

    if not server_ips:
        print("✗ No server IPs found for testing")
        return

    print(f"Found {len(server_ips)} potential server IPs for macOS Dras client:")
    for interface, ip in server_ips:
        print(f"- Interface: {interface}, IP: {ip}")

    # Check if port 67 is accessible
    for interface, ip in server_ips:
        # Check if port 67 is open using netcat
        try:
            result = run_command(f"nc -zu -w 1 {ip} 67 && echo 'Port is accessible' || echo 'Port is not accessible'")
            print(f"UDP port 67 on {ip} ({interface}): {result.strip()}")
        except:
            print(f"✗ Failed to check port 67 on {ip} ({interface})")

    print("\n--- macOS Dras Client Instructions ---")
    print("To use the Dras client on your macOS machine:")
    print("1. Ensure your macOS machine can reach one of these server IPs")
    print("2. Run the Dras client with the following command:")
    print("   dras -i en0 -n 1000 -r 50 -t 30 -s lease -d <server-ip>")
    print("   Where <server-ip> is one of the server IPs listed above")
    print("3. If connectivity fails, try:")
    print("   - Checking network connectivity between macOS and this server")
    print("   - Ensuring there are no firewalls blocking DHCP traffic")
    print("   - Running tcpdump on both ends to verify packet flow")

def print_recommendations():
    """Print recommendations based on test results"""
    print("\n--- Recommendations for macOS Dras Client Connectivity ---")
    print("1. Ensure Kea DHCP server is installed and running")
    print("   - If not installed: apt-get install kea")
    print("   - If not running: systemctl start kea-dhcp4-server")
    print("2. Check configuration file for errors")
    print("   - Verify /etc/kea/kea-dhcp4.conf syntax")
    print("   - Run: kea-dhcp4 -t /etc/kea/kea-dhcp4.conf")
    print("3. Ensure server is listening on correct interfaces")
    print("   - Update interfaces section in kea-dhcp4.conf")
    print("4. Check for firewall rules that might block DHCP")
    print("   - Run: iptables -L -n")
    print("   - Ensure UDP ports 67/68 are allowed")
    print("5. For macOS Dras client connectivity:")
    print("   - Ensure macOS can ping this server")
    print("   - Verify there are no network firewalls between macOS and server")
    print("   - Try running Dras with correct server IP:")
    print("     dras -i en0 -n 100 -r 10 -t 10 -s lease -d <server-ip>")
    print("6. Try running packet capture to verify DHCP traffic:")
    print("   - On Linux server: tcpdump -i <interface> port 67 or port 68")
    print("   - On macOS client: sudo tcpdump -i en0 port 67 or port 68")

def main():
    """Run all diagnostic checks"""
    check_root()

    print("=== Kea DHCP Server Connectivity Diagnostics ===\n")

    # Server process check
    server_running = check_kea_running()

    # Listening ports check
    check_kea_listening()

    # Network interfaces check
    check_network_interfaces()

    # Firewall check
    check_firewall()

    # Server connectivity check
    server_addr = '10.211.55.4'  # Default address
    check_dhcp_connectivity(server_addr)

    # macOS reachability check
    check_reachability_from_mac()

    # Only check logs and config if server is running
    if server_running:
        check_kea_logs()
        check_kea_config()

    # Send test packet
    send_test_dhcp_packet(server_addr)

    # Print recommendations
    print_recommendations()

    print("\n=== Diagnostics Complete ===")

if __name__ == "__main__":
    main()

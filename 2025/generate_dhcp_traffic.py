#!/usr/bin/env python3
# A script to generate DHCP traffic for testing the kea_metrics.py program

import subprocess
import time
import sys
import os
import socket
import random

def random_mac():
    """Generate a random MAC address"""
    mac = [0x00, 0x16, 0x3e,
           random.randint(0x00, 0x7f),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))

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

def get_server_ip():
    """Get the Kea DHCP server IP"""
    try:
        # Try to get the IP address from netstat
        result = run_command("sudo netstat -tulpn | grep kea-dhcp4")
        if result:
            # Extract IP from something like "udp 0 0 10.211.55.4:67 0.0.0.0:* 10904/kea-dhcp4"
            lines = result.strip().split('\n')
            for line in lines:
                parts = line.split()
                for part in parts:
                    if ':67' in part and part != '0.0.0.0:67':
                        return part.split(':')[0]

        # Default if can't determine
        return '10.211.55.4'
    except:
        return '10.211.55.4'  # Default if can't determine

def send_dhcp_packet(interface):
    """Send a DHCP packet using dhclient"""
    try:
        # Using dhclient to request a lease
        cmd = f"dhclient -v -1 -d -r {interface} && dhclient -v -1 -d {interface}"
        print(f"Requesting DHCP lease on {interface}")
        run_command(cmd)
        return True
    except Exception as e:
        print(f"Error running dhclient: {e}")
        return False

def send_raw_dhcp_discover(interface, server_ip):
    """Create and send a raw DHCP DISCOVER packet"""
    try:
        mac_addr = random_mac()
        print(f"Sending raw DHCP DISCOVER from {mac_addr} to {server_ip}")

        # Create MAC bytes
        mac_bytes = bytes.fromhex(mac_addr.replace(':', ''))

        # Create a raw DHCP DISCOVER packet
        packet = b''
        packet += b'\x01'  # OP: Boot Request
        packet += b'\x01'  # HTYPE: Ethernet
        packet += b'\x06'  # HLEN: 6 bytes for MAC
        packet += b'\x00'  # HOPS: 0
        packet += os.urandom(4)  # XID: Random Transaction ID
        packet += b'\x00\x00'  # SECS: 0 seconds
        packet += b'\x80\x00'  # FLAGS: Broadcast bit set
        packet += b'\x00\x00\x00\x00'  # CIADDR: 0.0.0.0 (no IP yet)
        packet += b'\x00\x00\x00\x00'  # YIADDR: 0.0.0.0 (no IP yet)
        packet += b'\x00\x00\x00\x00'  # SIADDR: 0.0.0.0 (no server IP)
        packet += b'\x00\x00\x00\x00'  # GIADDR: 0.0.0.0 (no relay)
        packet += mac_bytes  # CHADDR: Client MAC address
        packet += b'\x00' * 10  # Padding for CHADDR
        packet += b'\x00' * 64  # SNAME: empty
        packet += b'\x00' * 128  # FILE: empty

        # DHCP Magic Cookie
        packet += b'\x63\x82\x53\x63'

        # DHCP Option 53 (DHCP Message Type): DISCOVER
        packet += b'\x35\x01\x01'

        # DHCP Option 12 (Host Name)
        hostname = b'kea-test-client'
        packet += b'\x0c' + bytes([len(hostname)]) + hostname

        # DHCP Option 61 (Client Identifier)
        client_id = b'\x01' + mac_bytes  # Type 1 (Ethernet) + MAC address
        packet += b'\x3d' + bytes([len(client_id)]) + client_id

        # DHCP Option 255 (End)
        packet += b'\xff'

        # Pad to minimum DHCP packet size
        if len(packet) < 300:
            packet += b'\x00' * (300 - len(packet))

        # Create a socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to client port (68) on all interfaces
        s.bind(('0.0.0.0', 68))

        # Bind to interface if specified
        if interface:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, interface.encode())
            except:
                print(f"Could not bind to interface {interface}, using default")

        # Send packet to DHCP server
        s.sendto(packet, (server_ip, 67))

        # Brief wait for response
        s.settimeout(1)
        try:
            response, addr = s.recvfrom(1024)
            print(f"Received response: {len(response)} bytes from {addr}")
            return True
        except socket.timeout:
            print("No response received (timeout)")
            return False
        finally:
            s.close()

    except Exception as e:
        print(f"Error sending raw DHCP DISCOVER: {e}")
        return False

def generate_dhcp_traffic():
    """Generate DHCP traffic using multiple methods"""
    print("Starting DHCP traffic generation...")

    # Check if running as root
    if os.geteuid() != 0:
        print("This script needs to be run as root to manipulate network interfaces")
        sys.exit(1)

    # Get Kea DHCP server IP
    server_ip = get_server_ip()
    print(f"Detected Kea DHCP server IP: {server_ip}")

    # Get network interfaces
    interfaces_output = run_command("ip link show | grep 'state UP' | grep -oP '(?<=: )[^:]*(?=:)'")
    if interfaces_output:
        interfaces = interfaces_output.strip().split('\n')
    else:
        # Fallback to common interface names
        interfaces = ['eth0', 'enp0s5', 'wlan0']

    print(f"Found interfaces: {interfaces}")

    success_count = 0

    # Try different methods to generate DHCP traffic
    for interface in interfaces:
        # Method 1: Use dhclient
        try:
            if send_dhcp_packet(interface):
                success_count += 1
        except Exception as e:
            print(f"dhclient method failed: {e}")

        # Method 2: Send raw DHCP DISCOVER packets
        for i in range(3):  # Send multiple DISCOVER packets
            try:
                if send_raw_dhcp_discover(interface, server_ip):
                    success_count += 1
            except Exception as e:
                print(f"Raw packet method failed: {e}")
            time.sleep(0.5)

    print(f"DHCP traffic generation completed. Success count: {success_count}")

if __name__ == "__main__":
    try:
        # Run traffic generation a few times
        iterations = 3
        if len(sys.argv) > 1:
            try:
                iterations = int(sys.argv[1])
            except:
                pass

        for i in range(iterations):
            print(f"\nIteration {i+1}/{iterations}")
            generate_dhcp_traffic()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nTraffic generation interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

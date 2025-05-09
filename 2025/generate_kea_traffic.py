#!/usr/bin/env python3
# A script to generate DHCP traffic for the Kea server

import subprocess
import time
import sys
import os
import socket
import random
import struct

def random_mac():
    """Generate a random MAC address"""
    mac = [0x00, 0x16, 0x3e,
           random.randint(0x00, 0x7f),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))

def send_dhcp_discover(interface, mac_addr=None):
    """Send a DHCP DISCOVER packet using dhcping"""
    if mac_addr is None:
        mac_addr = random_mac()

    try:
        # Using dhcping to send DHCP discover packets
        cmd = f"dhcping -v -c {mac_addr} -h {mac_addr} -s 127.0.0.1 -i {interface}"
        result = subprocess.run(cmd, shell=True, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, timeout=5)
        print(f"DHCP DISCOVER sent via {interface} with MAC {mac_addr}")
        print(result.stdout)
        return True
    except subprocess.SubprocessError as e:
        print(f"Error sending DHCP DISCOVER: {e}")
        if hasattr(e, 'stderr'):
            print(f"Error output: {e.stderr}")
        return False

def create_raw_dhcp_discover(mac_addr=None):
    """Create a raw DHCP DISCOVER packet"""
    if mac_addr is None:
        mac_addr = random_mac()

    # Convert MAC address string to bytes
    mac_bytes = bytes.fromhex(mac_addr.replace(':', ''))

    # DHCP DISCOVER packet (simplified)
    packet = b''
    packet += b'\x01'  # OP: Boot Request
    packet += b'\x01'  # HTYPE: Ethernet
    packet += b'\x06'  # HLEN: 6 bytes for MAC
    packet += b'\x00'  # HOPS: 0
    packet += os.urandom(4)  # XID: Random Transaction ID
    packet += b'\x00\x00'  # SECS: 0 seconds
    packet += b'\x00\x00'  # FLAGS: 0
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
    hostname = b'test-client'
    packet += b'\x0c' + bytes([len(hostname)]) + hostname

    # DHCP Option 55 (Parameter Request List)
    requested_params = b'\x01\x03\x06\x0f\x1f\x21\x2b\x2c\x2e\x2f\x79\x21'
    packet += b'\x37' + bytes([len(requested_params)]) + requested_params

    # DHCP Option 255 (End)
    packet += b'\xff'

    # Pad to minimum DHCP packet size
    if len(packet) < 300:
        packet += b'\x00' * (300 - len(packet))

    return packet

def send_raw_dhcp_packet(interface, packet):
    """Send a raw DHCP packet using a raw socket"""
    try:
        # Create raw socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Bind to interface if specified
        if interface:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, interface.encode())

        # Send packet to DHCP server port
        s.sendto(packet, ('255.255.255.255', 67))
        print(f"Raw DHCP packet sent via {interface}")
        s.close()
        return True
    except Exception as e:
        print(f"Error sending raw DHCP packet: {e}")
        return False

def generate_dhcp_traffic():
    """Generate DHCP traffic for testing"""
    print("Starting DHCP traffic generation for Kea server...")

    # Get network interfaces
    try:
        result = subprocess.run("ip link show | grep 'state UP' | grep -oP '(?<=: )[^:]*(?=:)'",
                              shell=True, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
        interfaces = result.stdout.strip().split('\n')

        if not interfaces or interfaces[0] == '':
            print("No active network interfaces found, using 'lo'")
            interfaces = ['lo']
    except Exception as e:
        print(f"Error getting interfaces: {e}")
        interfaces = ['lo']  # Default to loopback

    success_count = 0

    # Try both methods for sending DHCP packets
    for _ in range(10):  # Send 10 packets
        mac = random_mac()
        for interface in interfaces:
            try:
                # Method 1: Try dhcping (if available)
                try:
                    if send_dhcp_discover(interface, mac):
                        success_count += 1
                except:
                    # Method 2: Try raw socket approach
                    packet = create_raw_dhcp_discover(mac)
                    if send_raw_dhcp_packet(interface, packet):
                        success_count += 1
            except Exception as e:
                print(f"Failed to send packet on {interface}: {e}")

        time.sleep(0.5)  # Small delay between packets

    print(f"DHCP traffic generation completed. Sent {success_count} packets")

if __name__ == "__main__":
    try:
        # Check if running as root
        if os.geteuid() != 0:
            print("This script needs to be run as root to send raw packets")
            sys.exit(1)

        # Run traffic generation
        for i in range(3):
            print(f"\nIteration {i+1}/3")
            generate_dhcp_traffic()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nTraffic generation interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

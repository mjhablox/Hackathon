#!/usr/bin/env python3
# Script to send raw DHCP traffic directly to the Kea server

import socket
import os
import sys
import time
import random
import struct

def random_mac():
    """Generate a random MAC address"""
    mac = [0x00, 0x16, 0x3e,
           random.randint(0x00, 0x7f),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))

def create_dhcp_discover(mac_addr=None, xid=None):
    """Create a DHCP DISCOVER packet"""
    if mac_addr is None:
        mac_addr = random_mac()

    # Convert MAC address string to bytes
    mac_bytes = bytes.fromhex(mac_addr.replace(':', ''))

    if xid is None:
        xid = os.urandom(4)  # Random transaction ID

    # DHCP DISCOVER packet
    packet = b''
    packet += b'\x01'  # OP: Boot Request
    packet += b'\x01'  # HTYPE: Ethernet
    packet += b'\x06'  # HLEN: 6 bytes for MAC
    packet += b'\x00'  # HOPS: 0
    packet += xid  # XID: Transaction ID
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

    # DHCP Option 55 (Parameter Request List)
    requested_params = b'\x01\x03\x06\x0f\x1f\x21\x2b\x2c\x2e\x2f\x79\x21'
    packet += b'\x37' + bytes([len(requested_params)]) + requested_params

    # DHCP Option 255 (End)
    packet += b'\xff'

    # Pad to minimum DHCP packet size
    if len(packet) < 300:
        packet += b'\x00' * (300 - len(packet))

    return packet, mac_addr, xid

def send_dhcp_packet(packet, interface=None, server_addr='10.211.55.4', server_port=67):
    """Send a DHCP packet using a UDP socket"""
    try:
        # Create UDP socket
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

        # Send packet to DHCP server - using Kea server IP
        print(f"Sending to DHCP server at {server_addr}:{server_port}")
        s.sendto(packet, (server_addr, server_port))

        # Brief wait for response (optional)
        s.settimeout(1)
        try:
            response, addr = s.recvfrom(1024)
            print(f"Received response: {len(response)} bytes from {addr}")
            return response
        except socket.timeout:
            print("No response received (timeout)")
            return None
        finally:
            s.close()

    except Exception as e:
        print(f"Error sending DHCP packet: {e}")
        return None

def send_multiple_discovers(count=10, interval=0.5):
    """Send multiple DHCP DISCOVER packets"""
    print(f"Sending {count} DHCP DISCOVER packets...")

    # Try multiple interfaces if available
    interfaces = []
    try:
        # Get active interfaces
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for i in range(1, 10):  # Try common interface indices
            try:
                interface = socket.if_indextoname(i)
                if interface != 'lo':  # Skip loopback
                    interfaces.append(interface)
            except (OSError, IOError):
                pass
        s.close()
    except:
        pass

    # If no interfaces found, try default ones
    if not interfaces:
        interfaces = ['eth0', 'enp0s5', 'wlan0']

    # Also try no specific interface (let OS choose)
    interfaces.append(None)

    # Try sending to the Kea server IP specifically, as well as broadcast
    server_addresses = ['255.255.255.255', '10.211.55.4']

    for i in range(count):
        mac = random_mac()
        xid = os.urandom(4)
        packet, mac_str, _ = create_dhcp_discover(mac, xid)

        # Try different interfaces and server addresses
        for interface in interfaces:
            for server_addr in server_addresses:
                print(f"Sending DISCOVER via {'any' if interface is None else interface} "
                      f"to {server_addr} (MAC: {mac_str})")
                send_dhcp_packet(packet, interface, server_addr)

        time.sleep(interval)

    print(f"Sent {count} DHCP DISCOVER packets")

if __name__ == "__main__":
    # Check if script is running as root
    if os.geteuid() != 0:
        print("This script needs to be run as root to send raw packets")
        sys.exit(1)

    # Get count from command line if provided
    count = 5
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except:
            pass

    send_multiple_discovers(count)

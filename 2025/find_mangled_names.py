#!/usr/bin/env python3
# filepath: /home/parallels/Work/Tutorials/Hackathon/2025/find_mangled_names.py

import os
import sys
import subprocess

# Define the Kea binary path
kea_binary = "/home/parallels/Work/Blox/UDDI/ddi.vendor.kea/kea/install_area/sbin/kea-dhcp4"

# List of demangled names we want to find the mangled versions for
demangled_names = [
    "isc::dhcp::Pkt4::getType",
    "isc::dhcp::AllocEngine::allocateLease",
    "isc::dhcp::Option::getData",
    "isc::dhcp::Network::getCalculateTeeTimes",
    "isc::dhcp::DhcpConfigError::~DhcpConfigError",
    "isc::util::Triplet<unsigned int> isc::dhcp::Network::getProperty",
    "isc::dhcp::SrvConfig::addConfiguredGlobal"
]

print("Searching for mangled function names in Kea binary...")

try:
    # Get all symbols (both mangled and demangled)
    nm_output = subprocess.check_output(["nm", "-D", "-C", kea_binary], text=True)
    lines = nm_output.strip().split('\n')

    # Build a dictionary mapping demangled names to their mangled counterparts
    mangled_map = {}
    for line in lines:
        if " T " in line or " t " in line or " W " in line:
            parts = line.split()
            if len(parts) >= 3:
                mangled_name = parts[2] if len(parts) == 3 else parts[1]
                demangled_name = " ".join(parts[2:])
                for target in demangled_names:
                    if target in demangled_name:
                        if target not in mangled_map:
                            mangled_map[target] = []
                        mangled_map[target].append((mangled_name, demangled_name))

    # Now get the original mangled names (without demangling)
    nm_output_mangled = subprocess.check_output(["nm", "-D", kea_binary], text=True)
    mangled_lines = nm_output_mangled.strip().split('\n')
    mangled_symbols = []

    for line in mangled_lines:
        if " T " in line or " t " in line or " W " in line:
            parts = line.split()
            if len(parts) >= 2:
                mangled_name = parts[-1]
                mangled_symbols.append(mangled_name)

    # Print results
    print("\nMangled names found for target functions:")
    for target in demangled_names:
        print(f"\nTarget: {target}")
        if target in mangled_map:
            for i, (mangled, demangled) in enumerate(mangled_map[target]):
                print(f"  {i+1}. Mangled: {mangled}")
                print(f"     Demangled: {demangled}")

                # Check if this mangled name exists in the actual symbols
                matches = [sym for sym in mangled_symbols if mangled in sym]
                if matches:
                    print(f"     Actual symbol(s): {', '.join(matches)}")
                else:
                    print("     No matching actual symbol found")
        else:
            print("  No matches found")

    print("\nRecommendation:")
    print("Use the mangled names (Actual symbols) in your kea_metrics.py script")

except subprocess.CalledProcessError as e:
    print(f"Error examining {kea_binary}: {e}")
except FileNotFoundError:
    print("'nm' command not found. Please install binutils package.")
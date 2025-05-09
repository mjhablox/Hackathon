#!/usr/bin/env python3
# filepath: /home/parallels/Work/Tutorials/Hackathon/2025/list_all_functions.py

import subprocess
import re
import os

# Define the Kea binary path
kea_binary = "/home/parallels/Work/Blox/UDDI/ddi.vendor.kea/kea/install_area/sbin/kea-dhcp4"

print(f"Analyzing binary: {kea_binary}")
print("This may take a moment...")

# Get all function symbols with addresses
try:
    # Get all symbols with demangled names
    output = subprocess.check_output(
        ["nm", "--demangle", "--defined-only", "-D", kea_binary],
        text=True, stderr=subprocess.DEVNULL
    )

    # Filter for functions only
    functions = []
    for line in output.splitlines():
        if ' T ' in line or ' t ' in line or ' W ' in line:
            parts = line.split(' ', 2)  # Split into at most 3 parts
            if len(parts) >= 3:
                address = parts[0]
                symbol_type = parts[1]
                name = parts[2]
                functions.append((address, symbol_type, name))

    # Sort by function name
    functions.sort(key=lambda x: x[2].lower())

    # Filter for specific patterns we're interested in
    keywords = ["pkt4", "allocengine", "option", "network", "dhcpconfigerror",
               "triplet", "srvconfig", "gettype", "getdata", "allocatelease",
               "property", "calculate", "error", "query", "database"]

    # Print all functions first (for reference)
    print(f"\nFound {len(functions)} functions.")
    print("\n=== FUNCTIONS MATCHING KEYWORDS ===")
    for addr, type, name in functions:
        name_lower = name.lower()
        if any(kw in name_lower for kw in keywords):
            print(f"{addr} {type} {name}")

    print("\n=== RECOMMENDED MAPPINGS ===")
    print("Use these in your kea_metrics.py:")
    print("kea_functions = {")

    # Find best matches for each metric
    metrics = {
        "packet_processing": ["pkt4", "packet", "gettype"],
        "packet_drop": ["drop", "allocatelease", "alloc"],
        "cpu_usage": ["option", "getdata"],
        "memory_usage": ["network", "calculate", "memory"],
        "network_traffic": ["option", "getdata", "pkt"],
        "error_rates": ["error", "dhcpconfigerror", "exception"],
        "lease_allocation": ["lease", "triplet", "property"],
        "database_query": ["database", "query", "config", "global"]
    }

    for metric, search_terms in metrics.items():
        best_matches = []
        for addr, type, name in functions:
            name_lower = name.lower()
            if any(term in name_lower for term in search_terms):
                best_matches.append((addr, type, name))

        if best_matches:
            # Take the best match (could be improved)
            addr, type, name = best_matches[0]
            mangled_name = name.split('(')[0].strip()  # Just the function name part
            print(f"    # {metric}")

            if "processing" in metric:
                print(f'    "0x{addr}": ["trace_start", "trace_end"],')
            elif "allocation" in metric and not "drop" in metric:
                print(f'    "0x{addr}": ["trace_lease_allocation", "trace_lease_allocation_end"],')
            elif "database" in metric:
                print(f'    "0x{addr}": ["trace_database_query", "trace_database_query_end"],')
            else:
                trace_func = next((f"trace_{k}" for k in metric.split('_') if k in ["packet_drop", "cpu", "memory", "network", "error"]), f"trace_{metric}")
                print(f'    "0x{addr}": ["{trace_func}"],')

    print("}")

except subprocess.CalledProcessError as e:
    print(f"Error examining {kea_binary}: {e}")
except FileNotFoundError:
    print("'nm' command not found. Please install binutils package.")
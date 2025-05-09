#!/usr/bin/env python3
# filepath: /home/parallels/Work/Tutorials/Hackathon/2025/find_available_functions.py

import os
import sys
import subprocess

# Updated paths based on your system
kea_binary_paths = [
    "/home/parallels/Work/Blox/UDDI/ddi.vendor.kea/kea/install_area/sbin/kea-dhcp4",
    "/home/parallels/Work/Blox/UDDI/ddi.vendor.kea/kea/install_area/sbin/kea-dhcp-ddns",
    "/home/parallels/Work/Blox/UDDI/ddi.vendor.kea/kea/install_area/sbin/kea-ctrl-agent",
]

# Expanded keywords for better matching
keywords = ["process", "packet", "dhcp", "lease", "allocate", "drop", "handle", "query",
            "database", "recv", "send", "parse", "addr", "ip", "option", "msg", "message"]

print("Searching for Kea functions...")
results = {}

for binary_path in kea_binary_paths:
    if not os.path.exists(binary_path):
        print(f"Binary not found: {binary_path}")
        continue

    print(f"\nExamining: {binary_path}")

    # Try with -C for demangled C++ names
    try:
        print("Using nm with demangling (-C):")
        nm_output = subprocess.check_output(["nm", "-D", "-C", binary_path], text=True)

        # Filter functions and look for our keywords
        functions = []
        for line in nm_output.split("\n"):
            if " T " in line or " t " in line or " W " in line:
                parts = line.split()
                if len(parts) >= 3:
                    func_name = " ".join(parts[2:])
                else:
                    func_name = parts[-1] if parts else ""

                # Check if any keyword is in the function name
                if any(keyword in func_name.lower() for keyword in keywords):
                    functions.append(func_name)

        if functions:
            results[binary_path] = functions
            for func in sorted(functions):
                print(f"  {func}")
        else:
            print("  No matching functions found with demangling")

            # Try without demangling as fallback
            print("\nTrying without demangling:")
            nm_output = subprocess.check_output(["nm", "-D", binary_path], text=True)
            functions = []
            for line in nm_output.split("\n"):
                if " T " in line or " t " in line or " W " in line:
                    func_name = line.split()[-1]
                    if any(keyword in func_name.lower() for keyword in keywords):
                        functions.append(func_name)

            if functions:
                results[binary_path] = functions
                for func in sorted(functions):
                    print(f"  {func}")
            else:
                print("  No matching functions found")

    except subprocess.CalledProcessError as e:
        print(f"  Error examining {binary_path}: {e}")
    except FileNotFoundError:
        print("  'nm' command not found. Please install binutils package.")

if not results:
    print("\nNo functions found. Let's try some debug steps:")
    print("\n1. Check if the binaries have symbols:")
    for binary_path in kea_binary_paths:
        if os.path.exists(binary_path):
            try:
                output = subprocess.check_output(["file", binary_path], text=True)
                print(f"  {binary_path}: {output.strip()}")
                if "stripped" in output:
                    print("    ⚠️  This binary is stripped of debug symbols!")
            except Exception as e:
                print(f"  Error checking {binary_path}: {e}")

    print("\n2. Check if Kea is running:")
    try:
        ps_output = subprocess.check_output(["ps", "aux", "|", "grep", "kea"], shell=True, text=True)
        print(ps_output)
    except Exception:
        print("  Could not check running processes")

    print("\n3. Consider trying uprobes instead of kprobes in your script.")
else:
    print("\nFound potential functions to trace.")
    print("Update your kea_metrics.py script with these function names.")

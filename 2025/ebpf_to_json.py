#!/usr/bin/env python3
# Script to convert eBPF metrics histogram output to JSON format for visualization

import argparse
import json
import os
import re
import sys
from datetime import datetime

# Increase integer string conversion limit
sys.set_int_max_str_digits(10000)

def parse_ebpf_metrics(filepath):
    """Parse eBPF metrics output and convert to a structured format"""
    with open(filepath, 'r') as f:
        content = f.read()

    # Extract all histogram sections
    sections = re.findall(r'\n([A-Za-z\s]+):\n([\s\S]*?)(?=\n\n|\n[A-Za-z\s]+:|$)', content)

    # Dictionary to store structured metrics data
    metrics_json = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "source_file": os.path.basename(filepath)
        },
        "metrics": {}
    }

    for title, data in sections:
        title = title.strip()
        if 'No data' in data or ('error' in data.lower() and not '|' in data):
            print(f"Skipping '{title}' - no data available")
            continue

        # Parse histogram data
        try:
            rows = []
            for line in data.strip().split('\n'):
                if '->' in line and '|' in line:
                    # Format is like: "     0 -> 1          : 75       |********                                |"
                    match = re.search(r'(\d+)\s*->\s*(\d+)\s*:\s*(\d+)', line)
                    if match:
                        lower = int(match.group(1))
                        upper = int(match.group(2))
                        count = int(match.group(3))

                        # Calculate the actual values these represent
                        # (typically these are powers of 2 or ranges)
                        if title.lower().find("time") >= 0:
                            unit = "ns"
                        elif title.lower().find("cpu") >= 0:
                            unit = "cores"
                        elif title.lower().find("memory") >= 0:
                            unit = "bytes"
                        elif title.lower().find("traffic") >= 0 or title.lower().find("packet") >= 0:
                            unit = "packets"
                        elif title.lower().find("error") >= 0:
                            unit = "errors"
                        else:
                            unit = "count"

                        # Add to rows
                        try:
                            lower_value = 2**lower if lower > 0 else 0
                            upper_value = 2**upper - 1 if upper > 0 else 0
                            
                            # For very large values, represent as strings to avoid JSON limitations
                            if lower > 63:  # 2^63 is around the max safe integer in most systems
                                lower_value = f"2^{lower}"
                            if upper > 63:
                                upper_value = f"2^{upper}-1"
                            
                            rows.append({
                                "range": {
                                    "lower": lower,
                                    "upper": upper,
                                    "lower_value": lower_value,
                                    "upper_value": upper_value
                                },
                                "count": count,
                                "unit": unit
                            })
                        except (OverflowError, ValueError):
                            # Handle overflow by using string representation
                            rows.append({
                                "range": {
                                    "lower": lower,
                                    "upper": upper,
                                    "lower_value": f"2^{lower}",
                                    "upper_value": f"2^{upper}-1"
                                },
                                "count": count,
                                "unit": unit
                            })

            if rows:
                metrics_json["metrics"][title] = {
                    "data": rows,
                    "total": sum(row["count"] for row in rows)
                }
                print(f"Parsed '{title}' - {len(rows)} data points")
            else:
                print(f"No data points found in '{title}'")
        except Exception as e:
            print(f"Failed to parse section '{title}': {e}")    # Parse aggregate counts
    aggregates = re.search(r'Aggregate Counts:([\s\S]*?)$', content)
    if aggregates:
        agg_data = {}
        for line in aggregates.group(1).strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                try:
                    agg_data[key.strip()] = int(value.strip())
                except ValueError:
                    agg_data[key.strip()] = value.strip()
        
        if agg_data:
            metrics_json["aggregates"] = agg_data
            print(f"Parsed aggregate counts: {len(agg_data)} items")

    return metrics_json

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Convert eBPF metrics to JSON format')
    parser.add_argument('input_file', help='Path to the eBPF metrics output file')
    parser.add_argument('-o', '--output-file', help='Path to save the JSON output')
    parser.add_argument('--pretty', action='store_true', help='Pretty print the JSON output')
    args = parser.parse_args()

    # Default output filename
    if not args.output_file:
        filename, _ = os.path.splitext(os.path.basename(args.input_file))
        args.output_file = f"{filename}.json"

    # Check if input file exists
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return 1

    # Parse the metrics file
    metrics_json = parse_ebpf_metrics(args.input_file)

    # Write the JSON output
    with open(args.output_file, 'w') as f:
        if args.pretty:
            json.dump(metrics_json, f, indent=2)
        else:
            json.dump(metrics_json, f)

    print(f"Converted eBPF metrics to JSON: {args.output_file}")

    return 0

if __name__ == "__main__":
    sys.exit(main())

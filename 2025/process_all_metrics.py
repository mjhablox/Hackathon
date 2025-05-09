#!/usr/bin/env python3
# Script to process all metric files in the results directory
# and generate JSON and visualization files

import os
import sys
import argparse
import subprocess
import json
from datetime import datetime

def find_metric_files(base_dir):
    """Find all metric files in the results directory"""
    metric_files = []

    # Walk through the results directory
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.startswith('metrics_') and file.endswith('.txt'):
                full_path = os.path.join(root, file)
                # Check if the file has content
                if os.path.getsize(full_path) > 0:
                    metric_files.append(full_path)

    return metric_files

def process_metric_file(metric_file, ebpf_to_json_script, visualize_script, output_dir):
    """Process a single metric file"""
    print(f"\nProcessing: {metric_file}")

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get the base name without extension
    base_name = os.path.basename(metric_file).replace('.txt', '')

    # Define output JSON file path
    json_file = os.path.join(output_dir, f"{base_name}.json")

    # Convert the metrics to JSON
    print(f"Converting to JSON: {json_file}")
    result = subprocess.run(
        [ebpf_to_json_script, metric_file, "-o", json_file, "--pretty"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error converting to JSON: {result.stderr}")
        return False

    print(result.stdout)

    # Check if the JSON file was created
    if not os.path.exists(json_file):
        print(f"JSON file was not created: {json_file}")
        return False

    # Create visualization directory for this metric
    viz_dir = os.path.join(output_dir, f"viz_{base_name}")
    if not os.path.exists(viz_dir):
        os.makedirs(viz_dir)

    # Generate visualizations
    print(f"Generating visualizations in: {viz_dir}")
    result = subprocess.run(
        [visualize_script, json_file, "-o", viz_dir, "-v"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error generating visualizations: {result.stderr}")
        return False

    print(result.stdout)
    return True

def main():
    parser = argparse.ArgumentParser(description='Process all metric files and generate visualizations')
    parser.add_argument('-r', '--results-dir', default='./results',
                        help='Directory containing the metric files (default: ./results)')
    parser.add_argument('-o', '--output-dir', default='./processed',
                        help='Directory to save the processed files (default: ./processed)')
    parser.add_argument('--ebpf-to-json', default='./ebpf_to_json.py',
                        help='Path to the ebpf_to_json.py script (default: ./ebpf_to_json.py)')
    parser.add_argument('--visualize-script', default='./visualize_json_metrics.py',
                        help='Path to the visualize_json_metrics.py script (default: ./visualize_json_metrics.py)')
    args = parser.parse_args()

    # Find metric files
    metric_files = find_metric_files(args.results_dir)

    if not metric_files:
        print(f"No metric files found in {args.results_dir}")
        return 1

    print(f"Found {len(metric_files)} metric files")

    # Process each file
    success_count = 0
    for metric_file in metric_files:
        if process_metric_file(
            metric_file,
            args.ebpf_to_json,
            args.visualize_script,
            args.output_dir
        ):
            success_count += 1

    print(f"\nProcessed {success_count} of {len(metric_files)} metric files")

    # Create a summary file
    summary_file = os.path.join(args.output_dir, "summary.json")
    with open(summary_file, 'w') as f:
        summary = {
            "processed_date": datetime.now().isoformat(),
            "total_files": len(metric_files),
            "successful": success_count,
            "files": [os.path.basename(f) for f in metric_files]
        }
        json.dump(summary, f, indent=2)

    print(f"Summary saved to: {summary_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

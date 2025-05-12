#!/usr/bin/env python3
# Script to check and display metrics from a JSON file

import os
import sys
import json
import matplotlib.pyplot as plt

def check_metrics_file(file_path):
    """Check the structure of a metrics JSON file and display some data"""
    print(f"Checking metrics file: {file_path}")

    if not os.path.exists(file_path):
        print(f"Error: File does not exist: {file_path}")
        return False

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Check basic structure
        if 'metrics' not in data:
            print("Error: No 'metrics' key found in JSON data")
            return False

        metrics = data['metrics']
        print(f"Found {len(metrics)} metrics categories:")

        # Show metrics categories and counts
        for category, details in metrics.items():
            total = details.get('total', 'unknown')
            print(f"  - {category}: {total} total events")

            # Count non-zero data points
            data_points = details.get('data', [])
            non_zero = sum(1 for point in data_points if point.get('count', 0) > 0)
            print(f"    {len(data_points)} data points, {non_zero} non-zero values")

        # Show aggregate data if available
        if 'aggregates' in data:
            print("\nAggregate metrics:")
            for key, value in data['aggregates'].items():
                print(f"  - {key}: {value}")

        # Generate a simple plot to verify visualization works
        if len(metrics) > 0:
            plt.figure(figsize=(10, 6))

            # Get the first metric with non-zero data
            for category, details in metrics.items():
                data_points = details.get('data', [])
                counts = [point.get('count', 0) for point in data_points]
                labels = [f"Bin {i}" for i in range(len(counts))]

                if sum(counts) > 0:
                    plt.bar(labels, counts)
                    plt.title(f"Sample plot for: {category}")
                    plt.xlabel("Data bins")
                    plt.ylabel("Count")
                    plt.xticks(rotation=45)

                    print(f"\nCreated sample plot for '{category}' with {sum(counts)} total events")

                    # Save the plot
                    output_path = os.path.join(os.path.dirname(file_path), "diagnostic_plot.png")
                    plt.savefig(output_path)
                    print(f"Plot saved to: {output_path}")
                    plt.close()

                    break

        return True

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file: {e}")
        return False
    except Exception as e:
        print(f"Error processing metrics file: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_metrics.py <metrics_json_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    if check_metrics_file(file_path):
        print("\nMetrics file looks valid!")
    else:
        print("\nMetrics file has issues.")
        sys.exit(1)

#!/usr/bin/env python3
# Script to visualize Kea DHCP performance metrics

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import argparse
import os
import re
import datetime
import json
import sys

# Increase integer string conversion limit if needed
sys.set_int_max_str_digits(10000)

class MetricsVisualizer:
    """Class to visualize Kea DHCP metrics"""

    def __init__(self):
        """Initialize the visualizer"""
        self.metrics_data = {}
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    def parse_metrics_file(self, filepath):
        """Parse a metrics log file"""
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract all histogram sections
        sections = re.findall(r'\n([A-Za-z\s]+):\n([\s\S]*?)(?=\n\n|\n[A-Za-z\s]+:|$)', content)

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
                            rows.append((lower, upper, count))

                if rows:
                    self.metrics_data[title] = rows
                    print(f"Parsed '{title}' - {len(rows)} data points")
                else:
                    print(f"No data points found in '{title}'")
            except Exception as e:
                print(f"Failed to parse section '{title}': {e}")

    def create_visualizations(self, output_dir='./visualizations'):
        """Create visualizations for all metrics"""
        if not self.metrics_data:
            print("No metrics data to visualize")
            return

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Visualization count
        viz_count = 0

        # Create a visualization for each metric
        for title, data in self.metrics_data.items():
            if not data:
                continue

            # Clean title for filename
            clean_title = title.lower().replace(' ', '_')

            # Create figure
            plt.figure(figsize=(10, 6))

            # Prepare data for histogram
            labels = []
            values = []

            for lower, upper, count in data:
                # Safely handle large exponents to avoid integer overflow
                try:
                    # Format very large numbers using scientific notation instead of calculating 2^n
                    if upper == lower + 1:
                        if lower > 20:  # Use scientific notation for very large values
                            labels.append(f"2^{lower}")
                        else:
                            labels.append(f"{2 ** lower:,}")  # Add commas for readability
                    else:
                        if lower > 20 or upper > 20:  # Use scientific notation for very large values
                            labels.append(f"2^{lower}-2^{upper-1}")
                        else:
                            labels.append(f"{2 ** lower:,}-{2 ** (upper-1):,}")
                except (OverflowError, ValueError):
                    # Fall back to exponential notation for very large values
                    labels.append(f"2^{lower}-2^{upper-1}" if upper != lower + 1 else f"2^{lower}")
                values.append(count)

            # Plot histogram
            plt.bar(range(len(values)), values, tick_label=labels)
            plt.xticks(rotation=45, ha='right')
            plt.title(f"Kea DHCP - {title} (macOS Dras Traffic)")

            # Add units to the y-axis
            plt.ylabel('Frequency (count)')

            # Add units to the x-axis based on metric type
            if 'time' in title.lower():
                plt.xlabel('Time (ns)')
            elif 'cpu' in title.lower():
                plt.xlabel('CPU Core')
            elif 'memory' in title.lower():
                plt.xlabel('Memory Size (bytes)')
            elif 'traffic' in title.lower():
                plt.xlabel('Packet Count')
            elif 'error' in title.lower():
                plt.xlabel('Error Count')
            elif 'drop' in title.lower():
                plt.xlabel('Packet Count')
            else:
                plt.xlabel('Value Range')

            # Add a note about data source
            plt.figtext(0.5, 0.01, "Data source: macOS Dras client traffic",
                       ha="center", fontsize=8, style='italic')

            plt.tight_layout()

            # Save figure
            output_path = os.path.join(output_dir, f"{clean_title}_{self.timestamp}.png")
            plt.savefig(output_path)
            plt.close()

            viz_count += 1
            print(f"Created visualization for '{title}' at {output_path}")

        # Create summary chart if we have multiple metrics
        if len(self.metrics_data) > 1:
            self.create_summary_chart(output_dir)
            viz_count += 1

        print(f"\nCreated {viz_count} visualizations in {output_dir}")

    def create_summary_chart(self, output_dir):
        """Create a summary chart of all metrics"""
        plt.figure(figsize=(12, 8))

        # Prepare data for summary chart
        metrics = []
        totals = []

        for title, data in self.metrics_data.items():
            if not data:
                continue

            total = sum(count for _, _, count in data)
            metrics.append(title)
            totals.append(total)

        # Only create chart if we have data
        if metrics:
            # Sort by total
            sorted_data = sorted(zip(metrics, totals), key=lambda x: x[1], reverse=True)
            metrics, totals = zip(*sorted_data)

            # Plot horizontal bar chart
            plt.barh(metrics, totals)
            plt.xlabel('Total Events (count)')
            plt.ylabel('Metrics Categories')
            plt.title('Kea DHCP Metrics Summary (macOS Dras Traffic)')

            # Add a note about data source
            plt.figtext(0.5, 0.01, "Data source: macOS Dras client traffic",
                       ha="center", fontsize=8, style='italic')

            # Add data labels to the bars
            for i, v in enumerate(totals):
                plt.text(v + (max(totals) * 0.01), i, str(v), va='center')

            plt.tight_layout()

            # Save figure
            output_path = os.path.join(output_dir, f"summary_{self.timestamp}.png")
            plt.savefig(output_path)
            plt.close()

            print(f"Created summary visualization at {output_path}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Visualize Kea DHCP performance metrics')
    parser.add_argument('input_file', help='Path to the metrics log file')
    parser.add_argument('-o', '--output-dir', default='./visualizations',
                        help='Directory to save visualizations (default: ./visualizations)')
    args = parser.parse_args()

    # Check if input file exists
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return 1

    # Create visualizer and process the data
    visualizer = MetricsVisualizer()
    visualizer.parse_metrics_file(args.input_file)
    visualizer.create_visualizations(args.output_dir)

    return 0

if __name__ == "__main__":
    exit(main())

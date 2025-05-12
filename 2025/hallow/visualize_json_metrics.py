#!/usr/bin/env python3
# Script to visualize eBPF metrics from JSON format using matplotlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import argparse
import os
import sys
import json
from datetime import datetime

class JSONMetricsVisualizer:
    """Class to visualize eBPF metrics from JSON format"""

    def __init__(self):
        """Initialize the visualizer"""
        self.metrics_data = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_json_metrics(self, filepath):
        """Load metrics from a JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Extract metrics data
            if 'metrics' in data:
                self.metrics_data = data['metrics']
                print(f"Loaded metrics data with {len(self.metrics_data)} categories")

                # Extract metadata if available
                if 'metadata' in data:
                    self.metadata = data['metadata']
                    print(f"Source file: {self.metadata.get('source_file', 'unknown')}")
                    print(f"Timestamp: {self.metadata.get('timestamp', 'unknown')}")

                # Extract aggregates if available
                if 'aggregates' in data:
                    self.aggregates = data['aggregates']
                    print("Aggregate metrics available:", list(self.aggregates.keys()))
            else:
                print("No metrics data found in JSON file")
                return False

            return True
        except Exception as e:
            print(f"Failed to load JSON metrics: {e}")
            return False

    def create_visualizations(self, output_dir='./visualizations', create_latest=False):
        """Create visualizations for all metrics"""
        if not self.metrics_data:
            print("No metrics data to visualize")
            return

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Visualization count
        viz_count = 0

        # Create a visualization for each metric
        for title, metric_data in self.metrics_data.items():
            data = metric_data.get('data', [])
            if not data:
                continue

            # Clean title for filename
            clean_title = title.lower().replace(' ', '_')

            # Extract data
            ranges = [f"{d.get('range', {}).get('lower', '')}-{d.get('range', {}).get('upper', '')}" for d in data]
            values = [d.get('count', 0) for d in data]

            # Get units if available
            unit = data[0].get('unit', '') if data else ''

            # Only create visualization if we have data
            if not any(values):
                print(f"Skipping visualization for '{title}' - no non-zero values")
                continue

            # Create the visualization
            plt.figure(figsize=(10, 6))
            bars = plt.bar(ranges, values)

            # Format the chart
            plt.title(f"{title} Distribution")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.grid(axis='y', alpha=0.3)

            # Set appropriate labels based on the metric type
            if 'time' in title.lower():
                plt.xlabel(f'Time Range ({unit})')
            elif 'cpu' in title.lower():
                plt.xlabel(f'CPU Usage ({unit})')
            elif 'memory' in title.lower():
                plt.xlabel(f'Memory Usage ({unit})')
            elif 'network' in title.lower():
                plt.xlabel(f'Packet Count ({unit})')
            elif 'error' in title.lower():
                plt.xlabel(f'Error Count ({unit})')
            elif 'drop' in title.lower():
                plt.xlabel(f'Drop Count ({unit})')
            else:
                plt.xlabel(f'Value Range ({unit})')

            # Add data values on top of the bars
            for i, rect in enumerate(bars):
                height = rect.get_height()
                plt.text(rect.get_x() + rect.get_width()/2., height + 0.01 * max(values),
                         f'{height}',
                         ha='center', va='bottom', rotation=0)

            # Add a note about data source
            if hasattr(self, 'metadata') and 'source_file' in self.metadata:
                plt.figtext(0.5, 0.01, f"Data source: {self.metadata['source_file']}",
                           ha="center", fontsize=8, style='italic')

            plt.tight_layout()

            # Save figure with timestamp
            output_path = os.path.join(output_dir, f"{clean_title}_{self.timestamp}.png")
            plt.savefig(output_path)

            # Save a latest version if requested
            if create_latest:
                latest_path = os.path.join(output_dir, f"{clean_title}_latest.png")
                plt.savefig(latest_path)
                print(f"Created latest version at {latest_path}")

            plt.close()

            viz_count += 1
            print(f"Created visualization for '{title}' at {output_path}")

        # Create summary chart if we have multiple metrics
        if len(self.metrics_data) > 1:
            self.create_summary_chart(output_dir, create_latest)
            viz_count += 1

        print(f"\nCreated {viz_count} visualizations in {output_dir}")

    def create_summary_chart(self, output_dir, create_latest=False):
        """Create a summary chart of all metrics"""
        plt.figure(figsize=(12, 8))

        # Prepare data for summary chart
        metrics = []
        totals = []

        for title, metric_data in self.metrics_data.items():
            total = metric_data.get('total', 0)
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
            plt.title('eBPF Metrics Summary')

            # Add data labels to the bars
            for i, v in enumerate(totals):
                plt.text(v + (max(totals) * 0.01), i, str(v), va='center')

            # Add a note about data source
            if hasattr(self, 'metadata') and 'source_file' in self.metadata:
                plt.figtext(0.5, 0.01, f"Data source: {self.metadata['source_file']}",
                           ha="center", fontsize=8, style='italic')

            plt.tight_layout()

            # Save figure with timestamp
            output_path = os.path.join(output_dir, f"summary_{self.timestamp}.png")
            plt.savefig(output_path)

            # Save a latest version if requested
            if create_latest:
                latest_path = os.path.join(output_dir, f"summary_latest.png")
                plt.savefig(latest_path)
                print(f"Created latest version at {latest_path}")

            plt.close()

            print(f"Created summary visualization at {output_path}")

    def create_aggregate_chart(self, output_dir, create_latest=False):
        """Create a chart of aggregate metrics"""
        if not hasattr(self, 'aggregates') or not self.aggregates:
            print("No aggregate data available")
            return

        plt.figure(figsize=(10, 6))

        # Extract data
        labels = list(self.aggregates.keys())
        values = list(self.aggregates.values())

        # Plot bar chart
        plt.bar(labels, values)
        plt.xlabel('Metric')
        plt.ylabel('Count')
        plt.title('eBPF Aggregate Metrics')
        plt.xticks(rotation=45, ha='right')

        # Add data labels above bars
        for i, v in enumerate(values):
            plt.text(i, v + 0.01 * max(values), str(v), ha='center')

        plt.tight_layout()

        # Save figure with timestamp
        output_path = os.path.join(output_dir, f"aggregates_{self.timestamp}.png")
        plt.savefig(output_path)

        # Save a latest version if requested
        if create_latest:
            latest_path = os.path.join(output_dir, f"aggregates_latest.png")
            plt.savefig(latest_path)
            print(f"Created latest version at {latest_path}")

        plt.close()

        print(f"Created aggregate metrics visualization at {output_path}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Visualize eBPF metrics from JSON format')
    parser.add_argument('input_file', help='Path to the JSON metrics file')
    parser.add_argument('-o', '--output-dir', default='./visualizations',
                        help='Directory to save visualizations (default: ./visualizations)')
    parser.add_argument('--create-latest', action='store_true',
                        help='Create files with _latest suffix for real-time dashboard')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output for debugging')
    args = parser.parse_args()

    if args.verbose:
        print(f"Starting visualization process with input file: {args.input_file}")
        print(f"Output directory: {args.output_dir}")

    # Check if input file exists
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return 1

    try:
        # Create visualizer and process the data
        visualizer = JSONMetricsVisualizer()

        if args.verbose:
            print("Loading JSON metrics data...")

        if visualizer.load_json_metrics(args.input_file):
            if args.verbose:
                print(f"JSON data loaded successfully. Metrics: {list(visualizer.metrics_data.keys())}")

            # Pass the create_latest flag to the visualization function
            generate_latest = args.create_latest
            if generate_latest and args.verbose:
                print("Creating visualizations with _latest suffix for real-time dashboard")

            visualizer.create_visualizations(args.output_dir, generate_latest)

            if hasattr(visualizer, 'aggregates'):
                if args.verbose:
                    print("Found aggregate data, creating aggregate chart...")
                visualizer.create_aggregate_chart(args.output_dir, generate_latest)
        else:
            print("Failed to process metrics data")
            return 1
    except Exception as e:
        print(f"Error during visualization: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())

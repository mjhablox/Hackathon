#!/usr/bin/env python3
# Script to convert eBPF metrics to Netflix Hollow format and push to a Hollow producer

import argparse
import json
import os
import sys
import requests
from datetime import datetime
import uuid

class HollowProducer:
    """A simple client for pushing data to a Hollow producer API"""

    def __init__(self, producer_url, auth_token=None):
        """Initialize the Hollow producer client"""
        self.producer_url = producer_url
        self.headers = {
            'Content-Type': 'application/json'
        }
        if auth_token:
            self.headers['Authorization'] = f'Bearer {auth_token}'

    def announce_dataset(self, dataset_name, dataset_version):
        """Announce a new dataset version to the Hollow producer"""
        endpoint = f"{self.producer_url}/api/datasets/{dataset_name}/versions"
        payload = {
            "version": dataset_version,
            "status": "ANNOUNCING"
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to announce dataset: {e}")
            return None

    def publish_data(self, dataset_name, dataset_version, data):
        """Publish data to the announced dataset version"""
        endpoint = f"{self.producer_url}/api/datasets/{dataset_name}/versions/{dataset_version}/data"

        try:
            response = requests.post(endpoint, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to publish data: {e}")
            return None

    def publish_version(self, dataset_name, dataset_version):
        """Finalize and publish the dataset version"""
        endpoint = f"{self.producer_url}/api/datasets/{dataset_name}/versions/{dataset_version}/status"
        payload = {
            "status": "PUBLISHED"
        }

        try:
            response = requests.put(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to publish version: {e}")
            return None


def convert_metrics_to_hollow(metrics_json):
    """Convert the metrics JSON to a Hollow-compatible format"""
    hollow_data = {
        "types": {
            "MetricsState": {
                "fields": {
                    "timestamp": "String",
                    "source": "String",
                    "metrics": "Map<String, Metric>",
                    "aggregates": "Map<String, Integer>"
                }
            },
            "Metric": {
                "fields": {
                    "name": "String",
                    "total": "Integer",
                    "unit": "String",
                    "buckets": "List<MetricBucket>"
                }
            },
            "MetricBucket": {
                "fields": {
                    "lower": "Integer",
                    "upper": "Integer",
                    "count": "Integer"
                }
            }
        },
        "data": {
            "MetricsState": [
                {
                    "timestamp": metrics_json.get("metadata", {}).get("timestamp", datetime.now().isoformat()),
                    "source": metrics_json.get("metadata", {}).get("source_file", "unknown"),
                    "metrics": {},
                    "aggregates": {}
                }
            ]
        }
    }

    # Fill in metrics data
    metrics_state = hollow_data["data"]["MetricsState"][0]
    metrics = metrics_json.get("metrics", {})

    for metric_name, metric_data in metrics.items():
        buckets = []
        unit = "count"  # Default unit

        for bucket in metric_data.get("data", []):
            if "unit" in bucket:
                unit = bucket["unit"]

            buckets.append({
                "lower": bucket.get("range", {}).get("lower", 0),
                "upper": bucket.get("range", {}).get("upper", 0),
                "count": bucket.get("count", 0)
            })

        metrics_state["metrics"][metric_name] = {
            "name": metric_name,
            "total": metric_data.get("total", 0),
            "unit": unit,
            "buckets": buckets
        }

    # Fill in aggregates
    if "aggregates" in metrics_json:
        metrics_state["aggregates"] = metrics_json["aggregates"]

    return hollow_data


def push_to_hollow(hollow_data, producer_url, dataset_name, auth_token=None):
    """Push the Hollow-formatted data to a Hollow producer"""
    producer = HollowProducer(producer_url, auth_token)

    # Generate a version identifier based on the current timestamp
    version = int(datetime.now().timestamp() * 1000)  # milliseconds since epoch

    print(f"Pushing to Hollow producer at {producer_url}")
    print(f"Dataset: {dataset_name}")
    print(f"Version: {version}")

    # Announce the dataset version
    result = producer.announce_dataset(dataset_name, version)
    if not result:
        return False

    # Publish the data
    result = producer.publish_data(dataset_name, version, hollow_data)
    if not result:
        return False

    # Finalize and publish the version
    result = producer.publish_version(dataset_name, version)
    if not result:
        return False

    print(f"Successfully published data to Hollow producer")
    print(f"Dataset {dataset_name} version {version} is now available")
    return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Convert eBPF metrics to Netflix Hollow format and push to a producer')
    parser.add_argument('input_file', help='Path to the JSON metrics file')
    parser.add_argument('-p', '--producer-url', required=True,
                       help='URL of the Hollow producer API')
    parser.add_argument('-d', '--dataset-name', default='ebpf_metrics',
                       help='Name of the dataset in Hollow (default: ebpf_metrics)')
    parser.add_argument('-t', '--auth-token',
                       help='Authentication token for the Hollow producer API')
    parser.add_argument('--dry-run', action='store_true',
                       help='Process the data but do not push to Hollow')
    parser.add_argument('--output',
                       help='Save the Hollow-formatted data to this file (optional)')
    args = parser.parse_args()

    # Check if input file exists
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return 1

    # Load the metrics JSON
    try:
        with open(args.input_file, 'r') as f:
            metrics_json = json.load(f)
    except Exception as e:
        print(f"Failed to load JSON metrics: {e}")
        return 1

    # Convert to Hollow format
    try:
        hollow_data = convert_metrics_to_hollow(metrics_json)
        print(f"Successfully converted metrics to Hollow format")
    except Exception as e:
        print(f"Failed to convert metrics to Hollow format: {e}")
        return 1

    # Save to output file if specified
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(hollow_data, f, indent=2)
            print(f"Saved Hollow-formatted data to {args.output}")
        except Exception as e:
            print(f"Failed to save output file: {e}")

    # Push to Hollow unless in dry-run mode
    if not args.dry_run:
        try:
            success = push_to_hollow(
                hollow_data,
                args.producer_url,
                args.dataset_name,
                args.auth_token
            )
            if not success:
                print("Failed to push data to Hollow producer")
                return 1
        except Exception as e:
            print(f"Error pushing to Hollow producer: {e}")
            return 1
    else:
        print("Dry run mode - not pushing to Hollow producer")

    return 0


if __name__ == "__main__":
    sys.exit(main())

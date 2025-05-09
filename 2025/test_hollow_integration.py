#!/usr/bin/env python3
# Test script to demonstrate Netflix Hollow integration with sample data

import os
import sys
import argparse
import subprocess
import time
import json
from datetime import datetime

def test_hollow_integration(producer_url, auth_token=None, dry_run=True):
    """Test the Netflix Hollow integration with sample data"""
    print("\n=== Netflix Hollow Integration Test ===\n")

    # Create a timestamp for this test
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create a test directory
    test_dir = f"./hollow_test_{timestamp}"
    os.makedirs(test_dir, exist_ok=True)
    print(f"Created test directory: {test_dir}")

    # Step 1: Convert sample metrics to JSON
    sample_json = os.path.join(test_dir, "sample_metrics.json")
    print("\nStep 1: Converting sample metrics to JSON...")

    try:
        result = subprocess.run(
            ["./ebpf_to_json.py", "sample_metrics.txt", "-o", sample_json, "--pretty"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(result.stdout)
        print(f"✅ Successfully created JSON file: {sample_json}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to convert sample metrics: {e.stderr}")
        return False

    # Step 2: Convert JSON to Hollow format
    hollow_json = os.path.join(test_dir, "hollow_format.json")
    print("\nStep 2: Converting JSON to Hollow format...")

    cmd = [
        "./ebpf_to_hollow.py",
        sample_json,
        "-p", producer_url,
        "--dry-run",  # Always do dry run in test
        "--output", hollow_json
    ]

    if auth_token:
        cmd.extend(["-t", auth_token])

    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(result.stdout)
        print(f"✅ Successfully created Hollow format file: {hollow_json}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to convert to Hollow format: {e.stderr}")
        return False

    # Step 3: Verify the Hollow format
    print("\nStep 3: Verifying Hollow format...")
    try:
        with open(hollow_json, 'r') as f:
            hollow_data = json.load(f)

        # Check basic structure
        if "types" not in hollow_data or "data" not in hollow_data:
            print("❌ Invalid Hollow format: Missing 'types' or 'data' sections")
            return False

        if "MetricsState" not in hollow_data["types"]:
            print("❌ Invalid Hollow format: Missing 'MetricsState' type")
            return False

        if "MetricsState" not in hollow_data["data"]:
            print("❌ Invalid Hollow format: Missing 'MetricsState' data")
            return False

        # Check metrics data
        metrics_state = hollow_data["data"]["MetricsState"][0]
        if "metrics" not in metrics_state or "aggregates" not in metrics_state:
            print("❌ Invalid Hollow format: Missing 'metrics' or 'aggregates'")
            return False

        print(f"✅ Hollow format is valid")
        print(f"  - Found {len(metrics_state['metrics'])} metrics")
        print(f"  - Found {len(metrics_state['aggregates'])} aggregate values")

    except Exception as e:
        print(f"❌ Failed to validate Hollow format: {e}")
        return False

    # Step 4: Push to Hollow (if not in dry_run mode)
    if not dry_run:
        print("\nStep 4: Pushing to Hollow producer...")
        cmd = [
            "./ebpf_to_hollow.py",
            sample_json,
            "-p", producer_url
        ]

        if auth_token:
            cmd.extend(["-t", auth_token])

        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(result.stdout)
            print(f"✅ Successfully pushed data to Hollow producer")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to push to Hollow producer: {e.stderr}")
            return False
    else:
        print("\nStep 4: Skipping push to Hollow (dry run mode)")

    print("\n=== Test Completed Successfully ===")
    print(f"Test artifacts are available in: {test_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Test Netflix Hollow integration with sample data')
    parser.add_argument('-p', '--producer-url', default='http://hollow-producer.example.com/api',
                       help='URL of the Hollow producer API')
    parser.add_argument('-t', '--auth-token',
                       help='Authentication token for the Hollow producer API')
    parser.add_argument('--push', action='store_true',
                       help='Actually push data to Hollow producer (default is dry run)')
    args = parser.parse_args()

    success = test_hollow_integration(
        args.producer_url,
        args.auth_token,
        not args.push  # dry_run is the opposite of push
    )

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

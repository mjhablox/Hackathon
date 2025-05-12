#!/usr/bin/env python3
# Script to diagnose and troubleshoot common issues with the eBPF-Hollow dashboard

import os
import sys
import json
import argparse
import logging
import subprocess
import socket
import requests
from pathlib import Path
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Dashboard-Diagnostics")

def check_file_exists(filepath, description):
    """Check if a file exists and log the result"""
    if os.path.exists(filepath):
        logger.info(f"✓ {description} exists: {filepath}")
        return True
    else:
        logger.error(f"✗ {description} not found: {filepath}")
        return False

def check_json_structure(filepath):
    """Check if a JSON file has the expected structure for metrics"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Check for required keys
        required_keys = ["metrics"]
        missing_keys = [key for key in required_keys if key not in data]

        if missing_keys:
            logger.error(f"✗ JSON file {filepath} is missing required keys: {', '.join(missing_keys)}")
            return False

        # Check metrics structure
        metrics = data["metrics"]
        if not metrics or not isinstance(metrics, dict):
            logger.error(f"✗ JSON file {filepath} has empty or invalid metrics data")
            return False

        # Check if at least one metric category has data
        has_data = False
        for category, details in metrics.items():
            if "data" in details and details["data"]:
                has_data = True
                break

        if not has_data:
            logger.warning(f"⚠ JSON file {filepath} has metrics but no actual data points")
            return True

        logger.info(f"✓ JSON file {filepath} has valid metrics structure with data")
        return True

    except json.JSONDecodeError:
        logger.error(f"✗ File {filepath} is not valid JSON")
        return False
    except Exception as e:
        logger.error(f"✗ Error checking JSON structure of {filepath}: {e}")
        return False

def check_port_available(port):
    """Check if a port is available or already in use"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()

    if result == 0:
        # Port is already in use
        logger.warning(f"⚠ Port {port} is already in use (possibly by the dashboard server)")
        # Try to determine what's using the port
        try:
            if sys.platform.startswith('linux'):
                output = subprocess.check_output(['lsof', '-i', f':{port}'], text=True)
                logger.info(f"Process using port {port}:\n{output}")
            elif sys.platform == 'darwin':
                output = subprocess.check_output(['lsof', '-i', f':{port}'], text=True)
                logger.info(f"Process using port {port}:\n{output}")
            elif sys.platform == 'win32':
                output = subprocess.check_output(['netstat', '-ano', '|', 'findstr', f':{port}'], text=True)
                logger.info(f"Process using port {port}:\n{output}")
        except:
            pass
        return False
    else:
        logger.info(f"✓ Port {port} is available")
        return True

def validate_visualizations(viz_dir):
    """Check visualization files in the specified directory"""
    if not os.path.exists(viz_dir) or not os.path.isdir(viz_dir):
        logger.error(f"✗ Visualization directory does not exist: {viz_dir}")
        return False

    # Expected visualization files
    expected_viz_files = [
        "summary_latest.png", "aggregates_latest.png", "cpu_usage_latest.png",
        "memory_usage_latest.png", "network_traffic_latest.png", "error_rates_latest.png",
        "packet_processing_time_latest.png", "packet_drop_rate_latest.png",
        "lease_allocation_time_latest.png", "database_query_performance_latest.png"
    ]

    # Check if visualization files exist
    missing_files = []
    has_placeholders = 0
    has_real_data = 0

    for viz_file in expected_viz_files:
        filepath = os.path.join(viz_dir, viz_file)
        if os.path.exists(filepath):
            # Check file size to determine if it's a placeholder or real data
            file_size = os.path.getsize(filepath)
            if file_size < 5000:  # Small files are likely placeholders
                has_placeholders += 1
                logger.debug(f"  - {viz_file}: Likely a placeholder image ({file_size} bytes)")
            else:
                has_real_data += 1
                logger.debug(f"  - {viz_file}: Likely has real data ({file_size} bytes)")
        else:
            missing_files.append(viz_file)

    # Log summary
    if not missing_files:
        logger.info(f"✓ All {len(expected_viz_files)} expected visualization files exist")
    else:
        logger.warning(f"⚠ Missing {len(missing_files)} visualization files: {', '.join(missing_files)}")

    logger.info(f"  - Files with likely real data: {has_real_data}")
    logger.info(f"  - Files that appear to be placeholders: {has_placeholders}")

    # Check if dashboard HTML exists
    dashboard_path = os.path.join(viz_dir, "index.html")
    if os.path.exists(dashboard_path):
        logger.info(f"✓ Dashboard HTML file exists: {dashboard_path}")
    else:
        logger.error(f"✗ Dashboard HTML file not found: {dashboard_path}")

    return not missing_files

def check_hollow_connection(producer_url):
    """Check if the Hollow producer is reachable"""
    try:
        response = requests.get(f"{producer_url}/api/status", timeout=3)
        response.raise_for_status()
        logger.info(f"✓ Hollow producer is reachable at {producer_url}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ Could not connect to Hollow producer at {producer_url}: {e}")
        return False

def check_local_hollow():
    """Check if local Hollow setup is available"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    hollow_local_dir = os.path.join(script_dir, "hollow-local")
    run_producer_script = os.path.join(hollow_local_dir, "run_producer.sh")

    if os.path.exists(run_producer_script):
        logger.info(f"✓ Local Hollow producer found at {hollow_local_dir}")

        # Check if producer is already running
        try:
            response = requests.get("http://localhost:7001/api/status", timeout=2)
            if response.status_code == 200:
                logger.info(f"✓ Local Hollow producer is running on port 7001")
            else:
                logger.warning(f"⚠ Local Hollow producer is not running (got status code {response.status_code})")
        except requests.exceptions.RequestException:
            logger.warning(f"⚠ Local Hollow producer is not currently running")

        return True
    else:
        logger.warning(f"⚠ Local Hollow producer not found at {hollow_local_dir}")
        return False

def validate_metrics_json(json_file):
    """Validate a metrics JSON file and generate a diagnostic plot"""
    if not os.path.exists(json_file):
        logger.error(f"✗ Metrics JSON file not found: {json_file}")
        return False

    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        # Check if metrics exist
        if "metrics" not in data or not data["metrics"]:
            logger.error(f"✗ JSON file {json_file} has no metrics data")
            return False

        # Get metrics info
        metrics = data["metrics"]
        num_categories = len(metrics)

        # Print metrics summary
        logger.info(f"✓ JSON file {json_file} contains {num_categories} metrics categories")

        # Count data points
        total_points = 0
        non_zero_points = 0
        categories = []
        point_counts = []

        for category, details in metrics.items():
            category_points = len(details.get("data", []))
            total_points += category_points

            # Count non-zero data points
            category_non_zero = sum(1 for point in details.get("data", [])
                                    if point.get("count", 0) > 0)
            non_zero_points += category_non_zero

            logger.info(f"  - {category}: {category_points} data points, {category_non_zero} non-zero")

            categories.append(category)
            point_counts.append(category_non_zero)

        logger.info(f"  Total: {total_points} data points, {non_zero_points} non-zero")

        # Generate diagnostic plot if there's data
        if categories and point_counts:
            plt.figure(figsize=(10, 6))
            plt.bar(categories, point_counts)
            plt.title('Non-zero Data Points by Category')
            plt.xlabel('Category')
            plt.ylabel('Number of Non-zero Data Points')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            # Save diagnostic plot
            script_dir = os.path.dirname(os.path.abspath(__file__))
            plot_path = os.path.join(script_dir, "diagnostic_plot.png")
            plt.savefig(plot_path)
            logger.info(f"✓ Diagnostic plot saved to {plot_path}")
            plt.close()

        return True

    except json.JSONDecodeError:
        logger.error(f"✗ File {json_file} is not valid JSON")
        return False
    except Exception as e:
        logger.error(f"✗ Error validating JSON file {json_file}: {e}")
        return False

def run_diagnostics(args):
    """Run all diagnostic checks"""
    success = True

    # 1. Check for the kea_metrics.py script
    kea_metrics_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kea_metrics.py")
    if check_file_exists(kea_metrics_path, "kea_metrics.py"):
        logger.info("eBPF metrics collection dependencies are available")
    else:
        logger.warning("Missing kea_metrics.py script may affect metrics collection")
        logger.info(f"You can copy it from: {os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')}")
        success = False

    # 2. Check test_metrics.json file for fallback
    test_metrics_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_metrics.json")
    if check_file_exists(test_metrics_path, "test_metrics.json"):
        check_json_structure(test_metrics_path)
    else:
        logger.warning("Missing test_metrics.json file will disable fallback mode")
        success = False

    # 3. Check dashboard port
    check_port_available(args.dashboard_port)

    # 4. Check visualizations directory
    viz_dir = args.viz_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "realtime_visualizations")
    validate_visualizations(viz_dir)

    # 5. Check Hollow connection
    if args.local:
        check_local_hollow()
    else:
        check_hollow_connection(args.producer_url or "http://localhost:7001")

    # 6. Validate a specific JSON metrics file if provided
    if args.json_file and os.path.exists(args.json_file):
        validate_metrics_json(args.json_file)

    return success

def main():
    parser = argparse.ArgumentParser(description='Diagnose and troubleshoot eBPF-Hollow dashboard issues')
    parser.add_argument('-p', '--producer-url',
                        help='URL of the Hollow producer API (default: http://localhost:7001)')
    parser.add_argument('--local', action='store_true',
                        help='Check local Hollow setup instead of remote producer')
    parser.add_argument('--dashboard-port', type=int, default=8080,
                        help='Dashboard server port to check (default: 8080)')
    parser.add_argument('--viz-dir',
                        help='Directory containing visualizations (default: realtime_visualizations)')
    parser.add_argument('--json-file',
                        help='JSON metrics file to validate')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    print("\n=== eBPF-Hollow Dashboard Diagnostics ===\n")

    success = run_diagnostics(args)

    print("\n=== Diagnostic Summary ===")
    if success:
        print("✓ All critical components are available and properly configured")
    else:
        print("⚠ Some issues were detected. Review the log messages above for details.")

    print("\nTo start the dashboard with all fixes, run: ./run_realtime_dashboard.sh")

    return 0 if success else 1

if __name__ == "__main__":
    try:
        # Make sure output is visible even if there's no TTY
        import sys
        sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
    except:
        pass
    sys.exit(main())

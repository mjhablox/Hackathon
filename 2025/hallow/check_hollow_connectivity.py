#!/usr/bin/env python3
# Script to check connectivity to the Netflix Hollow producer server

import argparse
import requests
import sys
import os
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Hollow-Connectivity-Check")

def check_hollow_connection(producer_url, timeout=5):
    """Check if the Hollow producer is reachable and operational"""
    logger.info(f"Testing connectivity to Hollow producer at {producer_url}")

    try:
        # Try to connect to the API status endpoint
        response = requests.get(f"{producer_url}/api/status", timeout=timeout)
        response.raise_for_status()

        # Parse response
        status_data = response.json()

        # Print status information
        logger.info("Hollow producer is reachable")
        logger.info(f"Status: {status_data.get('status', 'Unknown')}")

        # Check for available datasets
        try:
            datasets_response = requests.get(f"{producer_url}/api/datasets", timeout=timeout)
            datasets_response.raise_for_status()
            datasets = datasets_response.json()

            if datasets:
                logger.info(f"Available datasets: {len(datasets)}")
                for dataset in datasets:
                    logger.info(f" - {dataset.get('name')}: {dataset.get('version', 'Unknown version')}")
            else:
                logger.info("No datasets available on this producer")
        except Exception as e:
            logger.warning(f"Could not retrieve datasets: {e}")

        return True

    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error: Could not connect to {producer_url}")
        logger.info("The Hollow server appears to be offline or unreachable")
        return False

    except requests.exceptions.Timeout:
        logger.error(f"Timeout: Connection to {producer_url} timed out after {timeout} seconds")
        logger.info("The Hollow server might be overloaded or unreachable")
        return False

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        logger.info("The Hollow server is reachable but returned an HTTP error")
        return False

    except Exception as e:
        logger.error(f"Unexpected error while checking Hollow connectivity: {e}")
        return False

def check_local_hollow():
    """Check if local Hollow setup is available"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    hollow_local_dir = os.path.join(script_dir, "hollow-local")
    run_producer_script = os.path.join(hollow_local_dir, "run_producer.sh")

    if os.path.exists(run_producer_script):
        logger.info(f"Local Hollow producer found at {hollow_local_dir}")
        logger.info(f"You can start it using: {run_producer_script}")

        # Check if producer is already running
        try:
            response = requests.get("http://localhost:7001/api/status", timeout=2)
            if response.status_code == 200:
                logger.info("Local Hollow producer appears to be running on port 7001")
                return True
        except:
            logger.info("Local Hollow producer is not currently running")

        return True
    else:
        logger.error(f"Local Hollow producer not found at {hollow_local_dir}")
        logger.info("You can install it by running ./install_deps.sh and answering 'y' to install Hollow locally")
        return False

def main():
    parser = argparse.ArgumentParser(description='Check connectivity to Netflix Hollow producer server')
    parser.add_argument('-p', '--producer-url', default='http://localhost:7001',
                        help='URL of the Hollow producer API (default: http://localhost:7001)')
    parser.add_argument('--local', action='store_true',
                        help='Check local Hollow setup instead of remote producer')
    parser.add_argument('-t', '--timeout', type=int, default=5,
                        help='Connection timeout in seconds (default: 5)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Run the appropriate check
    if args.local:
        success = check_local_hollow()
    else:
        success = check_hollow_connection(args.producer_url, args.timeout)

    # Return appropriate exit code
    return 0 if success else 1

def print_banner():
    """Print a banner for the tool"""
    print("\n======================================================")
    print("  Netflix Hollow Connectivity Check Tool")
    print("======================================================\n")

if __name__ == "__main__":
    print_banner()
    sys.exit(main())

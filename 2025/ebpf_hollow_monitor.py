#!/usr/bin/env python3
# Script to continuously monitor eBPF metrics and push them to Netflix Hollow

import os
import sys
import time
import argparse
import subprocess
import json
import signal
import logging
from datetime import datetime
import uuid
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("eBPF-Hollow-Integration")

# Global flag for exiting
exiting = False

def signal_handler(sig, frame):
    """Handle termination signals"""
    global exiting
    logger.info("Received termination signal. Shutting down...")
    exiting = True

def run_metrics_collection(duration, output_file, args=None):
    """Run the eBPF metrics collection for the specified duration"""
    logger.info(f"Starting eBPF metrics collection for {duration} seconds")

    try:
        # Run the kea_metrics.py script with a timeout
        process = subprocess.Popen(
            ["sudo", "python3", "kea_metrics.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for the specified duration
        time.sleep(duration)

        # Send SIGINT to stop the metrics collection gracefully
        process.send_signal(signal.SIGINT)

        # Capture the output with a timeout
        stdout, stderr = process.communicate(timeout=10)

        # Write the output to the specified file
        with open(output_file, 'w') as f:
            f.write(stdout)

        logger.info(f"Metrics collection completed and saved to {output_file}")
        return True

    except subprocess.TimeoutExpired:
        logger.error("Metrics collection timed out")
        process.kill()
        process.communicate()

        # Check if fallback is disabled
        if args and hasattr(args, 'no_fallback') and args.no_fallback:
            logger.warning("Fallback to sample metrics is disabled. Skipping metrics collection.")
            return False

        # Fall back to using the sample metrics file
        logger.info("Using sample metrics data instead")
        try:
            sample_metrics_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_metrics.txt")
            if os.path.exists(sample_metrics_path):
                with open(sample_metrics_path, 'r') as src:
                    with open(output_file, 'w') as dst:
                        dst.write(src.read())
                logger.info(f"Using sample metrics from {sample_metrics_path}")
                return True
            logger.error("No sample metrics file found")
            return False
        except Exception as e:
            logger.error(f"Failed to use sample metrics: {e}")
            return False

    except Exception as e:
        logger.error(f"Error during metrics collection: {e}")
        if process.poll() is None:
            process.kill()

        # Check if fallback is disabled
        if args and hasattr(args, 'no_fallback') and args.no_fallback:
            logger.warning("Fallback to sample metrics is disabled. Skipping metrics collection.")
            return False

        # Fall back to using the sample metrics file
        logger.info("Using sample metrics data instead")
        try:
            sample_metrics_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_metrics.txt")
            if os.path.exists(sample_metrics_path):
                with open(sample_metrics_path, 'r') as src:
                    with open(output_file, 'w') as dst:
                        dst.write(src.read())
                logger.info(f"Using sample metrics from {sample_metrics_path}")
                return True
            logger.error("No sample metrics file found")
            return False
        except Exception as e:
            logger.error(f"Failed to use sample metrics: {e}")
            return False

def convert_to_json(metrics_file, json_file):
    """Convert the metrics file to JSON format"""
    logger.info(f"Converting metrics to JSON format: {json_file}")

    try:
        result = subprocess.run(
            ["python3", "ebpf_to_json.py", metrics_file, "-o", json_file],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info("JSON conversion completed successfully")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"JSON conversion failed: {e.stderr}")
        return False

    except Exception as e:
        logger.error(f"Error during JSON conversion: {e}")
        return False

def push_to_hollow(json_file, producer_url, dataset_name, auth_token=None):
    """Push the JSON metrics to Hollow"""
    logger.info(f"Pushing metrics to Hollow: {dataset_name}")

    try:
        cmd = [
            "python3", "ebpf_to_hollow.py",
            json_file,
            "-p", producer_url,
            "-d", dataset_name
        ]

        if auth_token:
            cmd.extend(["-t", auth_token])

        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        logger.info("Successfully pushed metrics to Hollow")
        logger.debug(result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to push to Hollow: {e.stderr}")
        return False

    except Exception as e:
        logger.error(f"Error pushing to Hollow: {e}")
        return False

def monitoring_loop(args):
    """Main monitoring loop"""
    global exiting

    iteration = 1

    while not exiting:
        logger.info(f"Starting monitoring iteration {iteration}")

        # Create timestamp for this iteration
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create temporary directory for this iteration if output_dir not specified
        if args.output_dir:
            output_dir = args.output_dir
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = tempfile.mkdtemp(prefix=f"ebpf_metrics_{timestamp}_")

        # Define file paths
        metrics_file = os.path.join(output_dir, f"metrics_{timestamp}.txt")
        json_file = os.path.join(output_dir, f"metrics_{timestamp}.json")

        # Run metrics collection
        if not run_metrics_collection(args.collection_interval, metrics_file, args):
            logger.error("Metrics collection failed. Continuing to next iteration.")
            time.sleep(args.retry_interval)
            iteration += 1
            continue

        # Convert to JSON
        if not convert_to_json(metrics_file, json_file):
            logger.error("JSON conversion failed. Continuing to next iteration.")
            time.sleep(args.retry_interval)
            iteration += 1
            continue

        # Push to Hollow
        if not push_to_hollow(json_file, args.producer_url, args.dataset_name, args.auth_token):
            logger.error("Failed to push to Hollow. Continuing to next iteration.")

        # Clean up temporary files if requested
        if args.cleanup and not args.output_dir:
            try:
                os.remove(metrics_file)
                os.remove(json_file)
                os.rmdir(output_dir)
                logger.info("Cleaned up temporary files")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary files: {e}")

        # Wait for the next iteration
        logger.info(f"Completed iteration {iteration}. Waiting for next cycle.")

        # Sleep until next collection cycle
        next_iteration_wait = max(0, args.collection_interval - args.retry_interval)

        for _ in range(int(next_iteration_wait)):
            if exiting:
                break
            time.sleep(1)

        iteration += 1

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Continuously monitor eBPF metrics and push to Netflix Hollow')

    parser.add_argument('-p', '--producer-url', required=True,
                       help='URL of the Hollow producer API')
    parser.add_argument('-d', '--dataset-name', default='ebpf_metrics',
                       help='Name of the dataset in Hollow (default: ebpf_metrics)')
    parser.add_argument('-t', '--auth-token',
                       help='Authentication token for the Hollow producer API')
    parser.add_argument('-i', '--collection-interval', type=int, default=60,
                       help='Time interval between metrics collections in seconds (default: 60)')
    parser.add_argument('-r', '--retry-interval', type=int, default=10,
                       help='Time to wait before retrying after a failure (default: 10)')
    parser.add_argument('-o', '--output-dir',
                       help='Directory to save metrics files (default: temporary directory)')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up temporary files after pushing to Hollow')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--no-fallback', action='store_true',
                       help='Disable fallback to sample metrics when collection fails')

    args = parser.parse_args()

    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting eBPF to Hollow integration")
    logger.info(f"Producer URL: {args.producer_url}")
    logger.info(f"Dataset Name: {args.dataset_name}")
    logger.info(f"Collection Interval: {args.collection_interval} seconds")

    try:
        # Start the monitoring loop
        monitoring_loop(args)
    except Exception as e:
        logger.error(f"Unexpected error in monitoring loop: {e}", exc_info=True)
        return 1

    logger.info("eBPF to Hollow integration complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())

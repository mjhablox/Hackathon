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
import threading
import http.server
import socketserver
import webbrowser
from pathlib import Path

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
# Global HTTP server reference
http_server = None

def signal_handler(sig, frame):
    """Handle termination signals"""
    global exiting, http_server
    logger.info("Received termination signal. Shutting down...")
    exiting = True
    # Stop HTTP server if running
    if http_server:
        logger.info("Stopping dashboard server...")
        http_server.shutdown()

def run_metrics_collection(duration, output_file, args=None):
    """Run the eBPF metrics collection for the specified duration"""
    logger.info(f"Starting eBPF metrics collection for {duration} seconds")

    # First, try to run the eBPF metrics collection
    try:
        # Use parent directory for kea_metrics.py
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        kea_metrics_path = os.path.join(parent_dir, "kea_metrics.py")

        # Check if kea_metrics.py exists
        if not os.path.exists(kea_metrics_path):
            raise FileNotFoundError(f"Metrics collection script not found at: {kea_metrics_path}")

        # Run the kea_metrics.py script with a timeout
        # Need to run from the parent directory so kea_metrics.py can find kea_metrics.c
        process = subprocess.Popen(
            ["sudo", "python3", kea_metrics_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=parent_dir  # Set working directory to parent_dir where kea_metrics.c exists
        )

        # Wait for the specified duration
        time.sleep(duration)

        # Send SIGINT to stop the metrics collection gracefully
        process.send_signal(signal.SIGINT)

        # Capture the output with a timeout
        stdout, stderr = process.communicate(timeout=10)

        if not stdout.strip():
            raise ValueError("No metrics data collected (empty output)")

        # Write the output to the specified file
        with open(output_file, 'w') as f:
            f.write(stdout)

        logger.info(f"Metrics collection completed and saved to {output_file}")
        return True

    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
        logger.warning(f"Metrics collection issue: {e}")
        if 'process' in locals() and process.poll() is None:
            process.kill()
            process.communicate()

        # Check if fallback is disabled
        if args and hasattr(args, 'no_fallback') and args.no_fallback:
            logger.warning("Fallback to sample metrics is disabled. Skipping metrics collection.")
            return False

        # Fall back to using the sample metrics file
        logger.info("Using sample metrics data instead")
        try:
            # Path to sample metrics file in the same directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            sample_metrics_path = os.path.join(script_dir, "test_metrics.json")

            # If the sample file exists and is a JSON file, use it directly
            if os.path.exists(sample_metrics_path) and sample_metrics_path.endswith('.json'):
                import shutil
                shutil.copy2(sample_metrics_path, output_file)
                logger.info(f"Copied sample JSON metrics to {output_file}")
                return True

            # Otherwise check in parent directory
            sample_metrics_path = os.path.join(parent_dir, "sample_metrics.txt")
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
        if 'process' in locals() and process.poll() is None:
            process.kill()
        return False

def convert_to_json(metrics_file, json_file):
    """Convert the metrics file to JSON format"""
    logger.info(f"Converting metrics to JSON format: {json_file}")

    try:
        # Check if the input file is already in JSON format
        if metrics_file.endswith('.json'):
            try:
                # Try to load the file as JSON to verify
                with open(metrics_file, 'r') as f:
                    json.load(f)

                # If successful, simply copy the file
                import shutil
                shutil.copy2(metrics_file, json_file)
                logger.info(f"Input file is already in JSON format, copied to {json_file}")
                return True
            except json.JSONDecodeError:
                logger.warning(f"File has .json extension but is not valid JSON: {metrics_file}")
                # Continue with conversion

        # Regular conversion using ebpf_to_json.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ebpf_to_json_path = os.path.join(script_dir, "ebpf_to_json.py")

        result = subprocess.run(
            ["python3", ebpf_to_json_path, metrics_file, "-o", json_file],
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

def push_to_hollow(json_file, producer_url, dataset_name, auth_token=None, local_mode=False):
    """Push the JSON metrics to Hollow"""
    if local_mode:
        logger.info(f"Using local Hollow setup for dataset: {dataset_name}")
    else:
        if not producer_url:
            logger.error("No producer URL specified and not in local mode")
            return False
        logger.info(f"Pushing metrics to remote Hollow at {producer_url}: {dataset_name}")

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ebpf_to_hollow_path = os.path.join(script_dir, "ebpf_to_hollow.py")

        # Base command
        cmd = ["python3", ebpf_to_hollow_path, json_file]

        if local_mode:
            cmd.append("--local")
        else:
            cmd.extend(["-p", producer_url])

        cmd.extend(["-d", dataset_name])

        if auth_token:
            cmd.extend(["-t", auth_token])

        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if local_mode:
            logger.info("Successfully prepared metrics for local Hollow")
        else:
            logger.info("Successfully pushed metrics to Hollow")

        logger.debug(result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        if local_mode:
            logger.error(f"Failed to prepare metrics for local Hollow: {e.stderr}")
        else:
            logger.error(f"Failed to push to remote Hollow: {e.stderr}")
        return False

    except Exception as e:
        logger.error(f"Error pushing to Hollow: {e}")
        return False

def visualize_metrics(json_file, visualization_dir):
    """Create visualizations from the JSON metrics file"""
    logger.info(f"Creating visualizations from {json_file}")

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        visualize_script = os.path.join(script_dir, "visualize_json_metrics.py")

        # Ensure the visualization directory exists
        os.makedirs(visualization_dir, exist_ok=True)

        # Verify the JSON file exists and has content
        if not os.path.exists(json_file):
            raise FileNotFoundError(f"JSON file not found: {json_file}")

        # Verify JSON file has valid content
        try:
            with open(json_file, 'r') as f:
                metrics_data = json.load(f)
                if 'metrics' not in metrics_data or not metrics_data['metrics']:
                    logger.warning(f"JSON file has no metrics data: {json_file}")
        except Exception as e:
            logger.warning(f"Error validating JSON file: {e}")

        # Call the visualization script
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.debug(f"Running visualization script: {visualize_script} {json_file} --output-dir {visualization_dir} --create-latest")

        result = subprocess.run(
            ["python3", visualize_script, json_file, "--output-dir", visualization_dir, "--create-latest", "-v"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Log the visualization output for debugging
        logger.debug(f"Visualization script output: {result.stdout}")
        if result.stderr:
            logger.warning(f"Visualization script warnings/errors: {result.stderr}")

        # Create/update symbolic links to the latest visualizations for the dashboard
        update_dashboard_visualizations(visualization_dir, timestamp)

        logger.info(f"Successfully created visualizations in {visualization_dir}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Visualization failed: {e.stderr}")
        return False

    except Exception as e:
        logger.error(f"Error during visualization: {e}")
        return False

def update_dashboard_visualizations(visualization_dir, timestamp):
    """Update symbolic links to the latest visualizations for the dashboard"""
    try:
        # Define the visualization types we expect
        viz_types = [
            "summary", "aggregates", "cpu_usage", "memory_usage",
            "network_traffic", "error_rates", "packet_processing_time",
            "packet_drop_rate", "lease_allocation_time", "database_query_performance"
        ]

        updated_count = 0

        # For each visualization type, create/update a symbolic link to the latest file
        for viz_type in viz_types:
            # Find the latest file for this visualization type
            latest_file = f"{viz_type}_{timestamp}.png"
            latest_path = os.path.join(visualization_dir, latest_file)

            # Check if the file exists
            if os.path.exists(latest_path):
                # Create a symlink or copy the file for dashboard
                dashboard_file = os.path.join(visualization_dir, f"{viz_type}_latest.png")

                # Remove existing link/file if it exists
                if os.path.exists(dashboard_file):
                    os.remove(dashboard_file)

                # Create a copy (more compatible than symlinks in some environments)
                import shutil
                shutil.copy2(latest_path, dashboard_file)

                # Add a timestamp to force browser cache refresh
                with open(dashboard_file, 'ab') as f:
                    # Append a comment with timestamp that doesn't affect the image
                    f.write(f"\n<!-- Updated: {timestamp} -->".encode('utf-8'))

                updated_count += 1
                logger.debug(f"Updated dashboard visualization: {viz_type}_latest.png")

        if updated_count > 0:
            logger.info(f"Updated {updated_count} dashboard visualizations with data from {timestamp}")

    except Exception as e:
        logger.warning(f"Failed to update dashboard visualizations: {e}")

def create_dashboard_index(visualization_dir):
    """Create a simple HTML dashboard that auto-refreshes"""
    index_path = os.path.join(visualization_dir, "index.html")

    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>eBPF Metrics Dashboard</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; }
        h1 { color: #333; }
        .dashboard { display: flex; flex-wrap: wrap; }
        .chart { margin: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); background-color: white; padding: 15px; }
        .chart img { width: 100%; height: auto; }
        .loading-placeholder {
            width: 100%;
            height: 200px;
            background-color: #e9e9e9;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-style: italic;
        }
        .status-message {
            padding: 8px;
            margin-bottom: 10px;
            background-color: #fffde7;
            border-left: 4px solid #ffd600;
        }
    </style>
</head>
<body>
    <h1>eBPF Metrics Real-time Dashboard</h1>
    <div class="status-message">
        <p>Auto-refreshes every 10 seconds. Last update: <span id="timestamp"></span></p>
        <p id="data-status">Waiting for initial data collection...</p>
    </div>

    <div class="dashboard">
        <div class="chart">
            <h3>Summary</h3>
            <div id="summary-container">
                <div class="loading-placeholder">Waiting for data...</div>
            </div>
        </div>
        <div class="chart">
            <h3>Aggregates</h3>
            <div id="aggregates-container">
                <div class="loading-placeholder">Waiting for data...</div>
            </div>
        </div>
        <div class="chart">
            <h3>CPU Usage</h3>
            <div id="cpu-usage-container">
                <div class="loading-placeholder">Waiting for data...</div>
            </div>
        </div>
        <div class="chart">
            <h3>Memory Usage</h3>
            <div id="memory-usage-container">
                <div class="loading-placeholder">Waiting for data...</div>
            </div>
        </div>
        <div class="chart">
            <h3>Network Traffic</h3>
            <div id="network-traffic-container">
                <div class="loading-placeholder">Waiting for data...</div>
            </div>
        </div>
        <div class="chart">
            <h3>Error Rates</h3>
            <div id="error-rates-container">
                <div class="loading-placeholder">Waiting for data...</div>
            </div>
        </div>
        <div class="chart">
            <h3>Packet Processing Time</h3>
            <div id="packet-processing-time-container">
                <div class="loading-placeholder">Waiting for data...</div>
            </div>
        </div>
        <div class="chart">
            <h3>Packet Drop Rate</h3>
            <div id="packet-drop-rate-container">
                <div class="loading-placeholder">Waiting for data...</div>
            </div>
        </div>
        <div class="chart">
            <h3>Lease Allocation Time</h3>
            <div id="lease-allocation-time-container">
                <div class="loading-placeholder">Waiting for data...</div>
            </div>
        </div>
        <div class="chart">
            <h3>Database Query Performance</h3>
            <div id="database-query-performance-container">
                <div class="loading-placeholder">Waiting for data...</div>
            </div>
        </div>
    </div>

    <script>
        // Update timestamp
        document.getElementById('timestamp').innerText = new Date().toLocaleString();
        setInterval(function() {
            document.getElementById('timestamp').innerText = new Date().toLocaleString();
        }, 1000);

        // Chart data
        const charts = [
            {id: 'summary-container', src: 'summary_latest.png', alt: 'Summary Metrics'},
            {id: 'aggregates-container', src: 'aggregates_latest.png', alt: 'Aggregate Metrics'},
            {id: 'cpu-usage-container', src: 'cpu_usage_latest.png', alt: 'CPU Usage'},
            {id: 'memory-usage-container', src: 'memory_usage_latest.png', alt: 'Memory Usage'},
            {id: 'network-traffic-container', src: 'network_traffic_latest.png', alt: 'Network Traffic'},
            {id: 'error-rates-container', src: 'error_rates_latest.png', alt: 'Error Rates'},
            {id: 'packet-processing-time-container', src: 'packet_processing_time_latest.png', alt: 'Packet Processing Time'},
            {id: 'packet-drop-rate-container', src: 'packet_drop_rate_latest.png', alt: 'Packet Drop Rate'},
            {id: 'lease-allocation-time-container', src: 'lease_allocation_time_latest.png', alt: 'Lease Allocation Time'},
            {id: 'database-query-performance-container', src: 'database_query_performance_latest.png', alt: 'Database Query Performance'}
        ];

        // Check image availability and load them
        function loadImages() {
            let availableImages = 0;

            charts.forEach(chart => {
                const container = document.getElementById(chart.id);
                const img = new Image();

                img.onload = function() {
                    container.innerHTML = '';
                    container.appendChild(this);
                    availableImages++;

                    if (availableImages > 0) {
                        document.getElementById('data-status').textContent =
                            `Data collection active: ${availableImages} of ${charts.length} visualizations available`;
                    }
                };

                img.onerror = function() {
                    // Keep the placeholder if image fails to load
                    if (container.querySelector('.loading-placeholder')) {
                        // Already has placeholder, do nothing
                    } else {
                        container.innerHTML = '<div class="loading-placeholder">Waiting for data...</div>';
                    }
                };

                // Add cache-busting parameter to force reload
                const cacheBuster = new Date().getTime();
                img.src = chart.src + '?t=' + cacheBuster;
                img.alt = chart.alt;
                img.style = 'width: 100%; height: auto;';
            });
        }

        // Initial load
        loadImages();

        // Reload images every few seconds
        setInterval(loadImages, 10000);
    </script>
</body>
</html>
"""

    with open(index_path, "w") as f:
        f.write(html_content)

    return index_path

def create_placeholder_images(visualization_dir):
    """Create placeholder images for the dashboard until real data is available"""
    logger.info(f"Creating placeholder images in {visualization_dir}")

    # Create a directory for visualizations if it doesn't exist
    os.makedirs(visualization_dir, exist_ok=True)

    # Define the visualization types
    viz_types = [
        "summary", "aggregates", "cpu_usage", "memory_usage",
        "network_traffic", "error_rates", "packet_processing_time",
        "packet_drop_rate", "lease_allocation_time", "database_query_performance"
    ]

    created_count = 0

    # Try using PIL/Pillow for better looking placeholders
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Create a basic placeholder image for each type
        for viz_type in viz_types:
            placeholder_file = os.path.join(visualization_dir, f"{viz_type}_latest.png")

            # Skip if the file already exists
            if os.path.exists(placeholder_file):
                logger.debug(f"Placeholder already exists: {placeholder_file}")
                continue

            # Create a simple placeholder image
            img = Image.new('RGB', (800, 400), color=(233, 233, 233))
            d = ImageDraw.Draw(img)

            # Draw text on the image - use a simpler method that works across PIL versions
            message = f"Waiting for {viz_type.replace('_', ' ')} data..."

            try:
                # Try to use a font if available
                try:
                    # Try a common font that should be available on most systems
                    font = ImageFont.truetype("Arial", 20)
                except:
                    # Fallback to default font
                    font = ImageFont.load_default()

                # Get text size - compatibility with different PIL versions
                try:
                    # For newer PIL versions
                    bbox = d.textbbox((0, 0), message, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                except AttributeError:
                    try:
                        # For older PIL versions
                        text_width, text_height = d.textsize(message, font=font)
                    except AttributeError:
                        # Fallback to approximate size
                        text_width, text_height = len(message) * 10, 20

                # Position text in center
                position = ((800 - text_width) // 2, (400 - text_height) // 2)
                d.text(position, message, fill=(100, 100, 100), font=font)

            except Exception as font_error:
                # If font handling fails, use simpler text placement
                logger.debug(f"Font handling error: {font_error}, using simple text placement")
                d.text((50, 180), message, fill=(100, 100, 100))

            # Save the placeholder image
            img.save(placeholder_file)
            created_count += 1
            logger.info(f"Created placeholder image: {placeholder_file}")

    except ImportError:
        logger.warning("PIL not installed, creating simple placeholder files")

        # Fallback to create empty files if PIL is not available
        for viz_type in viz_types:
            placeholder_file = os.path.join(visualization_dir, f"{viz_type}_latest.png")

            # Skip if the file already exists
            if os.path.exists(placeholder_file):
                continue

            # Create an empty file as placeholder
            try:
                # Write a simple 1x1 pixel PNG file (minimal valid PNG)
                with open(placeholder_file, 'wb') as f:
                    # Minimal valid PNG file (1x1 pixel, transparent)
                    png_data = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63fcffff3f000005fc01c5214089580000000049454e44ae426082')
                    f.write(png_data)
                created_count += 1
                logger.info(f"Created simple placeholder: {placeholder_file}")
            except Exception as e:
                logger.warning(f"Failed to create placeholder file {placeholder_file}: {e}")

    except Exception as e:
        logger.warning(f"Error creating placeholder images: {e}")

    return created_count > 0

def start_dashboard_server(visualization_dir, port=8000, open_browser=True):
    """Start a HTTP server to serve the dashboard"""
    global http_server

    # If the server is already running, just refresh the dashboard
    if http_server:
        logger.info("Dashboard server already running, refreshing content")
        # Create dashboard HTML file to ensure it's up to date
        dashboard_path = create_dashboard_index(visualization_dir)
        # Open browser again if requested
        if open_browser:
            webbrowser.open(f"http://localhost:{port}/")
        return True

    # Create visualization directory if it doesn't exist
    os.makedirs(visualization_dir, exist_ok=True)

    # Store the current directory to restore it later
    original_dir = os.getcwd()

    try:
        # Check if the port is already in use
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()

        if result == 0:
            # Port is already in use
            logger.warning(f"Port {port} is already in use, assuming dashboard is running")
            # Create dashboard HTML file to ensure it's up to date
            dashboard_path = create_dashboard_index(visualization_dir)
            # Create placeholder images
            create_placeholder_images(visualization_dir)
            # Open browser again if requested
            if open_browser:
                webbrowser.open(f"http://localhost:{port}/")
            return True

        # Create placeholder images before creating the dashboard index
        # This ensures the placeholders are created first
        placeholders_created = create_placeholder_images(visualization_dir)

        if not placeholders_created:
            logger.warning("Failed to create placeholder images, dashboard may show errors initially")

        # Create dashboard HTML file
        dashboard_path = create_dashboard_index(visualization_dir)

        # Set the directory containing the visualization
        os.chdir(visualization_dir)

        # Create a simple HTTP server
        handler = http.server.SimpleHTTPRequestHandler

        # Custom handler to prevent logging all requests (reduces console clutter)
        # and handle 404 errors gracefully
        class QuietHandler(handler):
            def log_message(self, format, *args):
                # Override to only log errors, not all requests
                if len(args) > 1 and (args[1].startswith('4') or args[1].startswith('5')):
                    # Log at debug level to avoid cluttering with 404s for images not yet created
                    if args[1] == '404':
                        logger.debug(f"Dashboard HTTP 404: {args[0]} - resource not yet available")
                    else:
                        logger.warning(f"Dashboard HTTP error: {args[0]} {args[1]}")

            def send_error(self, code, message=None, explain=None):
                # Override to provide better handling for 404 errors
                if code == 404 and self.path.endswith('.png'):
                    # For image files, send a transparent placeholder instead of 404
                    try:
                        self.send_response(200)
                        self.send_header('Content-type', 'image/png')
                        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                        self.send_header('Pragma', 'no-cache')
                        self.send_header('Expires', '0')
                        self.end_headers()

                        # Minimal valid PNG file (1x1 pixel, transparent)
                        png_data = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63fcffff3f000005fc01c5214089580000000049454e44ae426082')
                        self.wfile.write(png_data)
                        return
                    except Exception:
                        # Fall back to standard error if our override fails
                        pass

                # Use the standard error handling for other cases
                super().send_error(code, message, explain)

        class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True

        # Start HTTP server
        http_server = ThreadedHTTPServer(("", port), QuietHandler)

        # Start HTTP server in a separate thread
        server_thread = threading.Thread(target=http_server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        logger.info(f"Dashboard server started at http://localhost:{port}/")

        # Open the dashboard in a web browser if requested
        if open_browser:
            logger.info("Opening dashboard in web browser...")
            webbrowser.open(f"http://localhost:{port}/")

        return True

    except Exception as e:
        logger.error(f"Failed to start dashboard server: {e}")
        # Restore original directory if we changed it
        if os.getcwd() != original_dir:
            os.chdir(original_dir)
        return False

def monitoring_loop(args):
    """Main monitoring loop"""
    global exiting

    iteration = 1
    visualization_dir = args.viz_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "visualizations")

    # Create visualization directory if it doesn't exist
    os.makedirs(visualization_dir, exist_ok=True)

    # Initialize dashboard with placeholders before starting collection if requested
    dashboard_initialized = False
    if args.dashboard and args.dashboard_preload:
        logger.info("Pre-initializing dashboard with placeholders...")
        start_dashboard_server(visualization_dir, args.dashboard_port)
        dashboard_initialized = True

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

        # Create visualizations in real-time if requested
        if args.visualize:
            visualize_metrics(json_file, visualization_dir)

            # Start the dashboard after first visualizations are created
            if args.dashboard and not dashboard_initialized:
                start_dashboard_server(visualization_dir, args.dashboard_port)
                dashboard_initialized = True

        # Push to Hollow
        if not push_to_hollow(json_file, args.producer_url, args.dataset_name, args.auth_token, args.local):
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

    parser.add_argument('-p', '--producer-url',
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
    parser.add_argument('--local', action='store_true',
                       help='Use local Hollow setup instead of remote producer API')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')
    # Visualization options
    parser.add_argument('--visualize', action='store_true',
                       help='Create visualizations in real-time')
    parser.add_argument('--dashboard', action='store_true',
                       help='Enable real-time dashboard visualization')
    parser.add_argument('--dashboard-port', type=int, default=8000,
                       help='Port for the dashboard server (default: 8000)')
    parser.add_argument('--dashboard-preload', action='store_true',
                       help='Preload dashboard with placeholders before first data collection')
    parser.add_argument('--viz-dir',
                       help='Directory to save visualizations (default: visualizations)')
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

# eBPF Metrics Real-Time Dashboard

This dashboard provides real-time visualization of eBPF metrics collected from the Netflix Hollow integration. It automatically updates as new metrics are collected.

## Features

- Real-time visualization of eBPF metrics
- Auto-refreshing dashboard with latest data
- Support for multiple metric types and visualizations
- Error-resilient display that handles missing data gracefully

## Running the Dashboard

To start the dashboard, use the provided script:

```bash
./run_realtime_dashboard.sh
```

This will:

1. Start the eBPF metrics collection
2. Create a web-based dashboard at http://localhost:8080/
3. Open the dashboard in your default web browser
4. Automatically update visualizations as new data is collected

## Dashboard Usage

The dashboard shows visualizations for the following metrics:

- Summary of all metrics
- Aggregated metrics
- CPU usage
- Memory usage
- Network traffic
- Error rates
- Packet processing time
- Packet drop rate
- Lease allocation time
- Database query performance

The dashboard auto-refreshes every 10 seconds and shows a timestamp of when it was last updated.

## Advanced Configuration

You can run the monitoring script directly with custom options:

```bash
python ebpf_hollow_monitor.py \
    --producer-url "http://localhost:7001" \
    --dataset-name "my_ebpf_metrics" \
    --collection-interval 60 \
    --visualize \
    --dashboard \
    --dashboard-preload \
    --dashboard-port 8080 \
    --viz-dir "./my_visualizations" \
    -v
```

### Key Options:

- `--visualize`: Create visualizations from metrics
- `--dashboard`: Enable the web dashboard
- `--dashboard-preload`: Start dashboard immediately with placeholders
- `--dashboard-port`: Specify HTTP port for the dashboard
- `--viz-dir`: Directory to save visualizations
- `--collection-interval`: Time between metrics collections (seconds)

## Troubleshooting

If the dashboard doesn't display metrics:

1. Ensure the monitoring script is running correctly
2. Check that the dashboard server started successfully
3. Wait for at least one complete metrics collection cycle
4. Verify that the visualizations directory exists and is writable
5. Check for any error messages in the console output

## Dependencies

- Python 3.6+
- PIL/Pillow (optional, for better placeholder images)
- Matplotlib (for creating visualizations)
- A modern web browser

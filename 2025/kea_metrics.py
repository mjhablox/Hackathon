#!/usr/bin/env python3
# filepath: /home/parallels/Work/Tutorials/Hackathon/2025/kea_metrics.py

from bcc import BPF
import time
import signal
import sys

# Read the BPF program
with open('kea_metrics.c', 'r') as f:
    bpf_text = f.read()

# Define the path to the Kea DHCP binary
kea_binary = "/home/parallels/Work/Blox/UDDI/ddi.vendor.kea/kea/install_area/sbin/kea-dhcp4"

# Initialize BPF
try:
    b = BPF(text=bpf_text)
    print("BPF program loaded successfully")
except Exception as e:
    print(f"Failed to load BPF program: {e}")
    sys.exit(1)

# Define the Kea DHCP functions to trace using addresses from key_functions_output.txt
kea_functions = {
    # Packet processing time - only using entry probe since return probe fails
    "0x0000000000076590": ["trace_start"],

    # Packet drop tracking
    "0x0000000000084ba8": ["trace_packet_drop"],

    # CPU usage
    "0x0000000000076278": ["trace_cpu_usage"],

    # Memory usage
    "0x0000000000051a78": ["trace_memory_usage"],

    # Network traffic
    "0x0000000000075e30": ["trace_network_traffic"],  # isc::dhcp::Option::getData() const

    # Error rates
    "0x0000000000051480": ["trace_error_rates"],  # isc::dhcp::DhcpConfigError::~DhcpConfigError()

    # Lease allocation time - only using entry probe since return probe fails
    "0x0000000000076698": ["trace_lease_allocation"],

    # Database query performance - only using entry probe since return probe fails
    "0x0000000000051600": ["trace_database_query"]  # isc::dhcp::SrvConfig::addConfiguredGlobal
}

# Attach uprobes
attached_count = 0
for func_addr, trace_funcs in kea_functions.items():
    try:
        # Convert hex address string to integer
        addr = int(func_addr, 16)

        if "trace_start" in trace_funcs:
            b.attach_uprobe(name=kea_binary, addr=addr, fn_name="trace_start")
            print(f"✓ Attached trace_start to address {func_addr}")
            attached_count += 1

        if "trace_end" in trace_funcs:
            b.attach_uretprobe(name=kea_binary, addr=addr, fn_name="trace_end")
            print(f"✓ Attached trace_end to address {func_addr}")
            attached_count += 1

        if "trace_packet_drop" in trace_funcs:
            b.attach_uprobe(name=kea_binary, addr=addr, fn_name="trace_packet_drop")
            print(f"✓ Attached trace_packet_drop to address {func_addr}")
            attached_count += 1

        if "trace_cpu_usage" in trace_funcs:
            b.attach_uprobe(name=kea_binary, addr=addr, fn_name="trace_cpu_usage")
            print(f"✓ Attached trace_cpu_usage to address {func_addr}")
            attached_count += 1

        if "trace_memory_usage" in trace_funcs:
            b.attach_uprobe(name=kea_binary, addr=addr, fn_name="trace_memory_usage")
            print(f"✓ Attached trace_memory_usage to address {func_addr}")
            attached_count += 1

        if "trace_network_traffic" in trace_funcs:
            b.attach_uprobe(name=kea_binary, addr=addr, fn_name="trace_network_traffic")
            print(f"✓ Attached trace_network_traffic to address {func_addr}")
            attached_count += 1

        if "trace_error_rates" in trace_funcs:
            b.attach_uprobe(name=kea_binary, addr=addr, fn_name="trace_error_rates")
            print(f"✓ Attached trace_error_rates to address {func_addr}")
            attached_count += 1

        if "trace_lease_allocation" in trace_funcs:
            b.attach_uprobe(name=kea_binary, addr=addr, fn_name="trace_lease_allocation")
            print(f"✓ Attached trace_lease_allocation to address {func_addr}")
            attached_count += 1

        if "trace_lease_allocation_end" in trace_funcs:
            b.attach_uretprobe(name=kea_binary, addr=addr, fn_name="trace_lease_allocation_end")
            print(f"✓ Attached trace_lease_allocation_end to address {func_addr}")
            attached_count += 1

        if "trace_database_query" in trace_funcs:
            b.attach_uprobe(name=kea_binary, addr=addr, fn_name="trace_database_query")
            print(f"✓ Attached trace_database_query to address {func_addr}")
            attached_count += 1

        if "trace_database_query_end" in trace_funcs:
            b.attach_uretprobe(name=kea_binary, addr=addr, fn_name="trace_database_query_end")
            print(f"✓ Attached trace_database_query_end to address {func_addr}")
            attached_count += 1

    except Exception as e:
        print(f"✗ Failed to attach probe to address {func_addr}: {e}")

if attached_count == 0:
    print("\nWarning: No probes were successfully attached.")
    print("Check that the addresses exist in the binary and try again.")
    sys.exit(1)
else:
    print(f"\nSuccessfully attached {attached_count} probes.")

# Global flag to prevent reentrant calls
exiting = False

# Signal handler for graceful exit
def signal_handler(sig, frame):
    global exiting
    if exiting:
        return
    exiting = True

    print("\nExiting...")
    print("\nMetrics Summary:")

    # Safely print histograms
    for name, hist_type in [
        ("packet_processing_time", "time (ns)"),
        ("packet_drop_rate", "count"),
        ("cpu_usage", "cpu"),
        ("memory_usage", "bytes"),
        ("network_traffic", "packets"),
        ("error_rates", "errors"),
        ("lease_allocation_time", "time (ns)"),
        ("database_query_performance", "time (ns)")
    ]:
        try:
            table = b.get_table(name)
            print(f"\n{name.replace('_', ' ').title()}:")
            table.print_log2_hist(hist_type)
        except Exception as e:
            print(f"\n{name.replace('_', ' ').title()}: No data collected or error occurred")

    # Print counts for non-empty tables
    print("\n\nAggregate Counts:")
    for name in [
        "packet_drop_rate",
        "cpu_usage",
        "memory_usage",
        "network_traffic",
        "error_rates"
    ]:
        try:
            table = b.get_table(name)
            count = sum(v.value for v in table.values())
            print(f"{name.replace('_', ' ').title()}: {count}")
        except Exception as e:
            pass

    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print("\nTracing Kea DHCP server... Press Ctrl+C to exit")
print("(Note: You may need to generate DHCP traffic to see results)")

# Keep the program running until interrupted
while not exiting:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"Error in main loop: {e}")
        break

# Final cleanup
print("Monitoring complete. Exiting...")
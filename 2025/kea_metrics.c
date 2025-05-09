#include <uapi/linux/ptrace.h>
#include <linux/sched.h>
#include <net/sock.h>
#include <bcc/proto.h>

BPF_HASH(start, u32);
BPF_HISTOGRAM(packet_processing_time);
BPF_HISTOGRAM(packet_drop_rate);
BPF_HISTOGRAM(cpu_usage);
BPF_HISTOGRAM(memory_usage);
BPF_HISTOGRAM(network_traffic);
BPF_HISTOGRAM(error_rates);
BPF_HISTOGRAM(lease_allocation_time);
BPF_HISTOGRAM(database_query_performance);

int trace_start(struct pt_regs *ctx, struct sock *sk) {
    u32 pid = bpf_get_current_pid_tgid();
    u64 ts = bpf_ktime_get_ns();
    start.update(&pid, &ts);
    return 0;
}

int trace_end(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid();
    u64 *tsp = start.lookup(&pid);
    if (tsp != 0) {
        u64 delta = bpf_ktime_get_ns() - *tsp;
        packet_processing_time.increment(bpf_log2l(delta));
        start.delete(&pid);
    }
    return 0;
}

int trace_packet_drop(struct pt_regs *ctx) {
    packet_drop_rate.increment(1);
    return 0;
}

int trace_cpu_usage(struct pt_regs *ctx) {
    // Using proper helper function
    int cpu = bpf_get_smp_processor_id();
    cpu_usage.increment(cpu);
    return 0;
}

int trace_memory_usage(struct pt_regs *ctx) {
    // Simplified memory tracking since task->mm->total_vm access is complicated in BPF
    memory_usage.increment(1);
    return 0;
}

int trace_network_traffic(struct pt_regs *ctx, struct sock *sk) {
    // Using a simpler approach to track network traffic
    // as atomic_t is not directly accessible
    network_traffic.increment(1);
    return 0;
}

int trace_error_rates(struct pt_regs *ctx) {
    error_rates.increment(1);
    return 0;
}

int trace_lease_allocation(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid();
    u64 ts = bpf_ktime_get_ns();
    start.update(&pid, &ts);
    return 0;
}

int trace_lease_allocation_end(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid();
    u64 *tsp = start.lookup(&pid);
    if (tsp != 0) {
        u64 delta = bpf_ktime_get_ns() - *tsp;
        lease_allocation_time.increment(bpf_log2l(delta));
        start.delete(&pid);
    }
    return 0;
}

int trace_database_query(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid();
    u64 ts = bpf_ktime_get_ns();
    start.update(&pid, &ts);
    return 0;
}

int trace_database_query_end(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid();
    u64 *tsp = start.lookup(&pid);
    if (tsp != 0) {
        u64 delta = bpf_ktime_get_ns() - *tsp;
        database_query_performance.increment(bpf_log2l(delta));
        start.delete(&pid);
    }
    return 0;
}
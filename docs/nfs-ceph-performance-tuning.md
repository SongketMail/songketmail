---
okf_version: 0.1
type: research
title: "NFS v4.2 and Ceph RBD Performance Tuning Guide"
description: "A comprehensive performance tuning guide for NFS v4.2 server/client stacks and Ceph RBD burst IOPS benchmarking using fio against NVMe pools on Proxmox VE nodes."
resource: "file:///docs/nfs-ceph-performance-tuning.md"
timestamp: 2026-09-05T12:00:00Z
topics: [nfs, ceph, rbd, fio, performance, tuning, nvme, proxmox, songketmail]
---
# 🚀 NFS v4.2 & Ceph RBD Performance Tuning Guide

This guide provides an enterprise-grade performance tuning specification for NFS v4.2 server/client configurations and Ceph RADOS Block Device (RBD) burst IOPS benchmarking against NVMe pools on Proxmox VE hypervisor nodes.

---

## ⚡ Executive Summary & Architecture Overview

High-throughput email servers, container orchestrators, and database workloads demand low latency and high concurrent IOPS. Optimizing Linux storage stacks requires a multi-layered approach:
1. **NFS v4.2 Protocol Tuning**: Utilizing modern kernel capabilities such as `nconnect` TCP stream multiplexing, 1MB block transfers (`rsize=1048576,wsize=1048576`), and elevated Sun RPC slot capacity (`sunrpc.tcp_slot_table_entries=128`).
2. **Ceph RBD NVMe Pool Optimization**: Leveraging direct `librbd` or `ioengine=libaio` with `fio` benchmarking to measure 4K burst IOPS and 1M sequential throughput across Proxmox VE storage clusters.
3. **Client-Side FS-Cache Integration**: Utilizing `cachefilesd` under modern Linux Kernel 5.17+ re-architected caching layers to eliminate network round-trips for read-heavy operations.

---

## 🖥️ 1. NFS Server & Client Sysctl Kernel Tuning

To eliminate network socket buffering bottlenecks and maximize concurrent Remote Procedure Call (RPC) request capacity, apply the following sysctl parameters across NFS Server and Client nodes.

### A. `/etc/sysctl.conf` Configuration for NFS Servers & Clients

Edit `/etc/sysctl.conf` or create `/etc/sysctl.d/99-nfs-performance.conf`:

```ini
# --- Memory & I/O Optimizations ---
vm.max_map_count = 262144
vm.overcommit_memory = 1
vm.swappiness = 10
# Set dirty bytes limits to prevent large I/O stalls (600MB max dirty, 300MB background write-back)
vm.dirty_bytes = 629145600
vm.dirty_background_bytes = 314572800
# Elevate VFS cache pressure for rapid inode/dentry recycling
vm.vfs_cache_pressure = 200
fs.file-max = 65536000
fs.inotify.max_user_watches = 500000
fs.aio-max-nr = 1000000

# --- TCP/IP Network Stack Optimizations ---
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_notsent_lowat = 16384
# 128MB Maximum Receive & Send Buffers for 10G/25G/100G interfaces
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864
net.ipv4.tcp_mtu_probing = 1
net.core.somaxconn = 2147483647
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_max_syn_backlog = 3240000

# --- Sun RPC Slot Table Optimization ---
# Elevate in-flight RPC request slots per TCP connection
sunrpc.tcp_slot_table_entries = 128
```

To apply parameter updates dynamically without rebooting:
```bash
sudo sysctl -p /etc/sysctl.d/99-nfs-performance.conf
```

### B. Persistent RPC Slot Table Configuration

For kernel module stability across reboots, also persist the RPC slot table entries in `/etc/modprobe.d/sunrpc.conf`:
```ini
options sunrpc tcp_slot_table_entries=128
```

---

## 💾 2. NFS Client-Side Caching with `cachefilesd`

FS-Cache allows NFS clients to cache read-frequently data locally on flash or NVMe drives, reducing network latency.

### Installation & Daemon Activation
On RHEL, Enterprise Linux, AlmaLinux, or Rocky Linux:
```bash
sudo dnf install -y cachefilesd
sudo systemctl enable cachefilesd
```

On Debian or Ubuntu:
```bash
sudo apt update && sudo apt install -y cachefilesd
sudo systemctl enable cachefilesd
```

### Configuration (`/etc/default/cachefilesd`)
Ensure the service is explicitly enabled:
```ini
RUN=yes
```

Restart and verify kernel keyring registration:
```bash
sudo systemctl restart cachefilesd
sudo systemctl status cachefilesd
dmesg | grep cachefiles
```

---

## 🛠️ 3. Tuned NFS v4.2 Mount Configuration (`/etc/fstab`)

To maximize I/O throughput and manage metadata consistency, mount NFS exports using tuned parameters:

```text
nfsserver:/export/data /mnt/songketmail nfs4 rw,fsc,sync,vers=4.2,rsize=1048576,wsize=1048576,hard,proto=tcp,nconnect=4,timeo=600,retrans=2,sec=sys,local_lock=none,noresvport,_netdev 0 0
```

### Parameter Breakdown

| Option | Function | Performance & Durability Trade-off |
|---|---|---|
| `sync` | Forces synchronous write operations | **Durability Guarantee**: Guarantees that write operations are committed to non-volatile storage before returning to the client. *Trade-off*: Higher write latency per I/O compared to `async` (which buffers writes in client RAM at the risk of data loss during sudden power loss). |
| `rsize=1048576` | Sets read chunk size to 1MB | Maximizes block transfer payloads per RPC round-trip. |
| `wsize=1048576` | Sets write chunk size to 1MB | Maximizes sequential write throughput over 10G/25G networks. |
| `nconnect=4` | Establishes 4 parallel TCP streams per mount | Distributes RPC processing across multiple CPU cores, eliminating single-core bottlenecks. |
| `vers=4.2` | Forces NFS v4.2 protocol | Enables Server-Side Copy (SSC), sparse file support, and extended attributes. |
| `fsc` | Enables FS-Cache client-side caching | Integrates local drive cache via `cachefilesd`. |
| `hard` | Infinite retries on I/O timeout | Guarantees data integrity for High Availability cluster workloads. |
| `noresvport` | Uses non-privileged source ports | Prevents reconnection issues across network firewalls/NAT. |
| `_netdev` | Defers mounting until network initialization | Prevents boot hangs on system startup. |

---

## 🔬 4. Deep-Dive Technical Analysis: `nconnect` & RPC Concurrency

### 1. Kernel Prerequisites
- `nconnect` requires **Linux Kernel 5.3+** on client systems (standard in Ubuntu 22.04/24.04/26.04 and AlmaLinux 9+).
- **Kernel 5.17+** completely re-architected the FS-Cache subsystem (`fscache`), dramatically reducing locking contention during high-concurrency client caching.

### 2. Single-Connection Bottleneck vs. `nconnect` Multiplexing
Traditionally, an NFS mount utilizes a single TCP connection. On modern multi-core CPUs and high-speed networks (25GbE/100GbE), processing a single TCP socket stream is pinned to a single CPU core. This creates a severe single-thread bottleneck.

By specifying `nconnect=N` (e.g., `nconnect=4` to `nconnect=16`):
1. **True Parallelism**: The client creates $N$ distinct TCP connections for the same mount point.
2. **Per-CPU Load Balancing**: The Linux kernel distributes RPC encoding/decoding and socket interrupts across $N$ distinct CPU cores.
3. **RPC Slot Multiplication**: Combined with `sunrpc.tcp_slot_table_entries=128`, total in-flight concurrency scales to:
   $$\text{Total Slots} = N \times 128 = 4 \times 128 = 512 \text{ concurrent RPC requests}$$

---

## 📊 5. Ceph RBD Burst IOPS Benchmarking with `fio`

To validate Ceph RADOS Block Device (RBD) performance on Proxmox VE hypervisors with NVMe storage pools, execute automated synthetic benchmarks using `fio`.

### Executing the Benchmark Script
Run the built-in benchmarking tool:
```bash
# Dry-run / audit mode
./scripts/benchmark_ceph_rbd_fio.sh --dry-run

# Production benchmark execution against Proxmox NVMe pool
./scripts/benchmark_ceph_rbd_fio.sh --pool nvme-pool --image fio_test --size 4096 --runtime 30
```

### Benchmark Profile Matrix

| Benchmark Profile | Block Size | I/O Engine | IO Depth | Jobs | Direct I/O | Performance Objective |
|---|---|---|---|---|---|---|
| **4K Random Read Burst** | `4k` | `rbd` / `libaio` | 64 | 4 | `1` | Measure maximum read IOPS and sub-millisecond latency. |
| **4K Random Write Burst** | `4k` | `rbd` / `libaio` | 64 | 4 | `1` | Measure write IOPS under BlueStore DB write-ahead log (WAL). |
| **4K Mixed 70/30 R/W** | `4k` | `rbd` / `libaio` | 64 | 4 | `1` | Simulate real-world database and maildir workload. |
| **1M Sequential Read** | `1m` | `rbd` / `libaio` | 32 | 2 | `1` | Measure maximum read throughput in GB/s. |
| **1M Sequential Write** | `1m` | `rbd` / `libaio` | 32 | 2 | `1` | Measure maximum write throughput in GB/s. |

### Sample FIO Direct Benchmark Command
```bash
fio --name=ceph_rbd_4k_burst \
    --ioengine=rbd \
    --clientname=admin \
    --pool=nvme-pool \
    --rbdname=fio_test_image \
    --rw=randrw \
    --rwmixread=70 \
    --bs=4k \
    --iodepth=64 \
    --numjobs=4 \
    --direct=1 \
    --runtime=30 \
    --time_based \
    --group_reporting
```

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-09-05*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

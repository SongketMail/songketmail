---
okf_version: 0.1
type: documentation
title: "Ceph Native Deployment on Ubuntu 26.04 Server LTS"
description: "A comprehensive guide on deploying an independent 3-node Ceph storage cluster on Ubuntu 26.04 Server LTS, integrating it with a 4-node Proxmox VE 9 cluster, and performance tuning."
resource: "file:///docs/ceph-ubuntu-deployment.md"
timestamp: 2026-08-12T12:00:00Z
topics: [ceph, ubuntu, proxmox, deployment, rbd, architecture]
---
# 📦 Ceph Native Deployment on Ubuntu 26.04 Server LTS

This documentation details the architecture, design, and end-to-end automation of a 3-node independent Ceph storage cluster running **Ubuntu 26.04 LTS (Noble Numbat)** and the **Ceph Tentacle** release, fully integrated as an external storage provider for a 4-node **Proxmox Virtual Environment (PVE) 9** compute cluster.

---

## 📐 1. Design & Planning

Establishing an enterprise-grade storage backend requires strict separation of concerns, high-bandwidth storage fabrics, and granular resource limits on hypervisors and storage nodes.

### 1.1 Physical Network Segmentation & Addressing Plan

To avoid packet contention, split-brain conditions, and latency spikes on PVE quorum heartbeats, the cluster architecture uses three physically separated networks, each bound to non-overlapping IP subnets:

```
               +-------------------------------------------+
               |         ENTERPRISE FABRIC SEGMENTS        |
               +-------------------------------------------+
               |                                           |
               |  === [ PVE MGMT NETWORK: 10.10.10.0/24 ]  |
               |      Used for VM/CT console, API access   |
               |                                           |
               |  === [ CEPH PUBLIC NET: 10.10.20.0/24  ]  |
               |      Used for MON quorum, client mounts   |
               |                                           |
               |  === [ CEPH CLUSTER NET: 10.10.30.0/24 ]  |
               |      Used for OSD peer backfill/rebalance |
               |                                           |
               +-------------------------------------------+
```

| Hostname | Role | PVE MGMT IP | Ceph Public IP | Ceph Cluster IP |
|---|---|---|---|---|
| **ceph-node1** | Ceph Storage MON/MGR/OSD | — | 10.10.20.11 | 10.10.30.11 |
| **ceph-node2** | Ceph Storage MON/MGR/OSD | — | 10.10.20.12 | 10.10.30.12 |
| **ceph-node3** | Ceph Storage MON/MGR/OSD | — | 10.10.20.13 | 10.10.30.13 |
| **pve-node1** | PVE 9 Compute Host | 10.10.10.21 | 10.10.20.21 | — |
| **pve-node2** | PVE 9 Compute Host | 10.10.10.22 | 10.10.20.22 | — |
| **pve-node3** | PVE 9 Compute Host | 10.10.10.23 | 10.10.20.23 | — |
| **pve-node4** | PVE 9 Compute Host | 10.10.10.24 | 10.10.20.24 | — |

### 1.2 Capacity Sizing & Calculations

The raw disk array sizing target provides high performance and data durability using standard **3x replication** policies:

- **Raw NVMe Storage Array**: Each Ceph storage node houses **3× 17.1TB enterprise NVMe SSDs** in IT/Passthrough mode.
- **Raw Total Capacity**: 3 nodes × 3 drives × 17.1TB = **153.9TB Raw (approx. 154TB)**.
- **Usable Pool Capacity (3x Replication)**: 154TB / 3 = **51.3TB Usable (approx. 51TB)**.
- **OSD Resource Sizing**: To allow intensive storage operations (scrubbing, deep backfilling, rebalancing) without bottlenecking the underlying OS:
  - **Memory Limits**: 8 GiB RAM per OSD daemon (Total 24 GiB per storage node reserved exclusively for OSDs).
  - **CPU Allocation**: Minimum 1 physical core/thread per OSD daemon.

---

## 🖥️ 2. PVE Cluster Build

The compute layer consists of four greenfield Proxmox VE 9 nodes designed to execute virtual machines and containerized workloads.

### 2.1 PVE Greenfield Install & Quorum
1. **Host OS Provisioning**: Install Proxmox VE 9 on each of the 4 compute nodes. Keep local system volumes isolated from Ceph.
2. **Corosync Configuration**: Initialize a redundant Corosync cluster link over dedicated low-latency physical switches:
   ```bash
   pvecm create pve-compute-cluster --link0 10.10.10.21
   ```
3. **Cluster Joining**: Join the remaining three nodes to form a highly available, 4-node quorum cluster:
   ```bash
   pvecm add 10.10.10.21 --link0 10.10.10.22  # From pve-node2
   pvecm add 10.10.10.21 --link0 10.10.10.23  # From pve-node3
   pvecm add 10.10.10.21 --link0 10.10.10.24  # From pve-node4
   ```

---

## 🐙 3. Ceph Production Cluster Deployment

This stage uses Ansible to prepare the minimal Ubuntu 26.04 Server hosts and deploy containerized Ceph daemons via the native **`cephadm`** orchestrator.

### 3.1 Ansible Automated Roles

Our standalone Ansible Playbook structures deployment into five modular phases:
- **`ceph_prep`**: Installs `podman`, configures kernel requirements (file max, netfilter modules), and synchronizes Chrony NTP clocks.
- **`ceph_bootstrap`**: Downloads `cephadm`, bootstraps the active MON/MGR, clusters the storage nodes, and spins up OSDs across nvme target drives.
- **`security_hardening`**: Hardens storage nodes using precise network isolation rules.
- **`pve_integration`**: Handles keyring transfer, storage.cfg distribution, and VM storage verification.
- **`validation_bench`**: Runs storage synthetic benchmarking to output cluster statistics.

---

## 🔗 4. PVE–Ceph Integration

Integrating the independent Ceph cluster as an external storage backend for Proxmox VE requires client keyring delegation and clustered storage registration.

### 4.1 Keyring Extraction & Delegation
1. On **ceph-node1** (the bootstrap node), extract the administrative access keyring:
   ```bash
   ceph auth get-or-create client.admin
   ```
2. Distribute this keyring securely to all PVE compute hosts inside the secure Proxmox cluster directory `/etc/pve/priv/ceph/`:
   ```bash
   mkdir -p /etc/pve/priv/ceph/
   scp /etc/ceph/ceph-prod.client.admin.keyring root@10.10.10.21:/etc/pve/priv/ceph/external-ceph-prod.keyring
   ```

### 4.2 Storage Registration (`/etc/pve/storage.cfg`)
Define the external RADOS Block Device (RBD) backend in the PVE clustered configuration:
```ini
rbd: external-ceph-prod
    monhost 10.10.20.11;10.10.20.12;10.10.20.13
    pool pve-rbd-pool
    username admin
    content images,rootdir
    krbd 0
```

---

## 🛡️ 5. Network & Security Hardening

To guarantee maximum protection of storage assets, physical networks must be isolated using firewall policies.

### 5.1 IPTables Storage Isolation Rules

```
+---------------------------------------------------------------------------------------------------+
|                                 STORAGE HARDENING FIREWALL                                        |
+---------------------------------------------------------------------------------------------------+
|  [ INCOMING TRAFFIC ]                                                                             |
|                                                                                                   |
|    Source: 10.10.20.0/24 (Public Net)  -->  Ports: 6789, 3300 (MON/MGR)  -->  [ ALLOW ]           |
|    Source: 10.10.30.0/24 (Cluster Net) -->  Ports: 6800:7300 (OSDs)      -->  [ ALLOW ]           |
|    Source: Any (Outside segments)      -->  Ports: 6789, 3300            -->  [ DROP ]            |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

Our playbook implements these restrictions natively via FQCN-compliant firewall tasks:
- **Rule 1**: Allow inbound traffic on ports `6789` and `3300` only if originating from the `10.10.20.0/24` Public network.
- **Rule 2**: Allow inbound traffic on port range `6800:7300` (OSD daemons) only if originating from the `10.10.30.0/24` Cluster network.
- **Rule 3**: Explicitly drop any remaining storage traffic attempts from untrusted segments.

---

## 📊 6. Validation & Benchmarking

Verifying performance baselines helps confirm proper disk, fabric, and controller initialization before VM provisioning.

### 6.1 Cluster RADOS Benchmarking
Run the synthetic object bench tool directly from containerized cephadm shell:
```bash
cephadm shell -- rados bench -p pve-rbd-pool 30 write --no-cleanup
```
- Capture throughput (MB/s), average write latency (ms), and sustained IOPS.
- Clean up test benchmarks objects:
  ```bash
  cephadm shell -- rados -p pve-rbd-pool cleanup
  ```

---

## 🔄 7. HA Testing & Operational Runbook

This runbook guides administrators through routine storage node maintenance, recovery drills, and quorum failover handling.

### 7.1 Simulated Storage Node Outage (Drain and Maintenance)
When performing standard kernel upgrades or physical hardware repairs on a storage host, follow these precise maintenance commands:

1. **Set Cluster OSD Maintenance Flags**: Inform the cluster that a node is temporarily going offline to prevent immediate data replication or backfilling overhead:
   ```bash
   ceph osd set noout
   ```
2. **Gracefully stop OSD services on the node**: Shut down target daemons on the active maintenance node:
   ```bash
   systemctl stop ceph-osd@*
   ```
3. **Execute Host Repair**: Perform OS/kernel patching, reboot the host, and ensure all networks reconnect correctly.
4. **Restore Services and Clear Flags**: Re-enable standard data backfilling and healing:
   ```bash
   systemctl start ceph-osd@*
   ceph osd unset noout
   ```

### 7.2 Storage Quorum Healing Verification
Check the real-time cluster health and recovery status during rebalancing operations:
```bash
ceph status
ceph -w
```
Confirm health returns to `HEALTH_OK` once replication catchup completes.

---

*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-12*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

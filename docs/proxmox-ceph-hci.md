---
okf_version: 0.1
type: research
title: "Proxmox and Ceph Hyper-Converged Cluster Integration"
description: "A deep dive research guide on deploying a hyper-converged Proxmox VE + Ceph cluster, extending storage pools natively to Ubuntu 26.04 server LTS, and tuning performance."
resource: "file:///docs/proxmox-ceph-hci.md"
timestamp: 2026-08-12T12:00:00Z
topics: [proxmox, ceph, hyper-converged, rbd, cephfs, ubuntu]
---
# 📦 Proxmox and Ceph Hyper-Converged Cluster Integration

This guide outlines the integration of Proxmox Virtual Environment (PVE) and Ceph, covering hyper-converged architecture, physical network isolation, performance tuning, and the end-to-end deployment flow for production and disaster recovery (DR) environments.

---

## 🔄 Deployment Flow — Proxmox VE + External Ceph (Production & DR)

Implementing an enterprise-grade Proxmox VE hypervisor cluster coupled with an external, independent Ceph storage backend involves a structured multi-stage deployment flow. This design guarantees clear separation of concerns, high-performance replication, and bulletproof failover capability between active production and passive disaster recovery (DR) sites.

```
+---------------------------------------------------------------------------------------------------+
|                                     DEPLOYMENT STAGE FLOW                                         |
+---------------------------------------------------------------------------------------------------+
|  STAGE 1: Configure Proxmox VE 9 Compute Cluster (4 nodes, no local Ceph)                         |
|    |                                                                                              |
|    +---> STAGE 2A: Configure Ceph Production Cluster (3 nodes, Ubuntu 26.04 + Tentacle)           |
|    |       |                                                                                      |
|    |       +---> STAGE 3: Configure RBD Mirroring Production <-> DR (replication link)            |
|    |       |       |                                                                              |
|    +---> STAGE 2B: Configure Ceph DR Cluster (3 nodes, Ubuntu 26.04 + Tentacle)                   |
|            |       |                                                                              |
|            |       v                                                                              |
|            +---> STAGE 4: Integrate PVE <-> Ceph (Keyring transfer, storage.cfg, test VM on pool)  |
|                    |                                                                              |
|                    v                                                                              |
|                  STAGE 5: Validate & Test (Benchmark, HA node failure, DR failover / failback)     |
|                    |                                                                              |
|                    v                                                                              |
|                  STAGE 6: Documentation, UAT & Handover to Customer                             |
+---------------------------------------------------------------------------------------------------+
```

### Stage 1: Compute Cluster Provisioning
* **Objective**: Deploy a robust, high-availability compute layer on Proxmox VE 9 without storage resource contention.
* **Actions**:
  - Provision a **4-node Proxmox VE 9 compute cluster** on physical hardware nodes.
  - Disable local Ceph services (`pveceph` is not bootstrapped locally) to preserve maximum CPU and memory capacity for guest virtual machines and containers.
  - Configure redundant corosync interfaces on dedicated low-latency physical switches to prevent cluster split-brain.

### Stage 2: Dual-Site Ceph Cluster Sizing & Bootstrap
* **Objective**: Establish independent production and disaster recovery (DR) storage clusters using minimal Ubuntu 26.04 LTS installations.
* **Actions**:
  - **Production Site (Stage 2A)**: Bootstrap a **3-node Ceph Production cluster** running Ubuntu 26.04 LTS and the Ceph **Tentacle** release (containerised via `cephadm`). Assign at least 3 Monitors (MONs) and 3 Managers (MGRs) for robust quorum, mapping physical disks to dedicated OSD daemons.
  - **Disaster Recovery Site (Stage 2B)**: Deploy a mirroring clone of the production storage setup using another **3-node Ceph DR cluster** on identical hardware and Ubuntu 26.04 + Tentacle software stacks.

### Stage 3: High-Performance WAN/Replication Mirroring
* **Objective**: Connect the isolated storage clusters over a WAN link for block-level data replication.
* **Actions**:
  - Configure **Ceph RADOS Block Device (RBD) Mirroring** between the Production and DR clusters.
  - Set up an active-passive replication link using daemon-to-daemon token exchange.
  - Define mirroring policies (journal-based or snapshot-based) to enforce target Recovery Point Objectives (RPO) and Recovery Time Objectives (RTO).

### Stage 4: Cross-Cluster Integration
* **Objective**: Bind the Proxmox VE 9 compute hypervisors directly to the external Ceph production and DR pools.
* **Actions**:
  - Extract the client keyrings from the production and DR storage clusters.
  - Securely transfer keyrings onto the Proxmox clustered filesystem (`pmxcfs`) at `/etc/pve/priv/ceph/`.
  - Register the external pools in `/etc/pve/storage.cfg` on the PVE cluster.
  - Deploy a test virtual machine directly onto the external Production RBD pool to verify end-to-end read, write, and dynamic volume provisioning capabilities.

### Stage 5: Rigorous Validation & Stress Testing
* **Objective**: Verify cluster stability, network isolation, throughput, and failover behavior under simulated disaster scenarios.
* **Actions**:
  - Run synthetic storage benchmarks (using `fio` and `rados bench`) to capture baseline read/write IOPS and latency.
  - Perform **High Availability (HA) Node Failure Testing**: Forcefully terminate or fence PVE compute nodes and Ceph OSD/MON hosts to verify automatic workload relocation and storage rebalancing.
  - Execute **DR Failover & Failback Drills**: Demote the active production pools, promote the DR pools, redirect PVE hypervisors to mount the promoted DR storage, and verify virtual machine bootability. Follow up with a reverse failback drill to restore normal operations.

### Stage 6: Documentation, UAT & Handover
* **Objective**: Package operational knowledge, finalize formal client sign-off, and execute the operational transition.
* **Actions**:
  - Compile the system blueprint, network configuration worksheets, keyring management procedures, and disaster recovery execution runbooks.
  - Perform the User Acceptance Testing (UAT) review with client stakeholders.
  - Formally hand over the integrated, highly available Proxmox VE 9 + External Ceph architecture to the customer's operations team.

---

Traditional datacenter environments separate compute and storage into isolated silos, requiring expensive Storage Area Networks (SANs) or Network Attached Storage (NAS) appliances. **Hyper-Converged Infrastructure (HCI)** collapses these silos by co-locating compute (VMs and containers) and software-defined storage directly on the same physical hypervisor nodes.

Through native integration with **Ceph**, a highly scalable, distributed object store and file system, **Proxmox VE (PVE)** provides a turnkey platform to deploy, manage, and scale hyper-converged storage directly from the hypervisor console.

---

## 🏛️ Proxmox + Ceph HCI Architecture

A healthy, production-grade Proxmox VE hyper-converged Ceph cluster typically starts with a **minimum of 3 identical nodes** to ensure high availability, data redundancy, and quorum.

```
       +---------------------------------------------------+
       |              Proxmox VE + Ceph HCI                |
       +-----------------+-----------------+---------------+
       |     Node 1      |     Node 2      |    Node 3     |
       |  [MON] [MGR]    |  [MON] [MGR]    |  [MON] [MGR]  |
       |  [OSD] [OSD]    |  [OSD] [OSD]    |  [OSD] [OSD]  |
       +--------+--------+--------+--------+-------+-------+
                |                 |                |
  ==============+=================+================+==============  Ceph Public (10/25G)
  ==============+=================+================+==============  Ceph Cluster (10/25G)
  ==============+=================+================+==============  Corosync Link (1G)
```

### Core Daemons & Functions
- **Ceph Monitor (ceph-mon / MON)**: Maintains the master copy of the cluster map and tracks cluster health. Quorum requires an odd number of MONs (minimum 3).
- **Ceph Manager (ceph-mgr / MGR)**: Runs alongside monitors to provide additional monitoring, PG autoscaling, device health checks, and orchestration interfaces.
- **Ceph Object Storage Daemon (ceph-osd / OSD)**: Handles physical disk read/write operations, peer replication, and data rebalancing. Usually, one OSD is mapped per physical disk.
- **Ceph Metadata Server (ceph-mds / MDS)**: Manages metadata for the **CephFS** POSIX-compliant filesystem, translating file paths to RADOS objects.

---

## ⚙️ Hardware & Network Requirements for Stable HCI

Particularly in hyper-converged environments where compute and storage share resources, hardware sizing and network design dictate cluster stability.

### 1. Compute & Sizing Guidelines
- **CPU Reservation**: Allocate at least 1 physical core (or thread) purely to each OSD daemon. For modern enterprise NVMe drives capable of sustaining over 100,000 IOPS, an OSD can consume **4 to 6 threads** during peak performance or recovery loops.
- **Memory Planning**: Configure OSDs with a minimum of **8 GiB of RAM** per daemon (where the base OSD daemon consumes 4 GiB at idle, and the remaining headroom is critical for backfilling, rebalancing, or node failure recovery).
- **Storage Controllers**: **Avoid RAID controllers**. Use Host Bus Adapters (HBA) or flash controllers in IT/Pass-through mode. Ceph handles redundancy natively at the software layer; hardware RAID caching algorithms interfere with Ceph's BlueStore transactional engine, leading to latency spikes and silent corruption risks.
- **BlueStore DB/WAL Separation**: Utilize BlueStore (default engine) and, if budget permits, place the metadata database (`block.db`) and journal write-ahead log (`block.wal`) on a high-speed, low-latency NVMe SSD, while allocating standard SATA/SAS SSDs for bulk object storage.

### 2. Physical Network Isolation
To safeguard the cluster from split-brain scenarios and corosync timeout failures (which would break Proxmox cluster quorum and trigger immediate node self-fencing), Ceph traffic must be physically segregated:

| Network Interface | Recommended Bandwidth | Purpose |
|---|---|---|
| **Corosync Link** | 1 Gbps (Dedicated, Low Latency) | Latency-sensitive cluster heartbeat and quorum voting. |
| **Ceph Public Net** | 10 Gbps (or 25+ Gbps NVMe) | Storage traffic between PVE hypervisor clients (VMs/containers) and Ceph daemons. |
| **Ceph Cluster Net** | 10 Gbps (or 25+ Gbps NVMe) | High-bandwidth backend replication and OSD heartbeat rebalancing. |

---

## 🛠️ Performance Tuning & Pool Optimization

### 1. Placement Group (PG) Autoscaling
Placement Groups are logical fragments used to group objects within a pool to distribute writes evenly across OSDs.
- Enable the **PG Autoscaler** to dynamically adjust the PG count based on dataset growth:
  ```bash
  ceph mgr module enable pg_autoscaler
  ceph osd pool set <pool-name> pg_autoscale_mode on
  ```
- Setting `target_size` or `target_size_ratio` on pools gives the autoscaler early hints, preventing massive, performance-degrading reshuffles later.

### 2. Erasure Coding (EC) & FastEC Optimization
Erasure Coding provides high storage efficiency compared to traditional 3x replication (e.g., `k=2, m=1` provides 66% usable capacity compared to 33% on 3x replication).
To bypass the traditional latency penalty of EC on virtual machine workloads, enable **FastEC** on your data pool:
- Ensure the cluster is at least at the **Tentacle** release.
- Verify the default EC profile uses a compatible technique (e.g., `reed_sol_van`).
- Enable partial writes and partial reads optimization:
  ```bash
  ceph osd pool set <pool-name>-data allow_ec_optimizations 1
  ```
  *Note: `allow_ec_optimizations` is a one-way switch. Once enabled, it cannot be cleared without draining and recreating the pool.*

---

## 📊 Manpower & Operational Effort Analysis

Is the operational effort the same for **Proxmox VE Compute + Proxmox-managed Ceph** (decoupled via network) versus **Proxmox VE Compute + Ubuntu Ceph (`cephadm`)**?

**No, they are significantly different.** Although both architectures separate compute and storage layers over the network (avoiding resource contention on a single hypervisor host), the manpower, tooling, skillsets, and lifecycle management requirements diverge considerably.

Below is an in-depth analysis of the effort profiles for both scenarios:

### 1. Scenario A: Decoupled Proxmox VE Compute + Proxmox-Managed Ceph (Two PVE Clusters)
In this model, the infrastructure is split into:
* **PVE Compute Cluster**: Hypervisors configured only for VM execution and High Availability (HA), with no local Ceph OSDs.
* **PVE Storage Cluster**: A separate Proxmox VE cluster configured to run Ceph (and perhaps minor storage-related helper VMs) that delivers RBD/CephFS over the network to the Compute hypervisors.

#### Operational & Manpower Advantages:
* **Unified Control Plane & Low Learning Curve**: Sysadmins use the exact same Proxmox GUI, API, and `pveceph` CLI commands to manage both clusters. No specialized Ceph Orchestration CLI training is required.
* **Turnkey Provisioning**: OSDs, Monitors, Managers, and MDS daemons are provisioned via a single click in the PVE GUI or a single `pveceph` command.
* **Integrated Upgrades**: Proxmox coordinates Ceph upgrades directly within its normal package update repository. When Proxmox is upgraded, the underlying Ceph package upgrades are verified and integrated by the Proxmox team, minimizing compatibility testing effort.
* **Shared Cluster Knowledge**: The team only needs to master Proxmox administration, reducing the specialized staff overhead.

#### Drawbacks:
* **Licensing / Subscription Costs**: If using enterprise support, subscriptions are required for all nodes in both the Compute and Storage clusters.
* **Hypervisor Overhead**: The storage nodes run a full Proxmox VE hypervisor OS, consuming slightly more resource overhead than a minimal storage-only OS.

---

### 2. Scenario B: Proxmox VE Compute + Ubuntu Ceph (via `cephadm`)
In this model, compute is hosted on Proxmox VE, but the storage backend is deployed on raw, minimal Ubuntu 26.04 LTS servers managed independently via the official upstream **`cephadm`** containerized orchestrator.

#### Operational & Manpower Advantages:
* **Pure Storage Efficiency**: Operating system overhead is absolutely minimized. No hypervisor layers or graphical management overheads run on the storage nodes.
* **Granular Upstream Control**: Direct access to the newest Ceph features, point releases, and custom optimization parameters immediately upon release by the Ceph Foundation.
* **No PVE Licensing for Storage**: Storage nodes require no Proxmox VE subscriptions, reducing licensing costs.

#### Drawbacks & Manpower Multipliers:
* **Fragmented Management (Two Separate Toolchains)**: Administrators must navigate the Proxmox VE GUI/CLI for compute, and completely switch to the `cephadm` CLI / Ceph Dashboard for storage operations.
* **High Learning Curve & Specialized Skillsets**: Requires team members with deep knowledge of containerized Ceph deployments, systemd-container interactions (`cephadm` uses Podman or Docker under the hood), and upstream Ceph CLI orchestration (`ceph orch`).
* **Complex Upgrades & Compatibility Risks**: Upgrades must be manually planned, tested, and executed using `cephadm`. The administrator is fully responsible for verifying that the new Ceph version remains compatible with Proxmox's RBD client library (`librbd`).
* **Manual Network & Keyring Syncing**: Every time a storage node, monitor IP, or pool key is added, updated, or rotated, sysadmins must manually synchronize configurations, update keyrings, and modify `/etc/pve/storage.cfg` across the compute cluster.

---

### ⚖️ Operational Effort Comparison Matrix

| Operational Dimension | Scenario A: Proxmox-Managed Ceph (2 PVE Clusters) | Scenario B: Ubuntu Ceph (`cephadm`) | Effort Verdict |
|---|---|---|---|
| **Initial Deployment** | **Low to Medium**: Guided GUI/CLI setup using native Proxmox wizardry. | **High**: Requires manual host prep, container runtime setup, `cephadm` bootstrap, and cluster discovery. | **Scenario A is easier.** |
| **Ongoing Monitoring** | **Low**: Real-time status, performance charts, and alerts integrated directly into the Proxmox UI. | **Medium to High**: Requires managing a separate Ceph Dashboard or setting up external Prometheus/Grafana stacks. | **Scenario A is easier.** |
| **Upgrade Lifecycle** | **Low**: Streamlined through Proxmox's Debian-based APT repositories and unified cluster upgrade paths. | **High**: Requires executing automated orchestrator upgrades, monitoring container pulls, and verifying client-side compatibility. | **Scenario A is easier.** |
| **Troubleshooting & Support** | **Medium**: Single point of contact (Proxmox Support) for both hypervisor and storage layers. | **High**: Separate debugging for Ubuntu, Docker/Podman container runtimes, Ceph orchestrator issues, and Proxmox integration layers. | **Scenario A is easier.** |
| **Staffing & Training Costs** | **Low**: Standard PVE sysadmin skills are sufficient for both environments. | **High**: Requires specialized, expensive storage-engineering and container-orchestration training. | **Scenario A is easier.** |

---

## 🐧 Ceph Native Deployment on Ubuntu 26.04 Server LTS

While Proxmox VE manages Ceph natively through the GUI or `pveceph`, deploying an independent or connected Ceph cluster node on **Ubuntu 26.04 LTS** requires utilizing the official **`cephadm`** orchestrator.

### 1. Bootstrapping the Ubuntu 26.04 Storage Node
Install dependencies and bootstrap the cluster using a dedicated IP interface:
```bash
# Update packages and install Docker/Podman container runtime
sudo apt update && sudo apt install -y docker.io python3

# Download and run the cephadm bootstrap
curl --silent --remote-name https://download.ceph.com/rpm/el9/scap-security-guide/cephadm
chmod +x cephadm
sudo ./cephadm bootstrap --mon-ip <UBUNTU_NODE_IP>
```
This commands creates an initial Monitor, a Manager, distributes the cluster keys, and spins up a web dashboard on port `8443`.

### 2. Provisioning OSDs on Ubuntu
Once the cluster is running, identify raw, unpartitioned disks on the host and assign them as OSD storage devices:
```bash
# List available storage devices
sudo ceph orch device ls

# Add a specific disk as an OSD daemon
sudo ceph orch daemon add osd <ubuntu-hostname>:<device-path> (e.g., ubuntu-srv1:/dev/nvme0n1)
```

---

## 🔗 Cross-Cluster Connectivity: PVE to Ubuntu 26.04

To scale storage limitlessly or split storage costs, a Proxmox VE hyper-converged cluster can either consume external pools running on Ubuntu 26.04 or export its own pools to Ubuntu clients.

### Case A: Proxmox VE Consuming External Ceph Storage (Ubuntu 26.04)

```
  +------------------+                   +--------------------+
  |  Proxmox VE      |  (RBD / CephFS)   |  Ubuntu 26.04 LTS  |
  |  HCI Cluster     | <================ |  External Storage  |
  |  [VMs/Containers]|   Port 6789/tcp   |  [OSD Cluster]     |
  +------------------+                   +--------------------+
```

1. **Extract Client Keyring**: On the Ubuntu 26.04 Ceph cluster, retrieve the admin keyring:
   ```bash
   sudo ceph auth get-or-create client.admin
   ```
2. **Transfer Keyring to PVE**: Copy the keyring file to the secure Proxmox clustered filesystem (`pmxcfs`), naming it to match your intended storage ID:
   ```bash
   mkdir -p /etc/pve/priv/ceph
   scp user@<ubuntu-ip>:/etc/ceph/ceph.client.admin.keyring /etc/pve/priv/ceph/<storage-id>.keyring
   ```
3. **Configure Storage backend in PVE**: Add the external RADOS Block Device (RBD) config to `/etc/pve/storage.cfg`:
   ```ini
   rbd: external-ubuntu-ceph
       monhost 10.10.10.20:6789;10.10.10.21:6789;10.10.10.22:6789
       pool rbd-vm-pool
       username admin
       content images,rootdir
       krbd 0
   ```

### Case B: Ubuntu 26.04 Client Mounting PVE CephFS

1. **Export PVE Configuration**: Copy PVE's `/etc/pve/ceph.conf` and the client key to Ubuntu:
   ```bash
   scp root@<pve-ip>:/etc/pve/ceph.conf /etc/ceph/ceph.conf
   scp root@<pve-ip>:/etc/pve/priv/ceph/cephfs.keyring /etc/ceph/ceph.keyring
   ```
2. **Mount CephFS via fstab**: Add the mount option to `/etc/fstab` on Ubuntu 26.04 for high-performance, persistent file shares:
   ```text
   10.10.10.1:6789,10.10.10.2:6789,10.10.10.3:6789:/ /mnt/cephfs ceph name=admin,secretfile=/etc/ceph/ceph.keyring,_netdev,x-systemd.mount-timeout=15s 0 0
   ```

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-12*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

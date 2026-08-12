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

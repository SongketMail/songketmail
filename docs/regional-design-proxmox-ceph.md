---
okf_version: 0.1
type: documentation
title: "Geolocated Regional Data Center Design"
description: "A comprehensive technical design for a geodistributed multi-region Proxmox and Ceph infrastructure targeting high availability and regional redundancy."
resource: "file:///docs/regional-design-proxmox-ceph.md"
timestamp: 2026-08-14T12:00:00Z
topics: [proxmox, ceph, regional, geolocation, almalinux, architecture]
---

# Geolocated Regional Data Center Infrastructure Specification

---

## 🗺️ 1. Multi-Region Geodistributed Topology

By establishing three geographically isolated regional nodes, this architecture enforces cross-border fault isolation, regulatory data residency, and deterministic low-latency edge delivery.

```
       [ Region Alpha (Main/KUL) ]
             /               \
       IPsec Mesh         IPsec Mesh
           /                   \
[ Region Beta (JHB) ] ===== [ Region Gamma (PEN) ]
                    IPsec Mesh

```

### 1.1 Regional Characteristics

```
+------------------+-----------------------+---------------------------------------+-----------------------------+
| Region           | Geographic Role       | Primary Functional Workloads          | Interconnect Routing        |
+------------------+-----------------------+---------------------------------------+-----------------------------+
| Region Alpha     | Primary Ingestion &   | Core SongketMail MTA, Percona Patroni | Dual 10GbE dark fibre,      |
| (Central - KUL)  | Control Plane         | Master, Elastic Stack Hot Nodes       | FRR BGP with IPsec mesh     |
+------------------+-----------------------+---------------------------------------+-----------------------------+
| Region Beta      | Active-Active Replica | Read-replica MTAs, Patroni Standby,   | Redundant 10GbE WAN transit,|
| (Southern - JHB) | & Real-Time DR Target | Ceph Tier-2 Mirror, PBS Pull Target   | WireGuard/StrongSwan backup |
+------------------+-----------------------+---------------------------------------+-----------------------------+
| Region Gamma     | Edge Proxy, Analytics | GeoServer GIS workloads, Elastic Warm | Carrier-diverse MPLS/IPsec, |
| (Northern - PEN) | & Archival Target     | /Cold Nodes, PBS Offsite Cold Vault   | BGP EVPN fabric extension   |
+------------------+-----------------------+---------------------------------------+-----------------------------+

```

* **WAN Mesh Configuration:** Mesh networks operate across dynamic routing fabrics managed via [FRRouting (FRR)](https://frrouting.org/) utilising BGP over routed IPsec/WireGuard tunnels.
* **Consensus & State Isolation:** Quorum across distributed components (e.g., Patroni Distributed Configuration Stores via `etcd`, Ceph MON quorums) prevents split-brain by maintaining independent regional clusters federated at the application layer or using an offsite tie-breaker node.

---

## 🏛️ 2. Generalized Node Architecture (Per Region)

Each regional node implements a standardised, modular bare-metal specification designed for scale-out horizontal expansion, Day 2 operational simplicity, and zero vendor lock-in.

### 2.1 Hardware Sizing & Subsystem Specifications

```
+-------------------+---------------------------------------------------------+------------------------------------+
| Subsystem         | Hardware / Component Profile                            | Workload Target & Orchestration    |
+-------------------+---------------------------------------------------------+------------------------------------+
| Compute Fabric    | Dual AMD EPYC 9004 series (64C/128T per node), 512GB    | Proxmox VE 8.x / RKE2 K8s Nodes;   |
|                   | DDR5 ECC Registered RAM per hypervisor                  | Podman container runtimes          |
+-------------------+---------------------------------------------------------+------------------------------------+
| Security Layer    | Dedicated 1U appliances running Wazuh Agents,           | Layer 7 WAF, zero-trust mTLS,      |
|                   | [BunkerWeb WAF](https://www.bunkerweb.io/), OpenSCAP, Smallstep PKI  | automated PCI-DSS / ISO27001 scan  |
+-------------------+---------------------------------------------------------+------------------------------------+
| Networking        | Dual 25GbE Mellanox ConnectX-5 NICs (LACP bonded),      | RoCEv2 Ceph fabric, isolated VXLAN |
|                   | 100GbE QSFP28 Spine-Leaf Arista/Open Network switches   | / VLAN overlays for tenant traffic |
+-------------------+---------------------------------------------------------+------------------------------------+
| Storage Baseline  | Tier 1: NVMe U.2 Enterprise SSDs (PCIe Gen5, ZFS/Ceph); | Ultra-low latency IOPS (databases);|
|                   | Tier 2: High-density SATA/SAS Enterprise HDDs (18TB+)   | S3 Object / Maildir cold storage   |
+-------------------+---------------------------------------------------------+------------------------------------+
| Backup / Vault    | Dedicated 2U bare-metal chassis running Proxmox Backup  | PBS chunk storage, LTO-8/9 SAS tape|
|                   | Server with direct SAS HBA tape library interconnect    | autoloader connectivity ([PMTX](https://pbs.proxmox.com/docs/tape-backup.html)) |
+-------------------+---------------------------------------------------------+------------------------------------+
| AI / Vector Subsys| 2x NVIDIA L40S / A100 PCIe (or Sovereign Open GPUs),    | Local LLM inferencing, DSOM vector |
|                   | host-passthrough via VFIO to AI worker VMs              | search (`pg_vector`), Anti-Spam APM|
+-------------------+---------------------------------------------------------+------------------------------------+

```

---

## 🗄️ 3. Dual-Tier Ceph Storage Strategy

Storage workloads are partitioned to separate latency-sensitive transactional operations from high-volume sequential archival tiers.

```
       [ Proxmox VE Hypervisor Compute Fabric ]
             /                                \
   (Native Mesh / NVMe)               (10/25GbE Ceph Public Net)
           /                                    \
[ Tier 1: Hyper-Converged Ceph ]      [ Tier 2: AlmaLinux Ceph Storage SIG ]
  - BlueStore on NVMe (PCIe Gen5)       - High-Density OSDs (Enterprise HDDs)
  - VM Root Disks, WAL / DB Journals    - S3 RGW (Maildir, Attachments, Logs)
  - Managed via 'pveceph'               - RBD / CephFS Archival Pools

```

### 3.1 Tier 1: Local Hyper-Converged Ceph (Proxmox-Managed)

* **Underlying Engine:** Deployed directly onto Proxmox VE hypervisors using native `pveceph` tooling running the latest stable Ceph (Reef/Squid) releases.
* **Storage Medium:** Pure NVMe U.2/U.3 SSDs running Ceph BlueStore directly on raw block devices.
* **Target Workloads:** Virtual Machine boot drives, Patroni PostgreSQL write-ahead logs (`WAL`), Patroni base data directories, and Redis caching layers.
* **Documentation & Reference:** [Proxmox VE Ceph Server Administration](https://pve.proxmox.com/pve-docs/chapter-pveceph.html).

### 3.2 Tier 2: External Independent Ceph (AlmaLinux-Managed)

* **Underlying Engine:** Dedicated storage nodes running AlmaLinux 9 Enterprise, consuming upstream RPM packages maintained by the [CentOS Storage SIG Ceph Repository](https://sigs.centos.org/storage/).
* **Deployment & Lifecycle:** Automated deployment via `cephadm` or Ansible [Ceph-Ansible](https://docs.ceph.com/en/latest/cephadm/).
* **Target Workloads:** Object storage backing for SongketMail MIME attachments, Apache Kafka offloaded topics, Elastic cold indices, and GIS spatial assets.
* **Reference Guide:** [CentOS Storage SIG Documentation](https://sigs.centos.org/storage/) and [Ceph Deployment Documentation](https://docs.ceph.com/en/latest/cephadm/).

---

## 🔗 4. External Ceph Visibility Inside Proxmox VMs

Mapping storage from the external Tier 2 Ceph cluster into compute VMs running on Proxmox VE is achieved via three standard architectural approaches:

```
                                  [ External AlmaLinux Ceph Cluster ]
                                                  |
                    +-----------------------------+-----------------------------+
                    |                             |                             |
             (Approach A: KRBD)            (Approach B: Direct)          (Approach C: S3 API)
                    |                             |                             |
         [ PVE storage.cfg Client ]    [ Guest OS Driver / Mount ]     [ Application S3 SDK ]
                    |                             |                             |
             [ VM VirtIO SCSI ]                   |                             |
                    \                             |                             /
                     +---------------------> [ Guest VM ] <--------------------+

```

### Approach A: Hypervisor-Mediated Virtualization (`storage.cfg`)

Proxmox acts as the native Ceph client, mapping RBD images or CephFS exports directly to VMs as virtual disks (`VirtIO SCSI`).

* **Implementation:** The external Ceph keyring and `ceph.conf` are integrated into `/etc/pve/priv/ceph/<cluster>.keyring` and configured in `/etc/pve/storage.cfg`.
* **Proxmox Storage Configuration:**

```ini
rbd: external-ceph-tier2
        monhost 10.200.10.11:6789,10.200.10.12:6789,10.200.10.13:6789
        pool songketmail-vm-disks
        user admin
        keyring /etc/pve/priv/ceph/external-ceph-tier2.keyring
        content images

```

* **Pros:** Native hypervisor snapshots, live migration across PVE nodes without persistent guest mounts, zero guest-level storage configuration.
* **Reference:** [Proxmox VE External Ceph RBD Configuration](https://pve.proxmox.com/wiki/Storage:_RBD).

### Approach B: Guest-Native Direct Storage Protocol Access

Virtual Machines bypass the hypervisor storage abstraction entirely by establishing network routes directly to the Ceph Public Network.

* **Implementation:** The guest OS contains `librbd`, `ceph-common`, and kernel drivers for direct RBD mapping (`rbd map`) or POSIX-compliant CephFS mounts using `/etc/fstab`.
* **Mount Definition (`/etc/fstab` inside VM):**

```bash
admin@cluster-fs-id.cephfs=/ /mnt/songketmail-archive ceph name=admin,secretfile=/etc/ceph/admin.secret,_netdev,noatime 0 2

```

* **Pros:** VM-level multi-attach capabilities (`ReadWriteMany` volumes across multiple guest workers), POSIX compliance for legacy mail spool directories.
* **Reference:** [CephFS Kernel Mount Documentation](https://docs.ceph.com/en/latest/cephfs/mount-using-kernel-driver/).

### Approach C: S3-Compatible Object Storage Gateway (Ceph RGW)

Applications inside the VM consume storage over HTTPS via RESTful S3 APIs provided by Ceph RADOS Gateway (RGW).

* **Implementation:** Expose load-balanced RGW endpoints via HAProxy/Nginx. Applications use standard S3 SDKs (`aws-sdk`, `boto3`, MinIO Client).
* **Pros:** Complete decoupling from kernel storage drivers, built-in multi-tenancy, cross-region asynchronous bucket replication via Ceph Multisite Sync.
* **Reference:** [Ceph RADOS Gateway Guide](https://docs.ceph.com/en/latest/radosgw/).

---

## 🚀 5. Architectural Improvements & Hardening Recommendations

### 5.1 Time Synchronization: Chrony Geolocation Hardening

To prevent clock skew failures in distributed systems (which cause Ceph MON elections to fail and break Patroni consensus), deploy a geolocated, multi-source Chrony topology.

* **NTP Stratum Alignment:** Each region hosts local Stratum-1/Stratum-2 NTP servers synchronized to national metrology clocks (e.g., National Metrology Institute of Malaysia - NMIM).
* **Hardened Configuration (`/etc/chrony.conf`):**

```ini
# Regional Upstream Pools
server 0.my.pool.ntp.org iburst minpoll 4 maxpoll 8
server 1.my.pool.ntp.org iburst minpoll 4 maxpoll 8
# Cross-Region Inter-Node Peering
peer 10.100.0.10 maxpoll 6
peer 10.200.0.10 maxpoll 6

# Panic threshold: step clock if offset > 0.1s during boot; refuse large jumps at runtime
makestep 0.1 3
maxupdateskew 100.0
minsources 3

```

* **Reference:** [Chrony Security & Optimization Guide](https://chrony-project.org/doc/4.5/chrony.conf.html).

### 5.2 Network Tuning: MTU 9000 (Jumbo Frames)

Enable end-to-end Jumbo Frames across the storage switching matrix and inter-node links to reduce CPU interrupt overhead during high-throughput replication.

* **Interface Configuration (`/etc/network/interfaces` on Debian/PVE):**

```ini
auto bond0
iface bond0 inet manual
        bond-slaves eno1 eno2
        bond-miimon 100
        bond-mode 802.3ad
        bond-xmit-hash-policy layer2+3
        mtu 9000

auto vmbr10
iface vmbr10 inet static
        address 10.10.20.50/24
        bridge-ports bond0
        bridge-stp off
        bridge-fd 0
        mtu 9000

```

* **Reference:** [Proxmox Network Configuration Models](https://www.google.com/search?q=https://pve.proxmox.com/pve-docs/chapter-sysadmin.html%23sysadmin_network_configuration).

### 5.3 Network Ring-Fencing & Dynamic Routing Architecture

* **Interface Ring-Fencing:** Strictly separate management (`corosync`, SSH), storage (`Ceph Public/Cluster`), VM public traffic, and cross-DC WAN fabrics using isolated 802.1Q VLANs and physical NIC isolation.
* **Corosync Redundancy:** Corosync requires dedicated low-latency physical links. Configure two separate Corosync rings (`ring0_addr` and `ring1_addr`) over distinct networks to prevent split-brain fencing loops.
* **Reference:** [Corosync Cluster Engine Documentation](https://corosync.github.io/corosync/).

---

## 💾 6. Multi-Region Backup Architecture via Proxmox Backup Server (PBS)

To satisfy the **Backup 3-2-1 Rule** across a distributed layout, [Proxmox Backup Server (PBS)](https://www.proxmox.com/en/proxmox-backup-server) provides deduplication, client-side encryption, and WAN-optimised replication.

```
[ Region Alpha: PVE Nodes ]
        |
   (Local QEMU Dirty Bitmaps Backup)
        v
[ Region Alpha: PBS Local (ZFS Pool) ]
        |
   (Cross-Region Pull Sync Job over IPsec)
        v
[ Region Beta: PBS Remote Node ]  ======> [ Offsite Cold Tape Vault: LTO-9 / PMTX ]

```

### 6.1 Core Architectural Pillars of PBS

#### A. High-Performance Client-Server Engine (Rust-Powered)

* **Zstandard (ZSTD) Compression:** Data blocks are compressed on the hypervisor client using multi-threaded [ZSTD compression](https://facebook.github.io/zstd/), reducing network payload sizes before transfer.
* **QEMU Dirty Bitmaps Integration:** Hypervisor-native dirty bitmaps track modified storage sectors dynamically. Scheduled backups avoid re-reading unmodified disk areas, shortening backup windows.
* **Reference:** [Proxmox VE Backup Modes & Bitmaps](https://pve.proxmox.com/pve-docs/chapter-vzdump.html).

#### B. Chunk-Level Deduplication Engine

* **Fixed vs. Variable Chunking:** VM block storage devices are split into uniform fixed-size chunks (typically 4 MiB), while container archives (LXC/file-level) use variable-sized chunking algorithms to preserve alignment across shifted file streams.
* **Content-Addressable Storage:** Every chunk is assigned an ID based on its SHA-256 cryptographic digest. Repeated chunks across historical snapshots or multiple base VMs are written to disk only once.
* **Reference:** [PBS Technical Overview & Deduplication](https://pbs.proxmox.com/docs/introduction.html).

#### C. End-to-End Client-Side Encryption

* **Cryptographic Protocol:** Enforces AES-256 in Galois/Counter Mode (GCM) for combined confidentiality and data authenticity.
* **Key Architecture & Master Key Escrow:**
* Hypervisors encrypt chunks locally prior to network transmission.
* An asymmetric RSA Master Key pair can be used to escrow client keys. The public key encrypts the active backup encryption key alongside the manifest, enabling disaster recovery of backup volumes if a local node is destroyed.


* **Reference:** [PBS Encryption & Key Management](https://www.google.com/search?q=https://pbs.proxmox.com/docs/backup-client.html%23encryption).

### 6.2 Geolocated WAN Synchronization (Remotes & Sync Jobs)

```
+---------------------+-------------------------------+--------------------------------------------+
| Configuration Item  | Parameter Target              | Operational Function                       |
+---------------------+-------------------------------+--------------------------------------------+
| Remote Endpoint     | `pbs-alpha-remote`            | Connects PBS Beta to PBS Alpha API         |
| Pull Direction      | PBS Beta (Downstream Pull)    | Destination initiates sync over WAN       |
| Sync Interval       | Cron: `0 02 * * *` (Daily)    | Synchronises off-peak delta chunks         |
| Namespace Isolation | `ns/songketmail-core`         | Hierarchical segregation per tenant        |
+---------------------+-------------------------------+--------------------------------------------+

```

* **WAN-Optimised Pull Architecture:** The downstream regional backup appliance (Region Beta or Gamma) pulls newly written chunks from Region Alpha. The pull client matches existing SHA-256 chunk manifests and only transfers missing content over the WAN tunnel.
* **Namespaces:** Logical partitioning within a single PBS datastore allows tenant isolation and granular retention policies across multi-region boundaries.
* **Reference:** [PBS Remote Management & Sync Jobs](https://pbs.proxmox.com/docs/managing-remotes.html).

### 6.3 Anti-Ransomware, Integrity Verification, & Archival

#### A. Ransomware Defense & Datastore Hardening

* **Append-Only / Granular RBAC API Tokens:** PVE hypervisors access PBS using API tokens bound to restricted roles (`Datastore.Backup` or `Datastore.Audit`), preventing compromised hypervisors from pruning or destroying historical snapshots.
* **Decoupled Garbage Collection:** Two-phase deletion (phase 1: unmark index; phase 2: sweep sweep unreferenced chunks) prevents race conditions and accidental data purges.
* **Reference:** [PBS User Access & Permission Management](https://pbs.proxmox.com/docs/user-management.html).

#### B. Silent Data Corruption (Bit Rot) Detection

* **Automated Verification Jobs:** Background jobs compute read-verifications of chunk pools against manifest checksums (`index.json`) to detect underlying bit rot or silent media degradation.
* **Reference:** [PBS Verification Jobs](https://www.google.com/search?q=https://pbs.proxmox.com/docs/maintenance.html%23verification).

#### C. Enterprise Tape Backup Integration (LTO)

* **Native Rust Tape Subsystem:** Direct support for Linear Tape-Open (LTO-5 through LTO-9) devices without third-party backup layers.
* **Library Management (`pmtx`):** Integrated autoloader control tool (`pmtx`) handles cartridge swapping, media-set allocation, and hardware encryption workflows.
* **Reference:** [PBS Tape Backup & Autoloader Integration](https://pbs.proxmox.com/docs/tape-backup.html).

### 6.4 Low RTO/RPO Disaster Recovery & Restore Stack

#### A. Granular Single-File Level Recovery

* **Single-File Restore Engine:** Mounts VM image file allocation tables safely within a micro-VM/FUSE environment directly through the PVE GUI/CLI, allowing individual file extraction without restoring entire storage volumes.
* **Reference:** [PBS File-Level Restore](https://www.google.com/search?q=https://pbs.proxmox.com/docs/backup-client.html%23restore-single-files).

#### B. Live-Restore (Instant VM Boot)

* **Underlying Mechanism:** When triggered via `qmrestore --live-restore 1`, QEMU boots the guest immediately while blocks are continuously streamed in the background.
* **On-Demand Prioritisation:** If the guest operating system requests an uncopied disk sector, the live-restore block driver prioritises that request in real-time to avoid boot stalls, enabling low RTO recoveries for large database servers.
* **Reference:** [Proxmox VE Live-Restore Feature Documentation](https://pve.proxmox.com/pve-docs/chapter-vzdump.html#_live_restore).

---

## 📚 Reference Architecture Documentation Index

1. **Hypervisor & Cluster Management:** [Proxmox VE Official Documentation](https://pve.proxmox.com/pve-docs/)
2. **Enterprise Backup Systems:** [Proxmox Backup Server Documentation](https://pbs.proxmox.com/docs/)
3. **Enterprise Storage Fabric:** [Ceph Upstream Documentation](https://docs.ceph.com/en/latest/)
4. **CentOS Storage SIG:** [CentOS SIG Ceph Packaging](https://sigs.centos.org/storage/)
5. **Database High Availability:** [Percona Distribution for PostgreSQL (Patroni HA)](https://www.google.com/search?q=https://docs.percona.com/postgresql/index.html)
6. **Network Security & Dynamic Routing:** [FRRouting (FRR) User Manual](https://docs.frrouting.org/en/latest/)
7. **Security Baseline & WAF:** [BunkerWeb WAF Documentation](https://docs.bunkerweb.io/) & [OpenSCAP Compliance Suite](https://www.open-scap.org/)

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-14*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

---
okf_version: 0.1
type: documentation
title: "Geolocated Regional Data Center Design"
description: "A comprehensive technical design for a geodistributed multi-region Proxmox and Ceph infrastructure targeting high availability and regional redundancy."
resource: "file:///docs/regional-design-proxmox-ceph.md"
timestamp: 2026-08-14T12:00:00Z
topics: [proxmox, ceph, regional, geolocation, almalinux, architecture]
---

# 🌐 Geolocated Regional Data Center Design

This document details the technical design, architectural patterns, and systemic improvements for the **SongketMail Regional Data Center Infrastructure**. To achieve absolute business continuity, fault tolerance, and data sovereignty, the design specifies a geodistributed multi-region topology spanning at least three distinct regions with active-active and active-passive geolocation redundancy.

---

## 🗺️ 1. Multi-Region Geodistributed Topology

The core architecture consists of three geographically isolated regional data centers communicating over secure, dedicated low-latency Wide Area Networks (WAN) utilizing IPsec VPN meshes or dark fiber links.

```
                  +-----------------------------------+
                  |      GEOLOCATED WAN BACKBONE      |
                  +-----------------+-----------------+
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
+-----------v-----------+   +-------v-------+   +-----------v-----------+
|     REGION ALPHA      |   |  REGION BETA  |   |     REGION GAMMA      |
|  (Primary Production)  |   | (Secondary/DR) |   | (Geo-Redundant/Edge)  |
|                       |   |               |   |                       |
|  3x Proxmox HCI Nodes |   | 3x PVE Nodes  |   | 3x Proxmox HCI Nodes  |
|  3x AlmaLinux Ceph    |   | 3x AlmaCeph   |   | 3x AlmaLinux Ceph     |
+-----------------------+   +---------------+   +-----------------------+
```

### 1.1 Regional Characteristics
*   **Region Alpha (Primary Production)**: Hosts the primary active mail service instances, webmail gateways, and real-time transaction stores.
*   **Region Beta (Secondary / Disaster Recovery)**: Hosts mirrored virtual environments and acts as the immediate failover site for Region Alpha with hot-standby services.
*   **Region Gamma (Geo-Redundant / Edge Archive)**: Functions as a third quorum voter and offsite cold archival storage, preventing split-brain states and providing geolocated access for remote mail clients.

---

## 🏛️ 2. Generalized Node Architecture (Per Region)

Each regional node abstracts physical hardware dependencies into standardized, enterprise-grade compute, security, and storage building blocks.

```
+---------------------------------------------------------------------------------------------------+
|                                   GENERALIZED REGIONAL NODE                                       |
+---------------------------------------------------------------------------------------------------+
|  [ INGRESS ]                                                                                      |
|    Router / WAN CPE                                                                               |
|       |                                                                                           |
|    Active-Active GSLB & Next-Generation Enterprise Firewalls (HA NGFW)                            |
|       |                                                                                           |
|  [ CORE NETWORK ]                                                                                 |
|    Redundant Layer-3 Core Spine-Leaf Switches (10G/25G/100G Fabric)                               |
|       |                                                                                           |
|  [ COMPUTE LAYER ]                                                                                |
|    Min. 3x Multi-Core Enterprise Compute Hosts running Proxmox VE 9                               |
|    -> Running Local Hyper-Converged Ceph Cluster (Tier-1 Hot Storage)                             |
|       |                                                                                           |
|  [ STORAGE LAYER ]                                                                                |
|    Min. 3x Enterprise Storage Nodes running AlmaLinux 9.6                                         |
|    -> Running Independent External Ceph Cluster (Tier-2 Mailbox Object Storage)                   |
|       |                                                                                           |
|  [ COMPANION SERVICES ]                                                                           |
|    - High-Capacity Dedicated Backup Server (PBS) Appliance                                        |
|    - Specialized AI Inference Accelerator Nodes (GPU-backed)                                      |
+---------------------------------------------------------------------------------------------------+
```

### 2.1 Hardware Sizing & Refinement
*   **Compute Nodes**: Enterprise multi-core processor hosts (AMD/Intel) running Proxmox VE 9, equipped with redundant power supplies, multi-port high-speed NICs, and enterprise SAS/NVMe drives.
*   **Security Gateway**: Next-Generation Enterprise Firewalls (NGFW) in High-Availability active-passive pairs, providing deep packet inspection, IDS/IPS, and IPsec VPN termination.
*   **Fabric Networking**: High-performance, dual-spine, multi-leaf switching topology running at 25 Gbps for intra-rack storage traffic and 10 Gbps for public access.
*   **Backup Server**: High-density dedicated backup appliance running Proxmox Backup Server (PBS) for localized incremental, deduplicated backups.
*   **AI Accelerators**: Dedicated compute servers outfitted with Enterprise GPU hardware for accelerated spam analysis, natural language model validation, and malware quarantine analytics.

---

## 🗄️ 3. Dual-Tier Ceph Storage Strategy

To balance low-latency virtual machine operational requirements with high-capacity object and mailbox storage, this design enforces a **dual-tier Ceph storage strategy**.

```
+---------------------------------------------------------------------------------------------------+
|                                      DUAL-TIER CEPH FLOW                                          |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [ TIER 1: PVE Local Hyper-Converged Ceph ] <---> Low-Latency VM Boot Disks & System Volumes      |
|    - Managed natively via Proxmox VE (pveceph)                                                    |
|    - 3x Nodes minimum with local enterprise SSDs                                                  |
|                                                                                                   |
|  [ TIER 2: AlmaLinux Independent Ceph ]     <---> High-Capacity Mailbox Objects, RGW & S3 Stores    |
|    - Running on external AlmaLinux 9.6 nodes via cephadm                                          |
|    - Packages sourced from CentOS Storage SIG repositories                                        |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

### 3.1 Tier 1: Local Hyper-Converged Ceph (Proxmox-Managed)
*   **Deployment**: Bootstrapped natively on the Proxmox VE 9 compute cluster according to the [Proxmox VE Ceph Guide](https://pve.proxmox.com/pve-docs/chapter-pveceph.html#chapter_pveceph) and [Hyper-converged Infrastructure Wiki](https://pve.proxmox.com/wiki/Hyper-converged_Infrastructure).
*   **Use Case**: Holds high-IOPS VM boot drives, transactional database writes, and active state runtimes.
*   **Benefits**: Lowest latency path, direct integration with Proxmox VE High Availability (HA) stack, and simple GUI orchestration.

### 3.2 Tier 2: External Independent Ceph (AlmaLinux-Managed)
*   **Deployment**: Running on dedicated AlmaLinux 9.6 minimal nodes managed via `cephadm` and containerized Daemons.
*   **Repository Sourcing**: Sourced from the official **CentOS Storage SIG Repository** to guarantee stable enterprise-grade RedHat-compatible Ceph builds:
    ```bash
    # Enable the CentOS Storage SIG release package on AlmaLinux
    sudo dnf install -y centos-release-storage-common
    # Configure the Ceph repository release target (e.g., Reef or Tentacle)
    sudo dnf install -y centos-release-ceph-reef
    ```
    For more details, reference [AlmaLinux Repository Guidelines](https://wiki.almalinux.org/repos/CentOS.html#storage-sig).
*   **Use Case**: Houses massive mailbox object blocks, Dovecot Obox S3 stores, and cold/compressed document vaults.
*   **Benefits**: Decoupled lifecycle management, hardware optimized purely for high-capacity drives (HDDs/NVMe mixes), and zero CPU/Memory contention with the hypervisor layer.

---

## 🔗 4. External Ceph Visibility Inside Proxmox VMs

One of the critical design questions for the SongketMail data center is: **Can the external Ceph cluster be seen and consumed directly by a Virtual Machine running inside Proxmox?**

The answer is **Yes**. Depending on security, performance, and operational constraints, there are three architectural approaches to make external Ceph visible inside virtual guests.

```
+---------------------------------------------------------------------------------------------------+
|                                 VM-TO-CEPH VISIBILITY APPROACHES                                  |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  APPROACH A: Hypervisor-Mediated Virtualization (Recommended for VM System Disks)                 |
|    External Ceph Pool  --->  Proxmox VE Storage  --->  VirtIO Block (Raw/VMDK)  --->  Guest VM     |
|                                                                                                   |
|  APPROACH B: Guest-Native Direct Storage Protocol (Recommended for High-Performance Mail Stores)  |
|    External Ceph Cluster (RBD / CephFS)  =====[ Dedicated Storage VLAN ]=====>  Guest Client OS    |
|                                                                                                   |
|  APPROACH C: S3-Compatible Object Storage Gateway (Recommended for Decoupled Web Applications)     |
|    External Ceph RGW (S3 API)  --------------[ Standard TCP/IP Network ]------------->  Guest App  |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

### Approach A: Hypervisor-Mediated Virtualization (Storage.cfg)
*   **How it works**: Proxmox VE maps the external Ceph cluster as a native storage pool in `/etc/pve/storage.cfg` using `librbd` (admin or client keyrings). PVE then provisions virtual disks (`.raw` volumes) on this pool and presents them to the virtual machine as standard **VirtIO Block** or **SCSI** controllers.
*   **VM Visibility**: The VM sees a standard physical-like block device (e.g., `/dev/vdb` or `/dev/sdb`) and remains completely unaware that the underlying storage is Ceph.
*   **Pros**: Supports Proxmox snapshots, thin provisioning, VM live-migration across hypervisors, and simple central backup policies.
*   **Cons**: Introduces minor CPU overhead at the hypervisor mapping layer.

### Approach B: Guest-Native Direct Storage Protocol Access
*   **How it works**: The virtual machine is configured with a dedicated network interface mapped directly to the Ceph Public network segment (e.g., via VLAN tag). Inside the guest operating system, Ceph client packages are installed. The VM is granted its own unique Ceph keyring (`client.vm-mailstore`) with restrictive pool privileges.
*   **VM Visibility**:
    - **RADOS Block Device (RBD)**: The guest kernel maps the RBD block directly:
      ```bash
      sudo rbd map mypool/vm-mail-volume --name client.vm-mailstore
      ```
      This exposes the device directly as `/dev/rbd0` inside the VM.
    - **CephFS POSIX Mount**: The guest mounts CephFS using the kernel driver:
      ```bash
      sudo mount -t ceph 10.10.20.11:6789:/ /mnt/mailshares -o name=vm-mailstore,secretfile=/etc/ceph/vm-mailstore.key
      ```
*   **Pros**: Ultimate bare-metal read/write performance; bypasses any hypervisor virtual disk layer bottlenecks.
*   **Cons**: Increased administrative complexity; VMs must manage storage credentials; limits Proxmox-native snapshots/live migrations for that volume.

### Approach C: S3-Compatible Object Storage Gateway (Ceph RGW)
*   **How it works**: The external Ceph cluster runs **RADOS Gateway (RGW)** daemons, exposing an S3-compatible HTTP/HTTPS endpoint. Virtual machines communicate with the storage cluster purely through RESTful web requests (S3 APIs).
*   **VM Visibility**: The VM does not mount any block or filesystem storage. Instead, local application services (such as Dovecot Obox or Nextcloud) query and read/write object files directly using standard S3 client libraries.
*   **Pros**: Complete network decoupled architecture; no client storage drivers needed in the guest; easily scales across different regions.
*   **Cons**: Best suited for object/file-blob payloads (e.g., raw email files), not suitable for system boot disks.

---

## 🚀 5. Architectural Improvements & Hardening Recommendations

To optimize this design for the SongketMail production deployment, we suggest implementing the following improvements:

1.  **Chrony Geolocation Synchronization**: Ensure all regional clusters synchronize their system clocks using geographically localized, high-stratum NTP servers. Ceph relies on accurate timestamps; any clock drift exceeding 0.05 seconds between OSDs can trigger clock skew alerts and corrupt transaction order.
2.  **IPsec Low-Latency MTU Tuning**: Since replication and WAN mirroring packets cross geo-regions via IPsec tunnels, adjust the MTU of Ceph-bound virtual interfaces to **1400 bytes** to prevent packet fragmentation at security gateways.
3.  **Strict Storage Network Ring Fencing**: Do not expose the Ceph Cluster Network or public storage ports on any internet-facing router. All storage replication must transit through isolated IPsec or dedicated MPLS circuits.
4.  **LACP Bond Interfaces on Compute Nodes**: Implement 802.3ad LACP bonding (e.g., `bond0` consisting of dual 25G SFP28 interfaces) to guarantee both load balancing and failover capability for Tier-1 and Tier-2 storage operations.

---

## 💾 6. Multi-Region Backup Architecture via Proxmox Backup Server (PBS)

To satisfy the **Backup 3-2-1 rule** (3 copies of data, 2 different media, 1 offsite location) across a geodistributed topology, this design implements **Proxmox Backup Server (PBS)** as the core regional and cross-regional backup engine. PBS is a dedicated, enterprise-grade, client-server backup solution written in **Rust** to provide memory safety, high execution speed, and high resource efficiency without garbage collection overheads.

### 6.1 Core Architectural Pillars of PBS

#### A. Client-Server Architecture & High Performance (Rust-Powered)
PBS separates backup storage from virtual guests using a secure client-server framework. The entire stack is written in **Rust**, offering thread safety, memory safety, and high-performance throughput.
*   **Compression**: Backups utilize ultra-fast **Zstandard (ZSTD)** compression, capable of compressing several gigabytes of data per second with exceptional compression ratios, reducing storage footprints.
*   **Dirty Bitmaps Integration**: For virtual machines running in Proxmox VE, PBS interfaces directly with QEMU dirty bitmaps. This allows the hypervisor to track write operations in real-time, executing **incremental-only backups** by reading and transmitting only modified blocks since the previous run. This reduces backup windows from hours to seconds and lowers WAN utilization.

#### B. Chunk-Level Deduplication (Variable vs. Fixed Size)
To eliminate duplicate data produced by recurring daily backups and identical OS templates:
*   Incoming data streams are split into chunks. PBS supports both **fixed-sized chunking** (ideal for block devices and VM disks) and **variable-sized chunking** (ideal for file archives and directory backups).
*   Chunks are indexed by their **SHA-256 hash**, and only unique chunks are written to the datastore. Identical blocks across different virtual machines or historical snapshots reference the same physical chunks on disk. This results in massive storage cost reductions.

#### C. End-to-End Client-Side Encryption
To maintain absolute privacy and satisfy data sovereignty regulations in multi-tenant or leased environments, PBS enforces **client-side encryption**:
*   **Galois/Counter Mode (AES-256 GCM)**: Data is encrypted and authenticated *on the client-side* (within the Proxmox VE hypervisor) before it is transmitted over the network. If the backup server's physical storage or the WAN link is compromised, the payload remains unreadable.
*   **Key Management & Recovery**: Encryption keys are stored securely on the PVE host. Additionally, PVE can configure a <strong>Master Key</strong> (an RSA public/private key pair). The public key is stored alongside the backup and used to securely envelope the encryption key. If a node suffers a total hardware failure, administrators can recover the encryption key using the printed secret key or the private master key.

### 6.2 Geolocated WAN Synchronization (Remotes & Sync Jobs)

To ensure geographical redundancy and survival of a total site disaster:
1.  **Local Datastore Execution**: Each region schedules localized daily backups of active VMs, LXC containers, and critical host paths to its on-site PBS appliance (Tier-3 storage backed by local ZFS pools or SSD/HDD arrays).
2.  **Cross-Region Synchronization**:
    *   **Remotes Configuration**: PBS Beta is registered as a "Remote" target inside PBS Alpha.
    *   **Sync Jobs (Pull Strategy)**: On a recurring schedule, PBS Beta initiates a **Sync Job** to pull backup snapshots from PBS Alpha over the low-latency IPsec VPN mesh.
    *   **Incremental WAN Transfer**: Due to chunk-level hash comparison, only newly created unique chunks that do not exist in the destination datastore are transferred across the WAN. Syncing multi-terabyte virtual environments requires minimal bandwidth.
    *   **Namespaces**: PBS utilizes **Namespaces** to hierarchically group, isolate, and organize backups. Administrators can mirror namespaces across regions or migrate them cleanly without file collisions.

### 6.3 Anti-Ransomware, Integrity Verification, & Archival

#### A. Ransomware Defense & Datastore Hardening
*   **Access Control & Realms**: PBS integrates with multiple authentication realms including **Linux PAM** for system users, **OpenID Connect (OIDC)** for centralized Single Sign-On (SSO), and native **Proxmox Backup Server authentication**.
*   **Fine-Grained Permissions**: Strict Role-Based Access Control (RBAC) ensures backup clients (such as specific PVE clusters) are restricted to API tokens with write-only/append-only permissions (`PVETemplate` or `PBSBackup` roles) and are blocked from deleting historical backups.
*   **Garbage Collection (GC)**: Instead of immediate deletion, deleted snapshot references are unlinked, and actual disk space is freed later via scheduled Garbage Collection jobs, preventing accidental or malicious data loss.
*   **Immutable Datastores & Removable Media**: PBS supports removable datastores (e.g., hot-swap external storage) and namespace isolation, allowing physical air-gapping of critical email archives.

#### B. Silent Data Corruption (Bit Rot) Detection
*   PBS utilizes a **built-in SHA-256 checksumming verification engine**.
*   Within each backup snapshot, a manifest file (`index.json`) catalogs all chunk files with their sizes and cryptographic hashes.
*   Administrators can schedule automatic, recurring **Verification Jobs** to read chunks from the physical disks, recompute their SHA-256 hashes, and compare them against the manifest. This detects bit rot, disk degradation, or silent data corruption early.

#### C. Enterprise Tape Backup Integration (LTO)
For long-term cold archival and compliant offsite storage:
*   PBS includes a native, modern **Tape Backup System** written in Rust, replacing traditional legacy utilities.
*   **Hardware Encryption**: Supports standard Linear Tape-Open (LTO-5 or later) drives, media-set cataloging, and automated hardware tape encryption.
*   **Autoloader Support**: Interoperates with tape autoloaders and tape libraries via the specialized `pmtx` tool.
*   **LTO Barcode Generator**: Includes an integrated web-based LTO barcode generator to print standard label cartridges for physical vault inventory tracking.

### 6.4 Low RTO/RPO Disaster Recovery & Restore Stack

When a regional disaster hits Region Alpha, recovering services in Region Beta or Gamma must be near-instantaneous. PBS delivers via two critical mechanisms:
1.  **Granular File-Level Recovery**:
    *   Administrators can navigate the catalog file system of any VM or container backup directly from the Proxmox VE web interface.
    *   Single files, specific directories, or database tables can be restored in a flash without rebuilding or restoring the entire multi-gigabyte virtual disk.
    *   Interactive recovery shell allows recovery of individual files directly inside the running guest OS.
2.  **Live-Restore (Instant VM Recovery)**:
    *   To achieve near-zero **Recovery Time Objective (RTO)**, Proxmox VE can start a virtual machine *immediately* after triggering the restore job.
    *   The VM boots instantly, and QEMU streams required sectors from the PBS server in real-time as the operating system requests them.
    *   The remaining disk image is copied in the background. If a sector has not been copied yet but is read by the VM, it gets prioritized and fetched instantly. Users experience zero interruption, even for massive email databases.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-14*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

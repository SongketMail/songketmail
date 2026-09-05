---
okf_version: "0.1"
type: "documentation"
title: "Persistent Volume (PV) Storage Server Setup & RKE2 Storage Architecture"
description: "Detailed operational guide and architectural specification for setting up Kubernetes Persistent Volume (PV) storage on RKE2 fabrics, covering PVE-Ceph CSI integration, NFS storage server provisioning, and Local Path provisioners across Debian, Ubuntu, AlmaLinux, and Rocky Linux environments."
resource: "file:///docs/rke2-pv-storage-setup.md"
timestamp: 2026-08-25T12:00:00Z
topics: [kubernetes, rke2, ceph, nfs, pv, storage, proxmox, songketmail]
---

# Persistent Volume (PV) Storage Server Setup & RKE2 Storage Architecture

---

## 🗺️ RKE2 Persistent Volume (PV) Storage Architecture

With the operational requirement to establish highly available (HA), resilient, and horizontally scalable Day 2 storage operations for RKE2 fabrics, selecting the correct Persistent Volume (PV) provisioner is critical. By evaluating NFS, Ceph CSI, and Local Path provisioning against multi-node resiliency constraints, this document defines the deployment topologies across both Debian/Ubuntu and AlmaLinux/RockyLinux ecosystems.

The following architectural diagram illustrates the Proxmox VE hypervisor cluster hosting virtualized RKE2 master and worker nodes, backed by shared Ceph SDS and NFS persistent storage fabrics:

```text
+----------------------------------------------------------------------------------------------------+
|                               PROXMOX VE HYPER-CONVERGED CLUSTER                                   |
|                                                                                                    |
|  +---------------------------+   +---------------------------+   +---------------------------+  |
|  |       PROXMOX NODE 1      |   |       PROXMOX NODE 2      |   |       PROXMOX NODE 3      |  |
|  | +-----------------------+ |   | +-----------------------+ |   | +-----------------------+ |  |
|  | |     k8s Master VM     | |   | |     k8s Master VM     | |   | |     k8s Master VM     | |  |
|  | +-----------------------+ |   | +-----------------------+ |   | +-----------------------+ |  |
|  | |     k8s Worker VM     | |   | |     k8s Worker VM     | |   | |     k8s Worker VM     | |  |
|  | | [pod] [pod] [pod] [pod]| |   | | [pod] [pod] [pod] [pod]| |   | | [pod] [pod] [pod] [pod]| |  |
|  | +-----------┬-----------+ |   | +-----------┬-----------+ |   | +-----------┬-----------+ |  |
|  +-------------│-------------+   +-------------│-------------+   +-------------│-------------+  |
+----------------│-------------------------------│-------------------------------│-------------------+
                 │                               │                               │
                 └───────────────────────────────┼───────────────────────────────┘
                                                 │
                                                 ▼
+----------------------------------------------------------------------------------------------------+
|                                 DISTRIBUTED STORAGE LAYER (CEPH / NFS)                             |
|  +----------------------------------------------------------------------------------------------+  |
|  | RADOS Block Device (RBD) Pools  |  CephFS Shared File System  |  NFS Storage Server Shares    |  |
|  +----------------------------------------------------------------------------------------------+  |
+----------------------------------------------------------------------------------------------------+
```

---

## 💾 1. External Ceph CSI Storage Provisioning (RBD) & PVE-Ceph Integration

By leveraging a Proxmox Virtual Environment (PVE) Hyper-Converged Infrastructure (HCI) with integrated Ceph, the storage layer is decoupled from the compute nodes whilst maintaining block-level performance and multi-node redundancy. The Ceph Container Storage Interface (CSI) provides dynamic provisioning of RADOS Block Devices (RBD) and CephFS volumes directly to RKE2 pods.

### OS Family Dependencies & Configuration

For external Ceph connectivity, the RKE2 worker nodes require native Ceph client utilities to mount RBD and CephFS targets.

#### Debian/Ubuntu Family (Debian 12, Ubuntu 24.04 / 26.04 LTS)

```bash
# Install Ceph common utilities
sudo apt-get update && sudo apt-get install -y ceph-common

# Ensure kernel RBD module is loaded automatically on boot
sudo modprobe rbd
echo "rbd" | sudo tee /etc/modules-load.d/rbd.conf
```

#### AlmaLinux/RockyLinux Family (AlmaLinux 9.6, Rocky Linux 9)

```bash
# Enable CentOS Storage SIG repository for Ceph packages
sudo dnf install -y centos-release-ceph-reef epel-release
sudo dnf install -y ceph-common

# Ensure kernel RBD module is loaded automatically on boot
sudo modprobe rbd
echo "rbd" | sudo tee /etc/modules-load.d/rbd.conf
```

### PVE-Ceph Integration via Helm

By configuring the `ceph-csi` Helm chart within RKE2, dynamic volume provisioning is achieved against the Proxmox Ceph cluster.

#### Helm Chart Values Configuration (`ceph-csi-values.yaml`)

```yaml
# ceph-csi-values.yaml
csiConfig:
  - clusterID: "pve-ceph-cluster"
    monitors:
      - "10.0.10.11:6789"
      - "10.0.10.12:6789"
      - "10.0.10.13:6789"
storageClass:
  create: true
  name: ceph-rbd
  clusterID: "pve-ceph-cluster"
  pool: "k8s-pool"
  imageFeatures: layering
  reclaimPolicy: Retain
  allowVolumeExpansion: true
```

#### Kubernetes StorageClass & PVC Manifests

```yaml
# ceph-rbd-sc.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ceph-rbd
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: rbd.csi.ceph.com
parameters:
  clusterID: "pve-ceph-cluster"
  pool: "k8s-pool"
  imageFormat: "2"
  imageFeatures: layering
  csi.storage.k8s.io/provisioner-secret-name: csi-rbd-secret
  csi.storage.k8s.io/provisioner-secret-namespace: kube-system
  csi.storage.k8s.io/node-stage-secret-name: csi-rbd-secret
  csi.storage.k8s.io/node-stage-secret-namespace: kube-system
  csi.storage.k8s.io/controller-expand-secret-name: csi-rbd-secret
  csi.storage.k8s.io/controller-expand-secret-namespace: kube-system
reclaimPolicy: Retain
allowVolumeExpansion: true
mountOptions:
  - discard
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: songketmail-db-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ceph-rbd
  resources:
    requests:
      storage: 100Gi
```

* **Use Case:** Highly available databases (PostgreSQL/Patroni), vector databases (pg_vector), and stateful microservices requiring sub-millisecond IOPS and absolute reduction of MTTD/MTTR.
* **Verdict:** The primary choice for Day 2 operations requiring sovereign, distributed HA block storage without vendor lock-in.

---

## 📁 2. NFS Storage Server Provisioning

Through the deployment of the NFS subdir external provisioner, standard NFS exports are dynamically carved into Kubernetes PVs. While lacking the block-level performance and self-healing HA characteristics of Ceph, NFS provides a simplistic approach for shared, ReadWriteMany (RWX) storage arrays.

### OS Family Dependencies & Configuration

#### Server-Side Export Configuration (`10.0.20.50`)

##### Debian/Ubuntu Family

```bash
sudo apt-get update && sudo apt-get install -y nfs-kernel-server

# Prepare dynamic provisioner and static export paths
sudo mkdir -p /mnt/k8s_storage /mnt/k8s_static_pv
sudo chown -R nobody:nogroup /mnt/k8s_storage
sudo chmod 755 /mnt/k8s_storage

# Configure SongketMail application user permissions (UID:GID 2001:2001)
sudo chown -R 2001:2001 /mnt/k8s_static_pv
sudo chmod 775 /mnt/k8s_static_pv

# Export paths in /etc/exports
echo "/mnt/k8s_storage 10.0.20.0/24(rw,sync,no_subtree_check,root_squash)" | sudo tee -a /etc/exports
echo "/mnt/k8s_static_pv 10.0.20.0/24(rw,sync,no_subtree_check,root_squash)" | sudo tee -a /etc/exports

sudo exportfs -rav
sudo systemctl enable --now nfs-kernel-server
```

##### AlmaLinux/RockyLinux Family

```bash
sudo dnf install -y nfs-utils

# Firewalld configurations (when host acts as NFS server)
sudo firewall-cmd --permanent --add-service=nfs
sudo firewall-cmd --permanent --add-service=mountd
sudo firewall-cmd --permanent --add-service=rpc-bind
sudo firewall-cmd --reload

# Prepare directories and export permissions
sudo mkdir -p /mnt/k8s_storage /mnt/k8s_static_pv
sudo chown -R nobody:nobody /mnt/k8s_storage
sudo chmod 755 /mnt/k8s_storage

sudo chown -R 2001:2001 /mnt/k8s_static_pv
sudo chmod 775 /mnt/k8s_static_pv

echo "/mnt/k8s_storage 10.0.20.0/24(rw,sync,no_subtree_check,root_squash)" | sudo tee -a /etc/exports
echo "/mnt/k8s_static_pv 10.0.20.0/24(rw,sync,no_subtree_check,root_squash)" | sudo tee -a /etc/exports

sudo exportfs -rav
sudo systemctl enable --now nfs-server
```

#### RKE2 Worker Client Prerequisites

* **Debian/Ubuntu Family:**
```bash
sudo apt-get update && sudo apt-get install -y nfs-common
```

* **AlmaLinux/RockyLinux Family:**
```bash
sudo dnf install -y nfs-utils
```

### RKE2 NFS Provisioner Configuration

Using the `nfs-subdir-external-provisioner` Helm chart:

```yaml
# nfs-values.yaml
nfs:
  server: 10.0.20.50
  path: /mnt/k8s_storage
storageClass:
  name: nfs-client
  defaultClass: false
  archiveOnDelete: false
```

#### Helm Installation Command

```bash
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm install nfs-subdir-external-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  -f nfs-values.yaml \
  --namespace kube-system
```

* **Use Case:** Shared configuration files, web server static assets, and legacy application shared directories requiring RWX access modes across pods.
* **Verdict:** Suitable for low-IOPS, non-critical data sharing. Not recommended for database workloads due to locking and latency overheads.

---

## ⚡ 3. Static PV Binding & Local Path Provisioner

By utilising the underlying disk infrastructure of physical compute nodes, the Local Path Provisioner provides the highest raw IOPS possible. RKE2 ships with Rancher's Local Path Provisioner by default. However, this binds a pod to a specific node; if that node fails, the pod cannot be rescheduled to a different node with its data intact unless application-level replication (e.g., Patroni, Galera) is in place.

### Configuration (OS Agnostic)

The provisioner leverages host directories (typically `/var/lib/rancher/rke2/storage`). No specific OS package installations are required beyond standard disk formatting (XFS/ext4) and mounting.

#### ConfigMap Override (`local-path-config.yaml`)

```yaml
# local-path-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: local-path-config
  namespace: kube-system
data:
  config.json: |-
    {
      "nodePathMap":[
      {
        "node":"DEFAULT_PATH_FOR_NON_LISTED_NODES",
        "paths":["/opt/local-path-provisioner"]
      }
      ]
    }
```

#### Static Persistent Volume & Claim Manifests (`rke2-static-pv.yaml`)

```yaml
# rke2-static-pv.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: static-nfs-pv
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  mountOptions:
    - nconnect=8
  nfs:
    server: 10.0.20.50
    path: /mnt/k8s_static_pv
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: static-nfs-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: ""
  volumeName: static-nfs-pv
  resources:
    requests:
      storage: 100Gi
```

* **Use Case:** Highly specific workloads that handle their own replication at the application layer (e.g., Elasticsearch clusters, Kafka brokers, Patroni-managed PostgreSQL) where bare-metal NVMe performance is mandatory.
* **Verdict:** Deploy strictly when the application architecture is designed for "shared-nothing" resilience. Unsuitable for standard single-instance stateful deployments due to single-point-of-failure (SPOF) risks at the node level.

---

## ⚖️ Storage Decision Matrix & Architectural Comparison

| Provisioner Type | Primary Access Mode | Resiliency & HA Model | Target Workloads | OS Dependencies | Performance Profile |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ceph CSI (RBD)** | `ReadWriteOnce` (RWO) | Multi-node OSD replication, dynamic failover | PostgreSQL / Patroni, Vector DB, Stateful Apps | `ceph-common`, `rbd` module | High IOPS, Low Latency, Distributed HA |
| **Ceph CSI (CephFS)**| `ReadWriteMany` (RWX) | Multi-MDS HA filesystem, distributed replication | Shared media streams, attachments | `ceph-common` | Medium-High IOPS, Shared File System |
| **NFS External** | `ReadWriteMany` (RWX) | Single NFS server (SPOF unless NAS/SAN appliance) | Shared config files, static assets | `nfs-common` / `nfs-utils` | Low-Medium IOPS, File Locking Bottleneck |
| **Local Path** | `ReadWriteOnce` (RWO) | Bound to single host disk (No node HA) | Kafka, Elasticsearch, Shared-Nothing DB | None (standard filesystem mount) | Maximum Raw NVMe IOPS, Sub-millisecond |

---

*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-25*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

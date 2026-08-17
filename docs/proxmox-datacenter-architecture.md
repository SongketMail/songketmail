---
okf_version: 0.1
type: documentation
title: "Proxmox VE Enterprise Datacentre Architecture Specification"
description: "A comprehensive technical design for a multi-tier Proxmox VE hypervisor cluster and Ceph software-defined storage integrated with SongketMail infra."
resource: "file:///docs/proxmox-datacenter-architecture.md"
timestamp: 2026-08-25T12:00:00Z
topics: [proxmox, ceph, architecture, songketmail, datacentre, security]
---

# Proxmox VE Enterprise Datacentre Infrastructure Specification

---

## 🗺️ System Topology & Data Flow

```
+----------------------------------------------------------------------------------------------------+
|                                    EXTERNAL SYSTEMS INTEGRATION                                    |
|  +--------------------+  +--------------------+  +---------------------+  +---------------------+  |
|  | Inbound / Outbound |  | Threat Intel &     |  | Domain Identity &   |  | Cross-Sector IOC   |  |
|  | SMTP Mail Streams  |  | Reputation Feeds   |  | PKI Registries      |  | & Incident Feeds    |  |
|  +---------┬----------+  +---------┬----------+  +----------┬----------+  +----------┬----------+  |
+------------│-----------------------│------------------------│------------------------│-------------+
             └───────────────────────┼────────────────────────┴────────────────────────┘
                                     │ (mTLS / Encrypted Ingress Stream)
                                     ▼
+----------------------------------------------------------------------------------------------------+
|                                   PERIMETER SECURITY & INGRESS                                     |
|                       [ Boundary Next-Generation Firewall (NGFW) / IPS ]                           |
|                       [ Redundant Layer 4 / Layer 7 Load Balancers ]                               |
+--------------------------------------------┬-------------------------------------------------------+
                                             │
                                             ▼
+----------------------------------------------------------------------------------------------------+
|                               PRIMARY PRODUCTION DATACENTRE                                        |
|                                                                                                    |
|  +-------------------------------------+          +---------------------------------------------+  |
|  | 100GbE High-Throughput Data Plane   |          | 10GbE Out-of-Band Management Fabric         |  |
|  | (East-West VM/LXC & Ceph Corosync)  |          | (Proxmox Cluster API, BMC/IPMI, Telemetry)  |  |
|  +-------------------------------------+          +---------------------------------------------+  |
|                                                                                                    |
|  +--------------------------- PROXMOX VE HYPERVISOR CLUSTER (PVE) ------------------------------+  |
|  |                                                                                              |  |
|  |  +---------------------------+  +---------------------------+  +--------------------------+  |  |
|  |  |   AI / GPU Compute Tier   |  |     Application Tier      |  |    Database / Data Tier  |  |  |
|  |  | (4x High-Density Nodes)   |  | (4x PVE Virtualisation)   |  | (3x Clustered HA Nodes)  |  |  |
|  |  |  - PCIe GPU Passthrough   |  |  - Mail Routing Proxies   |  |  - Clustered Relational  |  |  |
|  |  |  - Deep NLP & BEC Models  |  |  - LXC Microservices / VM |  |  - Quarantine Metadata   |  |  |
|  |  |  - Embedding / Vector DB  |  |  - Message Queues/Spool   |  |  - Audit & Policy Logs   |  |  |
|  |  |  - Attachment Sandboxing  |  |  - Web Management GUI/API |  |  - State Persistence     |  |  |
|  |  +-------------┬-------------+  +-------------┬-------------+  +------------┬-------------+  |  |
|  +----------------│------------------------------│-----------------------------│----------------+  |
|                   │                              │                             │                   |
|  +----------------▼------------------------------▼-----------------------------▼----------------+  |
|  |                     HYPERCONVERGED / SOFTWARE-DEFINED STORAGE (CEPH SDS)                     |  |
|  |   [ High-IOPS Vector/Model Pool ]    [ VM / LXC Disk & Spool Pool ] [ DB Persistence & Staging ] |  |
|  +-----------------------------------------------------------------------------┬----------------+  |
|                                                                                │                   |
|  +-------------------------------- DATACENTRE INFRASTRUCTURE -----------------│-----------------+  |
|  |  [ N+1 Modular UPS Fabric ]     [ Proxmox Backup Server (PBS) ]    [ Security Monitoring ]   |  |
|  +-----------------------------------------------------------------------------│-----------------+  |
+--------------------------------------------------------------------------------│-------------------+
                                                                                 │ Dedicated WAN Link
                                                                                 ▼ (Storage Mirror + PBS)
+----------------------------------------------------------------------------------------------------+
|                                  DISASTER RECOVERY (DR) DATACENTRE                                 |
|  [ 2x AI Compute Nodes ]   [ 2x PVE App Nodes ]     [ 1x DB Replica Node ]    [ Ceph Mirror Pool ] |
+----------------------------------------------------------------------------------------------------+
```

---

## 📥 1. Ingress & External Integration Perimeter

* **Inbound & Outbound SMTP Mail Streams:** Ingests real-time ESMTP connection streams, envelope metadata, and raw multi-part MIME payloads across edge Mail Transfer Agents (MTAs). Captures transport-layer telemetry, connection pacing, sender IP addresses, and real-time handshake properties.
* **Threat Intelligence & Network Reputation Feeds:** Executes synchronous lookups against DNS-based Blackhole Lists (DNSBL/RBL) and custom real-time blocklists. Resolves Forward-Confirmed Reverse DNS (FCrDNS / PTR verification) and correlates Autonomous System Numbers (ASN), BGP route origins, and GeoIP datasets to identify suspicious relays, open proxies, and bulletproof hosting environments.
* **Domain Identity & PKI Cryptographic Registries:** Queries and validates domain-level authentication frameworks including SPF record flattening/macro evaluation, DKIM cryptographic signature verification (RSA/Ed25519), DMARC policy alignment, and ARC (Authenticated Received Chain) validation. Inspects TLS certificate chains, Certificate Authority (CA) trust hierarchies, CRL/OCSP stapling status, Certificate Transparency (CT) log history, and cryptographic validation via DANE (TLSA) and MTA-STS.
* **Cross-Sector IOC & Regulatory Data Feeds:** Pulls automated Indicators of Compromise (IOCs), malicious URL blacklists, known phishing hashes, and compliance blacklists via authenticated REST/gRPC interfaces secured with mutual TLS (mTLS 1.3).

---

## 🛡️ 2. Perimeter Security & Traffic Routing

* **Boundary Firewall & Threat Mitigation:** Upstream edge traffic is filtered through redundant Next-Generation Firewalls (NGFW) executing stateful packet filtering, Intrusion Prevention (IPS), and DDoS volumetric rate limiting.
* **Load Balancing & TLS Termination:** Redundant Layer 4 / Layer 7 Load Balancers distribute ingress traffic evenly across upstream gateway proxies, managing external TLS termination, rate control, and health probing before routing to internal aggregation switches.

---

## 🔌 3. Dual-Plane Network Fabric

* **100GbE High-Throughput Data Plane:** High-bandwidth, non-blocking switching fabric dedicated entirely to Proxmox VE VirtIO network bridges, Ceph public and cluster networks, inter-VM traffic, and high-frequency model inference transfers.
* **10GbE Out-of-Band (OOB) Management Plane:** An isolated physical and logical network reserved for Proxmox Corosync cluster communication, IPMI/iDRAC bare-metal orchestration, monitoring telemetry, and web GUI/API administrative access.

---

## ⚙️ 4. Proxmox VE Hypervisor Compute Fabric

* **AI Accelerator Compute Tier (4 PVE Nodes):**
  * *Hardware Configuration:* Dual enterprise multi-core CPUs, 8x High-Performance Datacentre GPUs, 2TB System RAM per node.
  * *Workload Responsibilities:* High-density Proxmox VE compute nodes utilising direct PCIe GPU Passthrough and vGPU configurations to execute real-time text tokenisation, dense vector embedding generation, NLP-based Business Email Compromise (BEC) detection, deep semantic scoring, attachment heuristic unpacking, and sandboxed dynamic analysis.

* **Application Services Tier (4 PVE Nodes):**
  * *Hardware Configuration:* Dual multi-core CPUs, 1TB System RAM per node.
  * *Workload Responsibilities:* Clustered Proxmox KVM Virtual Machines and unprivileged LXC Containers hosting core API gateways, SMTP protocol engines, message queue brokers (e.g., Kafka/RabbitMQ), mail policy services, and platform management interfaces.

* **Database & Stateful Data Tier (3 PVE Nodes):**
  * *Hardware Configuration:* Dual multi-core CPUs, 512GB System RAM per node.
  * *Workload Responsibilities:* Dedicated virtualised or bare-metal database instances running high-availability relational engines (e.g., PostgreSQL with Patroni) and distributed metadata stores for message disposition states, quarantine indices, system configuration matrices, and forensic audit logs.

---

## 🗄️ 5. Hyperconverged / Software-Defined Storage (Ceph SDS)

* **Integrated Ceph Cluster:** Managed directly via Proxmox VE to provide unified, distributed, self-healing block and file storage across all hypervisor nodes without single points of failure.
* **High-Performance AI Model & Vector Pool:** NVMe-backed low-latency Ceph RBD (RADOS Block Device) pools provisioned for rapid loading of neural network checkpoints, vector indices, and real-time inference scratchpads.
* **VM & LXC Storage Pool (RBD / CephFS):** Resilient storage pools providing dynamic, thin-provisioned virtual disk images (RAW/QCOW2 over RBD) and shared storage (CephFS) for container states, queue spooling, and application caches.
* **Database Persistence & Staging Pool:** Dedicated low-latency pools handling relational database write-ahead logs (WAL), transactional tablespaces, and encrypted quarantine staging for suspicious payloads.

---

## 🏢 6. Datacentre Supporting Infrastructure

* **Uninterruptible Power Supply (UPS):** N+1 redundant modular power architecture ensuring uninterrupted operation and clean power distribution across all compute, storage, and networking chassis.
* **Proxmox Backup Server (PBS):** Enterprise backup integration offering client-side deduplication, incremental snapshotting, Zstandard compression, and cryptographic encryption for VMs and LXC containers.
* **Integrated Security Monitoring:** Centrally collects hypervisor syslog telemetry, Proxmox task events, network flow records, and system health metrics for comprehensive observability and automated root cause analysis.

---

## 🔄 7. Disaster Recovery (DR) & Site Continuity

* **Warm-Standby Target Footprint:** Sized at half capacity (2x AI Nodes, 2x Application Nodes, 1x Database Replica) running a secondary Proxmox VE cluster to sustain essential security filtering and mail processing during a primary datacentre outage.
* **Cross-Site Replication Fabric:** Employs asynchronous Ceph RBD Mirroring and scheduled Proxmox Backup Server (PBS) remote-sync jobs over dedicated WAN links, complemented by database streaming replication to maintain minimal Recovery Point Objectives (RPO) and low Recovery Time Objectives (RTO).

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-25*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

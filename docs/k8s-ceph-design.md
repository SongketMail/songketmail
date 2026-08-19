---
okf_version: 0.1
type: documentation
title: "Enterprise Kubernetes & Distributed Ceph Architecture Specification"
description: "A comprehensive technical specification for SongketMail Kubernetes compute fabric (RKE2 & K3s) integrated with distributed software-defined storage (Ceph)."
resource: "file:///docs/k8s-ceph-design.md"
timestamp: 2026-08-20T12:00:00Z
topics: [kubernetes, rke2, k3s, ceph, architecture, container, songketmail]
---

# Enterprise Kubernetes & Distributed Ceph Architecture Specification

---

## 🗺️ System Topology & Data Flow

The following architectural diagram illustrates the end-to-end data flow, ingress traffic control, network segmentation, compute node tiering, distributed Ceph storage pools, and disaster recovery replication links for the SongketMail Enterprise Kubernetes environment.

```text
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
|  | (East-West Container & Ceph Fabric) |          | (Control Plane, BMC/IPMI, Telemetry)        |  |
|  +-------------------------------------+          +---------------------------------------------+  |
|                                                                                                    |
|  +-------------------------------- KUBERNETES COMPUTE FABRIC ---------------------------------+  |
|  |  [ MAIN PRODUCTION RKE2 CLUSTER ]               [ SUPPORTING SERVICES K3S CLUSTER ]          |  |
|  |  +---------------------------+                  +------------------------------------------+  |  |
|  |  |   AI / GPU Compute Tier   |                  |   Management / Observability Stack       |  |  |
|  |  | (4x High-Density Nodes)   |                  |   (3x HA Control Plane, 2x Worker Nodes)  |  |  |
|  |  |  - Deep NLP & BEC Models  |                  |  - Prometheus & Grafana Monitoring       |  |  |
|  |  |  - Embedding / Vector DB  |                  |  - Loki Log Aggregation Engine            |  |  |
|  |  |  - Multimodal Inspection  |                  |  - HashiCorp Vault Secret Management     |  |  |
|  |  +-------------┬-------------+                  |  - CI/CD Deployment & Admin Dashboards   |  |  |
|  |  +-------------┴-------------+                  +------------------------------------------+  |  |
|  |  |     Application Tier      |                                                                |  |
|  |  | (4x Microservices Nodes)  |                  +------------------------------------------+  |  |
|  |  |  - Mail Routing & Proxies |                  |    Database / Data Persistence Tier      |  |  |
|  |  |  - Microservices Engine   |                  |    (3x Clustered HA PostgreSQL Nodes)     |  |  |
|  |  |  - Message Queues/Streams |                  |  - Clustered Relational & Spool Metadata  |  |  |
|  |  +-------------┬-------------+                  +---------------------+--------------------+  |  |
|  +----------------│-----------------------------------------------------│---------------------+  |
|                   │                                                     │                        |
|  +----------------▼-----------------------------------------------------▼---------------------+  |
|  |                          DISTRIBUTED SOFTWARE-DEFINED STORAGE (CEPH)                         |  |
|  |   [ High-IOPS Vector/Model Pool ]    [ App / Spool Storage Pool ]   [ DB Persistence & Staging ] |  |
|  +-----------------------------------------------------------------------------┬----------------+  |
|                                                                                │                   |
|  +-------------------------------- DATACENTRE INFRASTRUCTURE -----------------│-----------------+  |
|  |  [ N+1 Modular UPS Fabric ]     [ Automated Backup / Archive ]     [ Security Monitoring ]   |  |
|  +-----------------------------------------------------------------------------│-----------------+  |
+--------------------------------------------------------------------------------│-------------------+
                                                                                 │ Dedicated WAN Link
                                                                                 ▼ (Storage + DB Sync)
+----------------------------------------------------------------------------------------------------+
|                                  DISASTER RECOVERY (DR) DATACENTRE                                 |
|  [ 2x AI Compute Nodes ]   [ 2x Application Nodes ]   [ 1x Database Replica ]   [ Ceph Mirror Pool ]|
+----------------------------------------------------------------------------------------------------+
```

---

## 📥 1. Ingress & External Integration Perimeter

* **Inbound & Outbound SMTP Mail Streams:**
  * Ingests real-time ESMTP connection streams, envelope metadata, and raw multi-part MIME payloads across edge Mail Transfer Agents (MTAs).
  * Captures transport-layer telemetry, connection pacing, sender IP addresses, and real-time handshake properties.

* **Threat Intelligence & Network Reputation Feeds:**
  * Executes synchronous lookups against DNS-based Blackhole Lists (DNSBL/RBL) and custom real-time blocklists.
  * Resolves Forward-Confirmed Reverse DNS (FCrDNS / PTR verification) and correlates Autonomous System Numbers (ASN), BGP route origins, and GeoIP datasets to identify suspicious relays, open proxies, and bulletproof hosting environments.

* **Domain Identity & PKI Cryptographic Registries:**
  * Queries and validates domain-level authentication frameworks including SPF record flattening/macro evaluation, DKIM cryptographic signature verification (RSA/Ed25519), DMARC policy alignment, and ARC (Authenticated Received Chain) validation.
  * Inspects TLS certificate chains, Certificate Authority (CA) trust hierarchies, CRL/OCSP stapling status, Certificate Transparency (CT) log history, and cryptographic validation via DANE (TLSA) and MTA-STS.
  * Analyses domain metadata for registration age (WHOIS), suspicious nameserver clustering, and lookalike homoglyph/typosquatting mutations.

* **Cross-Sector IOC & Regulatory Data Feeds:**
  * Pulls automated Indicators of Compromise (IOCs), malicious URL blacklists, known phishing hashes, and compliance blacklists via authenticated REST/gRPC interfaces secured with mutual TLS (mTLS 1.3).

---

## 🛡️ 2. Perimeter Security & Traffic Routing

* **Boundary Firewall & Threat Mitigation:** Upstream edge traffic is filtered through redundant Next-Generation Firewalls (NGFW) executing stateful packet filtering, Intrusion Prevention (IPS), and DDoS volumetric rate limiting.
* **Load Balancing & TLS Termination:** Redundant Layer 4 / Layer 7 Load Balancers distribute ingress traffic evenly across upstream gateway proxies, managing external TLS termination, rate control, and health probing before routing to internal aggregation switches.

---

## 🔌 3. Dual-Plane Network Fabric

* **100GbE High-Throughput Data Plane:** High-bandwidth, non-blocking switching fabric dedicated entirely to internal East-West container networking (CNI), Ceph storage replication, and high-frequency model inference data transfers over dedicated SFP28/QSFP28 interfaces.
* **100GbE / 10GbE Out-of-Band (OOB) Management Fabric:** Dedicated physical 1GbE / 10GbE RJ45 OOB interfaces connected to isolated out-of-band switches strictly reserved for IPMI/iDRAC bare-metal orchestration, BMC telemetry, control plane management, and administrative console access. These are physically separated from the 10GbE / 100GbE data plane and Ceph public network interfaces.

---

## ⚙️ 4. Clustered Compute & Orchestration Tier

* **AI Accelerator Compute Tier (4 Nodes):**
  * *Hardware Configuration:* Dual enterprise multi-core CPUs, 8x High-Performance Datacentre GPUs, 2TB System RAM per node.
  * *Workload Responsibilities:* Real-time text tokenisation, dense vector embedding generation, NLP-based Business Email Compromise (BEC) detection, deep semantic intention scoring, attachment heuristic unpacking, and multimodal visual analysis of embedded imagery/PDFs.

* **Application Services Tier (4 Nodes):**
  * *Hardware Configuration:* Dual multi-core CPUs, 1TB System RAM per node.
  * *Workload Responsibilities:* Hosts Kubernetes master and worker control planes, core API gateways, SMTP protocol engines, message queue brokers (e.g., Kafka/RabbitMQ), mail policy microservices, and management interfaces.

* **Database & Stateful Tier (3 Nodes):**
  * *Hardware Configuration:* Dual multi-core CPUs, 512GB System RAM per node.
  * *Workload Responsibilities:* High-availability relational database cluster (e.g., PostgreSQL with Patroni) and distributed metadata stores. Manages message disposition states, quarantine indices, system configuration matrices, forensic audit logs, and integration metadata.

---

## 🗄️ 5. Distributed Software-Defined Storage (Ceph SDS)

* **High-Performance AI Model & Vector Storage Pool:** NVMe-backed low-latency block (RBD) and object pools provisioned for rapid loading of neural network checkpoints, vector indices, and real-time inference scratchpads.
* **Application Persistent Volume Pool:** Block and CephFS storage pools supplying resilient Persistent Volume Claims (PVCs) for container state, queue spooling, and application configuration caches.
* **Database & Quarantine Staging Pool:** Dedicated, high-durability storage pools handling relational database write-ahead logs (WAL), transactional tablespaces, and encrypted quarantine staging for suspicious payloads.

---

## 🏢 6. Datacentre Supporting Infrastructure

* **Uninterruptible Power Supply (UPS):** N+1 redundant modular power architecture ensuring uninterrupted operation and clean power distribution across all compute, storage, and networking chassis.
* **Backup & Archival Subsystem:** Dedicated backup appliances executing automated, air-gapped, and deduplicated point-in-time snapshots of databases, persistent state, and system configurations.
* **Integrated Security Monitoring:** Centrally collects host metrics, audit logs, flow records, and network telemetry for comprehensive observability, anomaly alerting, and automated root cause analysis (RCA).

---

## 🔄 7. Disaster Recovery (DR) & Site Continuity

* **Warm-Standby Target Footprint:** Sized at half capacity (2x AI Nodes, 2x Application Nodes, 1x Database Replica) to sustain essential security filtering and mail stream processing during a primary datacentre outage.
* **Cross-Site Replication Fabric:** Employs asynchronous block-level Ceph RBD Mirroring over dedicated WAN links alongside database streaming replication to maintain minimal Recovery Point Objectives (RPO) and low Recovery Time Objectives (RTO).

---

## ☸️ 8. Open-Source Dual-Cluster Kubernetes Architecture (RKE2 & K3s)

To guarantee zero vendor lock-in, complete operational autonomy, and strict enterprise security standards, SongketMail divides its container orchestration into **two distinct open-source Kubernetes clusters**:

1. **Main Production Cluster (Very Big):** Built using **RKE2 (Rancher Kubernetes Engine 2)** — a CNCF-certified, security-hardened enterprise Kubernetes distribution that combines `k3s` operational simplicity with enterprise compliance (supporting FIPS 140-2 compliance when deployed with FIPS-validated cryptographic modules or Canal CNI, CIS Benchmark compliance, containerd runtime, and SELinux/AppArmor enforcement). When eBPF performance and advanced networking are required, Cilium CNI is used.
2. **Supporting Services Cluster (Small):** Built using **K3s** — a lightweight, CNCF-certified Kubernetes distribution optimized for low-resource footprints, edge operations, and management utilities.

```text
+-------------------------------------------------------------------------------------------------------------+
|                                    SONGKETMAIL DUAL KUBERNETES FABRIC                                       |
+----------------------------------------------------+--------------------------------------------------------+
|  CLUSTER 1: RKE2 MAIN PRODUCTION (14 NODES)        |  CLUSTER 2: K3S SUPPORTING SERVICES (5 NODES)          |
+----------------------------------------------------+--------------------------------------------------------+
|  - 3x Control Plane / Server Nodes (HA etcd)       |  - 3x Control Plane / Server Nodes (HA embedded etcd)  |
|  - 4x AI / GPU Acceleration Compute Worker Nodes   |  - 2x Dedicated Worker / Agent Nodes                   |
|  - 4x Application / Microservices Worker Nodes     |  - Core Observability: Prometheus, Grafana, Loki       |
|  - 3x Database & High-IOPS Stateful Worker Nodes   |  - Centralized Vault Secrets & Internal DNS/CI-CD      |
+----------------------------------------------------+--------------------------------------------------------+
```

---

### 8.1 Cluster Topology & Node Allocation Matrix

#### Cluster A: RKE2 Main Production Cluster (14 Nodes - Very Big)

| Hostname | Role | IP Address (Data Plane) | OS Target | Hardware Specs | Configuration File Path | Primary Workload |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rke2-cp-01` | Server / CP 1 | `10.200.10.11` | Ubuntu 26.04 LTS / Alma 9.6 | 16 vCPU, 64GB RAM, 200GB NVMe | `/etc/rancher/rke2/config.yaml` | Kubernetes Control Plane, etcd Member 1 |
| `rke2-cp-02` | Server / CP 2 | `10.200.10.12` | Ubuntu 26.04 LTS / Alma 9.6 | 16 vCPU, 64GB RAM, 200GB NVMe | `/etc/rancher/rke2/config.yaml` | Kubernetes Control Plane, etcd Member 2 |
| `rke2-cp-03` | Server / CP 3 | `10.200.10.13` | Ubuntu 26.04 LTS / Alma 9.6 | 16 vCPU, 64GB RAM, 200GB NVMe | `/etc/rancher/rke2/config.yaml` | Kubernetes Control Plane, etcd Member 3 |
| `rke2-worker-ai-01` | Worker / AI 1 | `10.200.10.21` | Ubuntu 26.04 LTS | 128 vCPU, 2TB RAM, 8x H100/A100 GPU | `/etc/rancher/rke2/config.yaml` | Real-Time NLP, BEC Embedding & Inspection |
| `rke2-worker-ai-02` | Worker / AI 2 | `10.200.10.22` | Ubuntu 26.04 LTS | 128 vCPU, 2TB RAM, 8x H100/A100 GPU | `/etc/rancher/rke2/config.yaml` | Real-Time NLP, BEC Embedding & Inspection |
| `rke2-worker-ai-03` | Worker / AI 3 | `10.200.10.23` | Ubuntu 26.04 LTS | 128 vCPU, 2TB RAM, 8x H100/A100 GPU | `/etc/rancher/rke2/config.yaml` | Multimodal OCR, Attachment Heuristics |
| `rke2-worker-ai-04` | Worker / AI 4 | `10.200.10.24` | Ubuntu 26.04 LTS | 128 vCPU, 2TB RAM, 8x H100/A100 GPU | `/etc/rancher/rke2/config.yaml` | Multimodal OCR, Attachment Heuristics |
| `rke2-worker-app-01`| Worker / App 1| `10.200.10.31` | Ubuntu 26.04 LTS / Alma 9.6 | 64 vCPU, 1TB RAM, 500GB NVMe | `/etc/rancher/rke2/config.yaml` | SMTP Ingress Proxies, NGINX Ingress |
| `rke2-worker-app-02`| Worker / App 2| `10.200.10.32` | Ubuntu 26.04 LTS / Alma 9.6 | 64 vCPU, 1TB RAM, 500GB NVMe | `/etc/rancher/rke2/config.yaml` | SMTP Outbound Engine, Queue Processing |
| `rke2-worker-app-03`| Worker / App 3| `10.200.10.33` | Ubuntu 26.04 LTS / Alma 9.6 | 64 vCPU, 1TB RAM, 500GB NVMe | `/etc/rancher/rke2/config.yaml` | Mail Policy Microservices, Webmail API |
| `rke2-worker-app-04`| Worker / App 4| `10.200.10.34` | Ubuntu 26.04 LTS / Alma 9.6 | 64 vCPU, 1TB RAM, 500GB NVMe | `/etc/rancher/rke2/config.yaml` | Kafka / RabbitMQ Streams, Redis Cache |
| `rke2-worker-db-01` | Worker / DB 1 | `10.200.10.41` | Ubuntu 26.04 LTS / Alma 9.6 | 32 vCPU, 512GB RAM, 4x 3.2TB NVMe | `/etc/rancher/rke2/config.yaml` | PostgreSQL Patroni Node 1, Ceph OSD |
| `rke2-worker-db-02` | Worker / DB 2 | `10.200.10.42` | Ubuntu 26.04 LTS / Alma 9.6 | 32 vCPU, 512GB RAM, 4x 3.2TB NVMe | `/etc/rancher/rke2/config.yaml` | PostgreSQL Patroni Node 2, Ceph OSD |
| `rke2-worker-db-03` | Worker / DB 3 | `10.200.10.43` | Ubuntu 26.04 LTS / Alma 9.6 | 32 vCPU, 512GB RAM, 4x 3.2TB NVMe | `/etc/rancher/rke2/config.yaml` | PostgreSQL Patroni Node 3, Ceph OSD |

#### Cluster B: K3s Supporting Services Cluster (5 Nodes - Small)

| Hostname | Role | IP Address (Management) | OS Target | Hardware Specs | Configuration File Path | Primary Workload |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `k3s-mgmt-01` | Server / CP 1 | `10.200.20.11` | Ubuntu 26.04 LTS / Alma 9.6 | 8 vCPU, 32GB RAM, 100GB SSD | `/etc/rancher/k3s/config.yaml` | K3s Control Plane, Embedded etcd |
| `k3s-mgmt-02` | Server / CP 2 | `10.200.20.12` | Ubuntu 26.04 LTS / Alma 9.6 | 8 vCPU, 32GB RAM, 100GB SSD | `/etc/rancher/k3s/config.yaml` | K3s Control Plane, Embedded etcd |
| `k3s-mgmt-03` | Server / CP 3 | `10.200.20.13` | Ubuntu 26.04 LTS / Alma 9.6 | 8 vCPU, 32GB RAM, 100GB SSD | `/etc/rancher/k3s/config.yaml` | K3s Control Plane, Embedded etcd |
| `k3s-worker-01` | Agent / Worker| `10.200.20.21` | Ubuntu 26.04 LTS / Alma 9.6 | 16 vCPU, 64GB RAM, 500GB SSD | `/etc/rancher/k3s/config.yaml` | Prometheus, Grafana, Loki Stack |
| `k3s-worker-02` | Agent / Worker| `10.200.20.22` | Ubuntu 26.04 LTS / Alma 9.6 | 16 vCPU, 64GB RAM, 500GB SSD | `/etc/rancher/k3s/config.yaml` | HashiCorp Vault, CI/CD Runners, DNS |

---

### 8.2 Open-Source Core Software Stack

To eliminate proprietary dependencies and avoid vendor lock-in, the entire orchestration ecosystem leverages standard, CNCF-maintained open-source software tested against a single supported version matrix:

* **Kubernetes Engines:**
  * **RKE2 (v1.30+):** Security-first distribution using containerd, embedded etcd, and CIS hardened defaults.
  * **K3s (v1.30+):** High-efficiency distribution for management cluster workloads.
* **Container Network Interface (CNI):**
  * **Cilium (v1.15+):** eBPF-based networking, high-speed load balancing, dynamic network policy enforcement, and Hubble observability without IPVS/iptables overhead.
* **Container Storage Interface (CSI):**
  * **Ceph CSI (v3.10+):** Direct block (`rbd.csi.ceph.com`) and filesystem (`cephfs.csi.ceph.com`) driver connecting Kubernetes PVCs directly to the external 3-node Ceph storage cluster.
  * **Longhorn (v1.6+):** Lightweight, open-source distributed block storage utilized strictly inside the K3s supporting cluster for management state snapshots.
* **Ingress & Edge Traffic Management:**
  * **Ingress-Nginx Controller (v1.10+):** Open-source high-throughput HTTP/HTTPS reverse proxy and TLS termination (disabling default bundled RKE2/K3s ingress controllers).
  * **MetalLB (v0.14+):** Bare-metal load balancer providing `LoadBalancer` type IP allocation over Layer 2 ARP / BGP.
* **Certificate & Secret Management:**
  * **Cert-Manager (v1.14+):** Automated x509 certificate issuance via Let's Encrypt ACME and internal HashiCorp Vault PKI.
  * **HashiCorp Vault (Open Source Edition):** Centralized secrets engine with K8s Service Account auth.

---

### 8.3 Node System Prerequisites & Host Preparation

Before installing RKE2 or K3s, all Linux nodes must execute the following kernel and sysctl tuning configuration:

#### 1. Load Required Kernel Modules (`/etc/modules-load.d/k8s.conf`)
```bash
sudo tee /etc/modules-load.d/k8s.conf <<EOF
overlay
br_netfilter
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
nf_conntrack
EOF

sudo modprobe overlay
sudo modprobe br_netfilter
```

#### 2. Configure System Control Parameters (`/etc/sysctl.d/99-kubernetes.conf`)
```bash
sudo tee /etc/sysctl.d/99-kubernetes.conf <<EOF
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
vm.max_map_count                    = 262144
fs.file-max                         = 2097152
EOF

sudo sysctl --system
```
*Note: Binding low-numbered ports (such as SMTP port 25) without root permissions is configured specifically on SMTP ingress worker nodes (`rke2-worker-app-*`) via `net.ipv4.ip_unprivileged_port_start = 25` or Linux `CAP_NET_BIND_SERVICE` capability settings, keeping other nodes restricted.*

---

### 8.4 Step-by-Step Installation & Configuration Guide

#### Secure Token Generation, CA Hash, & Security Notice
Before deploying cluster nodes, generate cryptographically secure 256-bit secret tokens for cluster server and agent join operations using OpenSSL:
```bash
openssl rand -hex 32
```
For cluster node join operations, full join-token values should include the CA hash prefix (`K10<CA_HASH>::<SECRET_TOKEN>`) to pin server TLS certificates during node registration.

Store tokens in an out-of-band secret manager (such as HashiCorp Vault or password manager) and never commit plaintext tokens to git repositories.

**Token Rotation Guidance:**
* **Server Token Rotation:** To rotate server tokens, run `rke2 token rotate` or `k3s token rotate` on control-plane servers.
* **Agent Token Rotation:** Rotating agent tokens requires updating the agent token on all control-plane servers (`/etc/rancher/rke2/config.yaml` / `/etc/rancher/k3s/config.yaml`), followed by updating agent configs on worker nodes and restarting affected worker agents (`systemctl restart rke2-agent` / `systemctl restart k3s-agent`).

#### A. Installing & Configuring RKE2 Production Cluster

Note: RKE2 Supervisor port 9345 and Kubernetes API port 6443 must be exposed on all control-plane nodes and load-balanced behind the HA VIP (`10.200.10.10` / `rke2-vip.songketmail.internal`).

##### Step 1: Configure Primary Control Plane Node (`rke2-cp-01`)
Create `/etc/rancher/rke2/config.yaml`:
```yaml
# /etc/rancher/rke2/config.yaml (Primary Server: rke2-cp-01)
token: "SongketMail-RKE2-SecureClusterToken-2026-Secret"
tls-san:
  - "10.200.10.10"
  - "rke2-cp-01.songketmail.internal"
  - "rke2-vip.songketmail.internal"
cni:
  - cilium
write-kubeconfig-mode: "0600"
etcd-expose-metrics: true
disable:
  - rke2-ingress-nginx
```

Execute installation CLI commands on `rke2-cp-01`:
```bash
curl -sfL https://get.rke2.io | INSTALL_RKE2_CHANNEL="v1.30" sh -
sudo systemctl enable --now rke2-server.service
```

##### Step 2: Configure Additional Control Plane Nodes (`rke2-cp-02` & `rke2-cp-03`)
Create `/etc/rancher/rke2/config.yaml` on `rke2-cp-02` and `rke2-cp-03`:
```yaml
# /etc/rancher/rke2/config.yaml (Secondary Servers: rke2-cp-02 / rke2-cp-03)
server: "https://10.200.10.11:9345"
token: "SongketMail-RKE2-SecureClusterToken-2026-Secret"
tls-san:
  - "10.200.10.10"
  - "rke2-vip.songketmail.internal"
cni:
  - cilium
write-kubeconfig-mode: "0600"
disable:
  - rke2-ingress-nginx
```

Enable systemd service on `rke2-cp-02` and `rke2-cp-03`:
```bash
curl -sfL https://get.rke2.io | INSTALL_RKE2_CHANNEL="v1.30" sh -
sudo systemctl enable --now rke2-server.service
```

##### Step 3: Configure Worker / Agent Nodes (`rke2-worker-ai-*`, `rke2-worker-app-*`, `rke2-worker-db-*`)
Create `/etc/rancher/rke2/config.yaml` on agent nodes:
```yaml
# /etc/rancher/rke2/config.yaml (Worker / Agent Nodes)
server: "https://10.200.10.10:9345"
token: "<GENERATE_SECURE_RKE2_AGENT_TOKEN>"
node-label:
  - "songketmail.io/tier=ai-compute"  # (Adjust label per tier: application / database)
```

Enable systemd agent service on worker nodes:
```bash
curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="agent" INSTALL_RKE2_CHANNEL="v1.30" sh -
sudo systemctl enable --now rke2-agent.service
```

---

#### B. Installing & Configuring K3s Supporting Services Cluster

Note: K3s API server / supervisor port 6443 must be exposed across all management control-plane nodes and load-balanced behind the HA VIP (`10.200.20.10` / `k3s-mgmt.songketmail.internal`).

##### Step 1: Configure Primary K3s Control Plane Node (`k3s-mgmt-01`)
Create `/etc/rancher/k3s/config.yaml`:
```yaml
# /etc/rancher/k3s/config.yaml (Primary Server: k3s-mgmt-01)
cluster-init: true
token: "SongketMail-K3s-MgmtToken-2026-Secret"
tls-san:
  - "10.200.20.10"
  - "k3s-mgmt.songketmail.internal"
write-kubeconfig-mode: "0600"
disable:
  - servicelb
  - traefik
```

Execute installation CLI commands on `k3s-mgmt-01`:
```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL="v1.30" sh -
sudo systemctl enable --now k3s.service
```

##### Step 2: Join Additional K3s Control Plane Nodes (`k3s-mgmt-02` & `k3s-mgmt-03`)
Create `/etc/rancher/k3s/config.yaml` on `k3s-mgmt-02` and `k3s-mgmt-03`:
```yaml
# /etc/rancher/k3s/config.yaml (Join HA Control Plane)
server: "https://10.200.20.11:6443"
token: "SongketMail-K3s-MgmtToken-2026-Secret"
tls-san:
  - "10.200.20.10"
  - "k3s-mgmt.songketmail.internal"
write-kubeconfig-mode: "0600"
disable:
  - servicelb
  - traefik
```

Enable systemd service:
```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL="v1.30" sh -
sudo systemctl enable --now k3s.service
```

##### Step 3: Join K3s Worker / Agent Nodes (`k3s-worker-01` & `k3s-worker-02`)
Execute agent registration CLI command on `k3s-worker-01` and `k3s-worker-02`:
```bash
curl -sfL https://get.k3s.io | K3S_URL="https://10.200.20.11:6443" K3S_TOKEN="SongketMail-K3s-MgmtToken-2026-Secret" sh -
sudo systemctl enable --now k3s-agent.service
```

---

### 8.5 Verification & Operational Handover Checklist

1. **RKE2 Cluster Node Status Verification:**
   ```bash
   sudo /var/lib/rancher/rke2/bin/kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml get nodes -o wide
   ```
   *Expected Output:* 14 nodes listed in `Ready` status with containerd runtime.

2. **K3s Cluster Node Status Verification:**
   ```bash
   sudo k3s kubectl get nodes -o wide
   ```
   *Expected Output:* 5 nodes listed in `Ready` status.

3. **Ceph Storage CSI Integration Verification:**
   ```bash
   sudo /var/lib/rancher/rke2/bin/kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml get storageclass
   ```
   *Expected Output:* `ceph-rbd` and `cephfs` provisioners available and set as persistent volume backends.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-20*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

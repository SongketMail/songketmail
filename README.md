# SongketMail — Podman Email Server Deployment Fabric

An enterprise-grade, highly secure, and horizontally scalable email server baseline orchestrated using **Ansible** and **Podman 5+**. This project acts as the architectural blueprint and operational baseline for deploying persistent, secure, and performant rootless email services.

---

## 🛰️ Distributed Node Strategy

To support production-level horizontal scaling, high availability, and localized file execution, the fabric enforces the **Persistence Trinity**:

### 1. Quadlet Orchestration
Instead of legacy docker-compose or ad-hoc run scripts, this baseline utilizes **Podman Quadlets** for native, user-level systemd integration. This ensures:
- Containers automatically recover and start following host/node reboots.
- Services are managed natively via standard systemd tooling (`systemctl --user`).
- Clean separation of concern with declarative `.container`, `.pod`, and `.network` configuration files.

### 2. Node-Isolated Storage & Sovereignty
To maximize host I/O throughput and maintain clear storage structures, volume mounts point to node-isolated paths under:
```
/opt/songketmail/{{ service_name }}/{{ inventory_hostname }}/data
```
For example, the SMTP/IMAP data for `node1.songketmail.internal` maps exactly to `/opt/songketmail/emailserver/node1.songketmail.internal/data`.

> ⚠️ **The Rootless UID Mapping Problem**:
> In a default rootless Podman environment without user namespace configurations, Podman re-maps host UIDs (e.g., mapping internal UID 2001 to an arbitrary high-range host UID like 101000). This renders the hard disk data directory ownership on the host as `nobody:nogroup`, preventing standard non-sudo administrative rituals, backups, cleanup, or auditing.
>
> 💡 **The Solution — Storage Sovereignty via `keep-id`**:
> We enforce a **mandatory `keep-id` mapping** at the **Pod level**.
> ```ini
> UserNS=keep-id:uid=2001,gid=2001
> ```
> This ensures that the host UID/GID (`2001:2001`) of the `songketmail` owner matches exactly the containerized process's internal UID/GID. Storage Sovereignty is preserved: the Master Architect owns and interacts with the physical mount directories directly and securely without `sudo` privileges.

### 3. Fabric Isolation
All pods, networks, and container names are cluster-prefixed (e.g., `skm_fabric_net`, `skm_fabric_pod`). This ensures that multiple distinct persistence fabrics can co-exist on a single Jump-Host or hypervisor without port or network conflicts.

---

## 🔒 Security Architecture (Aligned with ASIMP Hardening)

To ensure maximum host integrity and protect against vulnerabilities, our setup aligns directly with the **ASIMP (Ansible System Integrity Management Platform)** hardening directives:

1. **Rootful Host-Level Tuning (Tier 3)**:
   - Ansible orchestration operates with `become: yes` to perform essential system-level optimization, including increasing system kernel limits (`vm.max_map_count`) to support elastic/database search indexing, persisting native bridge configurations (`br_netfilter`), and enabling systemd lingering.
2. **Strict Rootless Service Execution**:
   - Component processes (`emailserver`, `spam`, `antivirus`, `webmail`, `imap`, `pop`) run strictly as the unprivileged, non-sudo system user `songketmail` (UID/GID 2001).
3. **ASIMP-aligned Security Audits**:
   - The preparation phase integrates lightweight baseline compliance verification modeled after the ASIMP "Measure, Harden, Re-Measure" pipeline. It verifies the presence of:
     - **Lynis**: Comprehensive host configuration audit and compliance profiling.
     - **OpenSCAP**: Scanning against standard CIS Security Linux Level 2 profile.
     - **Debsums**: Package-level file integrity validation.

---

## 📁 Repository Structure

```
.
├── ansible.cfg                    # Custom Ansible execution settings & privilege escalation
├── site.yml                       # Unified deployment playbook
├── group_vars/
│   └── all.yml                    # Global constants, UID/GID mapping, subuids, and service variables
├── inventory/
│   └── hosts.ini                  # Target server host configurations
├── roles/
│   ├── host_prepare/              # Rootful OS hardening, namespace mapping, and ASIMP audits
│   │   └── tasks/
│   │       ├── main.yml           # Host tuning, subuid/subgid setup, lingering configurations
│   │       └── audit.yml          # ASIMP-style debsums, Lynis, and OpenSCAP baseline scanners
│   └── podman_quadlet/            # Rootless deployment of Podman 5+ Quadlets
│       ├── tasks/
│       │   └── main.yml           # Deploys configurations, reloads user systemd daemon & starts units
│       └── templates/
│           ├── skm_network.network # Declarative container network definition
│           ├── skm_pod.pod         # Declarative shared Pod specification (defines UserNS=keep-id)
│           ├── emailserver.container
│           ├── spam.container
│           ├── antivirus.container
│           ├── webmail.container
│           ├── imap.container
│           └── pop.container
└── README.md                      # Comprehensive baseline documentation
```

---

## 🚀 Deployment Guide

### Prerequisites
- **Podman**: Version `5.0.0` minimum is required on all target nodes.
- **Ansible**: `9.0.0` or higher is recommended.

### 1. Configuration Check
Review global parameters in `group_vars/all.yml` to ensure correct subnetting and volume locations:
```yaml
cluster_prefix: "skm_fabric"
songketmail_uid: 2001
storage_base_path: "/opt/songketmail"
```

### 2. Update Inventory
Add your remote hosts to `inventory/hosts.ini`:
```ini
[email_servers]
node1.songketmail.internal ansible_host=10.0.1.11
node2.songketmail.internal ansible_host=10.0.1.12
```

### 3. Run the Playbook
Run the baseline orchestration play to prepare, harden, and deploy services:
```bash
ansible-playbook -i inventory/hosts.ini site.yml
```

*Note: Host-level tasks use `become: yes` to perform system-level kernel changes, while Quadlet container deployment switches privileges specifically to execute as the unprivileged user `songketmail`.*

---

## 🛠️ Service Maintenance & Auditing

Since **Storage Sovereignty** is maintained via `keep-id`, you can perform data maintenance (backups, logs inspection, configuration updates) directly under the host mount directory as the `songketmail` user without needing root privileges:

```bash
# View Postfix logs or mail queues
ls -lh /opt/songketmail/emailserver/node1.songketmail.internal/data/

# Verify running rootless systemd services as the user
systemctl --user status skm_fabric_emailserver
systemctl --user status skm_fabric_pod-pod
```

---
okf_version: 0.1
type: agent_skill
title: "Ceph Storage Native Deployment Skill"
name: ceph-deployment
description: "Guides AI agents through Ceph native deployment, multi-OS chrony/chronyd configuration, active monitor/manager bootstrap, RBD keyring transfer, and security hardening on Ubuntu 26.04 and AlmaLinux 9.6."
resource: "file:///.agents/skills/ceph-deployment/SKILL.md"
timestamp: 2026-08-25T12:00:00Z
topics: [skills, ceph, deployment, ansible, fqcn, chrony, cephadm]
---

# 🐙 Ceph Storage Native Deployment Skill

This skill teaches Google Antigravity and other AI agents how to natively deploy and manage an independent, production-grade 3-node Ceph storage cluster supporting both Ubuntu 26.04 LTS and AlmaLinux 9.6 (Ceph Tentacle release) using `cephadm` and Ansible roles.

---

## 🎯 When to use this skill
- Use this skill when deploying, updating, or maintaining an independent Ceph cluster.
- Use this skill when configuring multi-OS host synchronization (Chrony) or setting up RBD storage pools for Proxmox VE integration.

---

## 📋 Multi-OS Chrony/chronyd Synchronization

Time synchronization is critical for Ceph cluster quorum stability. The `ceph_prep` role dynamically handles Debian/Ubuntu and RedHat/AlmaLinux path differences:

- **Debian / Ubuntu**: Package `chrony`, config file `/etc/chrony/chrony.conf`
- **RedHat / AlmaLinux**: Package `chrony` (requires EPEL for dependencies), config file `/etc/chrony.conf`, and handler targets `chronyd`

### Declarative Handler Definition
```yaml
- name: Restart Chrony Service
  ansible.builtin.systemd:
    name: "{{ 'chronyd' if (ansible_facts['os_family'] | default('Debian') == 'RedHat') else 'chrony' }}"
    state: restarted
    enabled: true
```

---

## 🚀 Standalone cephadm Bootstrap Sequence

To avoid package repository lockouts, Ceph is deployed using the standalone `cephadm` binary downloader:

1. **Download & Execute**: Download `cephadm` directly from official storage locations using `ansible.builtin.get_url`.
2. **Add Repo**: Run `cephadm add-repo --release tentacle` dynamically.
3. **Install Core Engine**: Install `cephadm` and container engine tools.
4. **Cluster Bootstrap**:
   Bootstrap the cluster on the first monitor node:
   ```bash
   cephadm bootstrap --mon-ip <monitor-ip> --fsid <cluster-fsid>
   ```
5. **Key & Configuration Retrieval**:
   Retrieve the generated admin keyring (`ceph.client.admin.keyring`) and distribute the SSH public keys across all node targets to establish SSH trust.

---

## 🔒 Security Hardening & Isolation

To secure storage communications, backend network isolation is enforced across public and cluster interfaces:
- **Public Network**: Client/Compute communication (e.g. Proxmox VE hosts accessing block volumes).
- **Cluster Network**: Dedicated backend replication and heartbeats between OSDs.
- **Port Isolation**: Local firewalls must restrict access to Ceph daemon ports (such as `3300`, `6789`, `6800-7300`).

---

## 🔌 Proxmox VE (PVE) Integration

Integrating Ceph storage natively with Proxmox VE 9 involves two critical files:
1. **RBD Keyring Transfer**: Copy `/etc/ceph/ceph.client.admin.keyring` to PVE hosts under `/etc/pve/priv/ceph/<cluster-name>.keyring`.
2. **Dynamic `/etc/pve/storage.cfg`**:
   Declare the storage target declaratively:
   ```ini
   rbd: ceph-external
       monhost 10.10.10.1;10.10.10.2;10.10.10.3
       pool rbd
       username admin
       content images
       krbd 0
   ```

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-25*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

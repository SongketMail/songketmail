---
okf_version: 0.1
type: documentation
title: "Automation Framework and FQCN Compliance Standards"
description: "Enforcing Fully Qualified Collection Names (FQCN), privilege escalation philosophies, and Quadlet file deployment tasks."
resource: "file:///docs/ansible-fqcn.md"
timestamp: 2026-07-04T09:40:04Z
topics: [ansible, fqcn, automation, compliance]
---
# 🤖 Automation Framework and FQCN Compliance Standards

To support deployment via automated frameworks such as Google Jules, Ansible playbooks must enforce Fully Qualified Collection Names (FQCN) and manage rootless systemd execution contexts.

---

## 🛠️ Mandatory Ansible FQCN Mapping

Shorthand module names (such as `copy`, `sysctl`, or `systemd`) are replaced with explicit FQCN references across all playbooks and roles.

| Legacy Module Name | Mandatory FQCN Mapping | Primary Automation Context |
|---|---|---|
| **copy** | `ansible.builtin.copy` | Provisioning static configuration files for BunkerWeb, Postfix, and Dovecot. |
| **template** | `ansible.builtin.template` | Generating dynamic Quadlet unit files and SQL initialization scripts. |
| **file** | `ansible.builtin.file` | Provisioning host storage paths assigned to 2001:2001. |
| **systemd** | `ansible.builtin.systemd_service` | Managing Quadlet systemd user services and reloads. |
| **sysctl** | `ansible.posix.sysctl` | Setting host kernel parameters (`net.ipv4.ip_unprivileged_port_start=25`). |
| **postgresql_table** | `community.postgresql.postgresql_table` | Provisioning PostgreSQL database tables for virtual accounts. |
| **postgresql_db** | `community.postgresql.postgresql_db` | Initializing application databases for Postfix, Roundcube, and Rspamd. |
| **podman_network** | `containers.podman.podman_network` | Configuring rootless network bridges (`songketmail-net`). |

---

## 📁 Repository Structure and Implementation Mapping

The Ansible framework uses a modular role layout to isolate component configurations:

| Repository Directory / Role Path | Component Responsibility & Functional Scope |
|---|---|
| **playbooks/site.yml** | Master execution playbook orchestrating host preparation, storage, and service deployment. |
| **playbooks/01_host_prep.yml** | Sets kernel sysctls, provisions user songket (2001), and enables systemd linger. |
| **playbooks/02_storage_setup.yml** | Creates `/var/srv/songketmail/` directory trees assigned to UID/GID 2001:2001. |
| **playbooks/03_database_init.yml** | Deploys PostgreSQL and initializes virtual domain, mailbox, and alias schemas. |
| **playbooks/04_deploy_quadlets.yml** | Generates Quadlet files in `$HOME/.config/containers/systemd/` and starts services. |
| **roles/podman_quadlet/** | Manages rootless Quadlet configuration files including the BunkerWeb proxy container. |
| **roles/dovecot/** | Manages Dovecot configuration, LMTP settings, and obox/s3 object storage integration. |
| **roles/postfix/** | Configures Postfix MTA, PostgreSQL lookup tables, and Rspamd milter bindings. |
| **roles/postgresql/** | Manages database user permissions, initialization scripts, and persistent storage. |
| **roles/minio/** | Sets up MinIO S3 buckets, user access keys, and storage paths. |

---

## ⚙️ Privilege Escalation Philosophy

### Symmetric Privilege Strategy

Ansible playbooks must separate global host tuning (requiring superuser privileges) from the deployment of unprivileged container specifications:

1. **Rootful OS Hardening**: Executed with `become: yes` (sudo as root). Applies sysctl kernel overrides, creates users/groups, and installs Podman and Python packages.
2. **Rootless Deployments**: Executed with `become: yes` + `become_user: songket`. Deploys Quadlet templates directly to the user directory, reloads the unprivileged daemon, and starts services.

---

## 📋 Quadlet File Placement

Systemd Quadlets are evaluated from directories based on the execution context. For our rootless `songket` deployment, the designated destination is:

```
/home/songket/.config/containers/systemd/
```

This directory is scanned automatically by the rootless systemd manager. Placing files here allows unprivileged units to be declared and generated without needing administrative intervention.

---

## 🤖 FQCN Ansible Tasks Blueprint

Below is an explicit, production-grade Ansible task list utilizing proper FQCN syntax to template and deploy Quadlet configurations under the rootless environment. Notice how the environment variables `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` are passed explicitly to the user-level systemd service manager.

{% raw %}
```yaml
# Deploys standard and custom Quadlets into the rootless systemd path
- name: Create Quadlet configuration directory
  ansible.builtin.file:
    path: "/home/songket/.config/containers/systemd"
    state: directory
    owner: songket
    group: songket
    mode: '0755'
  become: yes
  become_user: songket

- name: Deploy SongketMail Quadlet container templates
  ansible.builtin.template:
    src: "templates/{{ item }}.j2"
    dest: "/home/songket/.config/containers/systemd/{{ item }}"
    owner: songket
    group: songket
    mode: '0644'
  loop:
    - skm_network.network
    - skm_pod.pod
    - emailserver.container
  become: yes
  become_user: songket
  register: quadlets_deployed

- name: Reload user-level systemd daemon and restart services
  ansible.builtin.systemd_service:
    daemon_reload: yes
    scope: user
    name: skm_pod-pod.service
    state: restarted
    enabled: yes
  become: yes
  become_user: songket
  environment:
    XDG_RUNTIME_DIR: "/run/user/{{ songket_uid | default(2001) }}"
    DBUS_SESSION_BUS_ADDRESS: "unix:path=/run/user/{{ songket_uid | default(2001) }}/bus"
  when: quadlets_deployed.changed
```
{% endraw %}

---

## ⚠️ Troubleshooting Rootless Ansible Executions

- **Error: Failed to connect to bus**: Double check that systemd lingering is enabled for the target user, and ensure both `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` are explicitly passed inside the Ansible task environment block.
- **Error: Permission denied /var/srv/songketmail/**: Ensure the storage mount path permissions are configured recursively for the UID/GID 2001:2001 host user before initiating the unprivileged Podman deployment.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

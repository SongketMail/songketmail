---
okf_version: 0.1
type: documentation
title: "Rootless Podman 5+ & Quadlet Orchestration"
description: "Advanced rootless capabilities using systemd Quadlets, keep-id namespace mapping, and enabling systemd lingering."
resource: "file:///docs/podman-rootless.md"
timestamp: 2026-07-04T09:40:04Z
---
# 🐳 Rootless Podman 5+ & Quadlet Orchestration

Legacy container deployments heavily rely on rootful Docker daemons or system-wide configurations, presenting major security risks. **Podman 5+** introduces advanced rootless capabilities using **systemd Quadlets**, converting declarative `.container`, `.volume`, `.pod`, and `.network` files directly into native, unprivileged systemd unit files. This removes the overhead of complex daemon architectures and ensures containers behave exactly like local system services.

---

## ⚙️ Mandatory Environment Variables

To interact with rootless systemd managers, Ansible and external scripts must operate within the correct context:

- **`XDG_RUNTIME_DIR`**: Specifies the path where user-specific runtime files (such as sockets and lockfiles) must be stored. For rootless users, this defaults to `/run/user/<UID>` (e.g., `/run/user/2001`). Without this variable, rootless systemctl commands fail with a connection refused error.
- **`DBUS_SESSION_BUS_ADDRESS`**: Points the D-Bus client to the user-level message bus socket, typically located at `unix:path=/run/user/<UID>/bus`. Systemd requires this to authenticate and route systemctl API calls for unprivileged sessions.

---

## 🔒 The keep-id Namespace Mapping Solution

By default, rootless Podman remaps container UID 0 (root) to the host user's UID (e.g., 2001), and maps internal non-root container UIDs (like 2001 inside the container) to high-range subuids (e.g., 102000). Without explicit user namespace mapping, files created inside a container by an internal user are assigned arbitrary subuid ownership on the host, complicating backup operations and permission management.

### Storage Sovereignty via `UserNS=keep-id:uid=2001,gid=2001`

SongketMail enforces namespace mapping using **keep-id** with UID/GID 2001:2001 at the container and pod levels. A dedicated non-root user and group (`songket:songket`, UID/GID 2001:2001) are provisioned on the host OS. System storage directories are created under a standardized path structure (e.g., `/var/srv/songketmail/data/`) and assigned ownership to 2001:2001. By specifying `UserNS=keep-id:uid=2001,gid=2001` in Quadlet unit files, Podman maps UID 2001 inside the container directly to UID 2001 on the host OS. This aligns host and container permissions natively without requiring elevated privileges or dynamic ownership modifications.

---

## 📋 Declarative Quadlet Specifications

### 1. `skm_fabric_pod.pod`
```ini
[Pod]
PodName=skm_fabric_pod
Network=skm_fabric_net.network
UserNS=keep-id:uid=2001,gid=2001
PublishPort=25:25
PublishPort=143:143
PublishPort=465:465
PublishPort=993:993
```

### 2. `skm_fabric_net.network`
```ini
[Network]
NetworkName=skm_fabric_net
Subnet=10.89.1.0/24
Gateway=10.89.1.1
Internal=false
```

### 3. `emailserver.container`
```ini
[Container]
ContainerName=skm_fabric_emailserver
Pod=skm_fabric_pod.pod
Image=docker.io/library/postfix:3.9.0
Volume=/var/srv/songketmail/postfix/config:/etc/postfix:Z
Volume=/var/srv/songketmail/postfix/spool:/var/spool/postfix:Z
UserNS=keep-id:uid=2001,gid=2001

[Service]
Restart=always
```

---

## 🚀 Enabling Systemd Lingering for Rootless Users

By default, user-level systemd processes are killed when the user logs out. To allow background mail services to run persistently on system startup and survive logouts, systemd lingering must be enabled for the service account via `loginctl enable-linger songket` (UID 2001).

```yaml
- name: Enable systemd lingering for songket user
  ansible.builtin.command:
    cmd: "loginctl enable-linger songket"
    creates: "/var/lib/systemd/linger/songket"
  become: yes
```

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

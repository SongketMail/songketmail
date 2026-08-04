---
okf_version: 0.1
type: planning
title: "Google Jules Operational Plan: End-to-End SongketMail & DockPod Deployment"
description: "A highly-structured, multi-phase operational roadmap to bootstrap a minimal Linux server, deploy the full SongketMail email fabric via Ansible, and integrate DockPod for unprivileged management."
resource: "file:///docs/jules-planning.md"
timestamp: 2026-07-04T12:00:00Z
---
# 📋 Google Jules Operational Plan: End-to-End Deployment & Integration

This operational document provides a highly structured, end-to-end tactical roadmap for **Google Jules** to bootstrap a minimal Linux server, deploy the full **SongketMail** secure email server fabric using **Ansible** and **Podman Quadlets**, and configure the **DockPod** control plane for rootless container management and AI-assisted diagnostics.

---

## 🗺️ End-to-End Deployment Overview

```
 [ Minimal Linux Server ]
            │
            ▼
┌───────────────────────────────┐
│   Phase 1: Core Fabric        │
│   (Host Tuning, Ansible FQCN, │ ===> Webmail is ready!
│    Sovereign Storage, Podman) │      (Roundcube + BunkerWeb)
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│   Phase 2: Agentic Control    │
│   (DockPod Control Plane,     │ ===> AI Agentic Diagnostics
│    MCP SSE Server, SSL Proxy) │      (Real-time Logs & Metrics)
└───────────────────────────────┘
```

---

## 📂 Phase 1: Core SongketMail Service Fabric Deployment

The objective of this phase is to transition a minimal, fresh Linux server into a fully operational, production-grade email server and webmail client using Ansible automation.

### Step 1.1: Host Environment Preparation & Tuning
Perform host-level kernel and system-level configuration required for rootless container sandboxing. This requires rootful superuser access (`become: yes`).

1.  **Install Required Base Packages**:
    Ensure the latest stable versions of Python, Ansible, Podman, and the `podman-docker` compatibility layer are installed on the host:
    ```bash
    apt-get update && apt-get install -y python3 python3-pip ansible podman podman-docker
    ```
2.  **Enable Unprivileged Low-Port Binding**:
    Standard Linux kernels restrict unprivileged users from binding to ports below `1024`. Since BunkerWeb runs rootless and must bind to public ports `25`, `80`, `443`, `587`, and `993`, we must tune the sysctl settings:
    ```bash
    sysctl -w net.ipv4.ip_unprivileged_port_start=25
    ```
    To persist this across reboots, define it in `/etc/sysctl.d/99-songketmail.conf`:
    ```ini
    net.ipv4.ip_unprivileged_port_start=25
    ```
3.  **Kernel Networking & Memory Optimizations**:
    Load and persist the bridge networking module for container inter-communication, enable packet forwarding, and increase virtual memory map limits to support database performance:
    ```bash
    modprobe br_netfilter
    echo "br_netfilter" > /etc/modules-load.d/br_netfilter.conf
    sysctl -w net.ipv4.ip_forward=1
    sysctl -w vm.max_map_count=262144
    ```
4.  **Provision Unprivileged User and Subordinate UIDs**:
    Create the designated service owner account `songketmail` (UID/GID `2001:2001`) and configure namespace subuids and subgids to map container operations natively:
    ```bash
    groupadd -g 2001 songketmail
    useradd -u 2001 -g 2001 -m -s /bin/bash songketmail
    echo "songketmail:100000:65536" >> /etc/subuid
    echo "songketmail:100000:65536" >> /etc/subgid
    ```
5.  **Enable User Session Lingering**:
    By default, user systemd daemons terminate upon session logout. To ensure email services run continuously on system startup and persist background executions, activate systemd linger:
    ```bash
    loginctl enable-linger songketmail
    ```

### Step 1.2: Host Persistent Storage & Sovereign Directory Setup
To maintain absolute data integrity and backup capability, establish host-level storage paths mapped directly using user namespace `keep-id`.

1.  **Initialize Storage Base Path**:
    Construct the root storage path at `/var/srv/songketmail` with strict permissions (`0700`) restricting access exclusively to the `songketmail` owner:
    ```bash
    mkdir -p /var/srv/songketmail
    chmod 0700 /var/srv/songketmail
    chown 2001:2001 /var/srv/songketmail
    ```
2.  **Provision the 14 Specific Subdirectories**:
    Create the individual directories to isolate configurations, databases, and message caches for the decoupled service mesh:
    - `bunkerweb/data` - Proxy dynamic storage
    - `nginx/conf` - Ingress site configurations
    - `certs` - SSL/TLS certificates and private keys
    - `postfix/config` - MTA mapping tables and virtual domain definitions
    - `postfix/spool` - Outgoing and active mail queues
    - `dovecot/config` - MDA overrides and SSL keys
    - `dovecot/indexes` - Mailbox index metadata
    - `dovecot/cache` - S3 caching layer
    - `postgres/data` - Accounts maps database
    - `minio/data` - S3 object storage data directory
    - `roundcube/config` - Webmail application configuration files
    - `roundcube/db` - Webmail session and contact database files
    - `rspamd/config` - Spam filters and classification parameters
    - `rspamd/data` - Redis spam database and bayesian cache

    *Note: All of these folders must inherit recursive ownership of UID/GID `2001:2001` with `0700` permissions on the host.*

### Step 1.3: Ansible Playbook Orchestration
Leverage the Ansible playbook (`site.yml`) with strict FQCN mapping to automate the entire deployment.

1.  **Configure Host Inventory (`inventory/hosts.ini`)**:
    Specify the minimal Linux server as the target node:
    ```ini
    [email_servers]
    mail_node ansible_host=192.168.1.100 ansible_user=root
    ```
2.  **Define Global Variables (`group_vars/all.yml`)**:
    Review and pin image tags and execution parameters:
    {% raw %}
    ```yaml
    cluster_prefix: "songketmail"
    songketmail_user: "songketmail"
    songketmail_uid: 2001
    songketmail_gid: 2001
    storage_base_path: "/var/srv/songketmail"
    roundcube_image_tag: "1.6.8-apache"
    bunkerweb_image_tag: "1.6.13"
    ```
    {% endraw %}
3.  **Execute the Deployment**:
    Run the unified site playbook. This implements the **Symmetric Privilege Strategy**: executing host-level hardening as `root`, and switching context directly to `become_user: songketmail` to template, write, and run user-session Quadlet unit files:
    ```bash
    ansible-playbook -i inventory/hosts.ini site.yml
    ```

### Step 1.4: Quadlet Activation & User Systemd Daemon Execution
Ensure the Quadlets are correctly interpreted by the systemd user manager.

1.  **Verify Quadlet Unit Placements**:
    Confirm files are located under:
    ```bash
    /home/songketmail/.config/containers/systemd/
    ```
    The directory must contain:
    - `songketmail_net.network` (Network configuration bridge)
    - `songketmail_pod.pod` (Consolidated Pod container group with `UserNS=keep-id`)
    - `songketmail_proxy.container` (BunkerWeb edge proxy)
    - `songketmail_postfix.container` (Postfix SMTP server)
    - `songketmail_dovecot.container` (Dovecot IMAP and LMTP delivery)
    - `songketmail_db.container` (PostgreSQL accounts maps)
    - `songketmail_s3.container` (MinIO remote storage backend)
    - `songketmail_web.container` (Roundcube Webmail)
    - `songketmail_rspamd.container` (Rspamd spam filters)
2.  **Reload User systemd Manager**:
    Run a user-session daemon-reload to parse the Quadlet configurations and generate native systemd service files:
    ```bash
    systemctl --user daemon-reload
    ```
3.  **Start and Enable Services**:
    Initialize the Pod group and the individual container engines:
    ```bash
    systemctl --user enable --now songketmail_pod-pod.service
    systemctl --user enable --now songketmail_proxy.service
    systemctl --user enable --now songketmail_web.service
    ```

### Step 1.5: Core Service and Webmail Ingress Verification
Confirm the email server is fully up, secure, and ready to transmit and receive messages.

1.  **Check Services Status**:
    Inspect the service statuses under the unprivileged user scope:
    ```bash
    systemctl --user status songketmail_pod-pod.service
    systemctl --user status songketmail_web.service
    ```
2.  **Verify Public Ports Binding**:
    Ensure BunkerWeb is successfully listening on host ports:
    ```bash
    ss -tulnp | grep -E "25|80|443|587|993"
    ```
3.  **Validate Webmail UI Access**:
    Access the Roundcube client through your web browser at `https://mail.songketmail.internal/`.
    The connection is terminated securely via BunkerWeb, utilizing client IP preservation and standard WAF filters to shield the mail backend from external threats.

---

## 📊 Phase 2: DockPod Control Plane & Agentic MCP Integration

The objective of this phase is to deploy **DockPod** as a lightweight, zero-dependency container manager and Model Context Protocol (MCP) server, allowing remote AI clients to securely perform log audits, health checks, and metrics collection.

### Step 2.1: Local Socket Activation for Unprivileged Access
Enable the rootless Podman API socket, allowing DockPod to interact with the container engine without root permissions.

1.  **Activate user-level Podman Socket**:
    ```bash
    systemctl --user enable --now podman.socket
    ```
2.  **Verify Socket Ownership**:
    Ensure the socket is initialized and accessible under the `songketmail` user session:
    ```bash
    ls -la /run/user/2001/podman/podman.sock
    ```

### Step 2.2: DockPod Daemon Provisioning and User systemd Service
Deploy the compiled Go binary and manage its lifecycle natively via systemd.

1.  **Download the Binary**:
    ```bash
    mkdir -p ~/.local/bin
    curl -fsSL -o ~/.local/bin/dockpod https://dockpod.io/releases/latest/dockpod
    chmod +x ~/.local/bin/dockpod
    ```
2.  **Create User systemd Unit File**:
    Write the service file to `~/.config/systemd/user/dockpod.service`:
    ```ini
    [Unit]
    Description=DockPod Container Control Plane
    After=podman.socket
    Requires=podman.socket

    [Service]
    ExecStart=%h/.local/bin/dockpod --addr 127.0.0.1:8080 --mcp-addr 127.0.0.1:8090 --data-dir /var/srv/songketmail/dockpod/data --socket /run/user/2001/podman/podman.sock
    Restart=on-failure
    WorkingDirectory=%h

    [Install]
    WantedBy=default.target
    ```
3.  **Start the Service**:
    ```bash
    systemctl --user daemon-reload
    systemctl --user enable --now dockpod.service
    ```

### Step 2.3: Ingress Routing and SSL Termination through BunkerWeb
Configure secure HTTPS endpoints for the DockPod dashboard and MCP streaming server.

1.  **Configure Proxy Route**:
    Update the BunkerWeb reverse proxy configuration or specify environment variables to handle routing to DockPod:
    ```nginx
    # DockPod Panel Proxy Configuration
    server {
        listen 443 ssl;
        server_name panel.songketmail.local;

        ssl_certificate /var/srv/songketmail/certs/fullchain.pem;
        ssl_certificate_key /var/srv/songketmail/certs/privkey.pem;

        location / {
            proxy_pass http://127.0.0.1:8080;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }

    # Isolate Server-Sent Events (SSE) buffering for MCP Stream
    server {
        listen 443 ssl;
        server_name mcp.songketmail.local;

        ssl_certificate /var/srv/songketmail/certs/fullchain.pem;
        ssl_certificate_key /var/srv/songketmail/certs/privkey.pem;

        location / {
            proxy_pass http://127.0.0.1:8090;
            proxy_http_version 1.1;
            proxy_buffering off;
            proxy_cache off;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
    ```
2.  **Restart BunkerWeb Container**:
    ```bash
    systemctl --user restart songketmail-proxy
    ```

### Step 2.4: Token Generation and Security Hardening
Establish strict security controls to prevent unauthorized access to the container manager.

1.  **Configure Localhost Ingress Restriction**:
    Ensure public direct access to ports `8080` and `8090` is dropped by the host firewall. External access must traverse BunkerWeb SSL/TLS port `443` exclusively.
2.  **Create Administrator Account**:
    Log into `https://panel.songketmail.local` and register your admin credentials.
3.  **Generate MCP Access Token**:
    Navigate to **Settings -> API Keys -> Generate Key**. Save the generated secure token (e.g. `dp_mcp_xxxxxxxxxxxxxxxxxxxx`) with unprivileged permissions (`0600`) on the host.

### Step 2.5: Agentic Connection and Diagnostic Auditing
Connect your AI Client to DockPod and verify deep diagnostic reporting.

1.  **Configure Client Settings**:
    Add the MCP remote definition to the client configuration file (e.g., `claude_desktop_config.json`):
    ```json
    {
      "mcpServers": {
        "DockPod": {
          "command": "npx",
          "args": [
            "mcp-remote",
            "https://mcp.songketmail.local/sse",
            "--header",
            "Authorization: Bearer dp_mcp_xxxxxxxxxxxxxxxxxxxx"
          ]
        }
      }
    }
    ```
2.  **Verify Connection with LLM Tools**:
    Ask the AI agent to list containers or verify Postfix mail loops to prove end-to-end telemetry and monitoring are fully established.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

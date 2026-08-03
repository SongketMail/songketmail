---
okf_version: 0.1
type: planning
title: "Google Jules Operational Plan: DockPod Integration"
description: "A highly-structured, multi-session roadmap for autonomous agents to deploy, configure, and secure DockPod in the unprivileged SongketMail environment."
resource: "file:///docs/jules-planning.md"
timestamp: 2026-07-04T12:00:00Z
---
# 📋 Google Jules Operational Plan: DockPod Integration

This operational document provides a highly structured, multi-session tactical plan for **Google Jules** to systematically implement, configure, and secure the **DockPod** container manager within the **SongketMail** unprivileged user context.

---

## 🛠️ Multi-Session Implementation Roadmap

```
+---------------------------------------------------------------------------------+
|                         OPERATIONAL SESSIONS TIMELINE                           |
|                                                                                 |
| [Session 1: Env Prep] --> [Session 2: Service Provision] --> [Session 3: Ingress]
|                                                                        |        |
| [Session 5: Verification] <-- [Session 4: Hardening & MCP Setup] <-----+        |
+---------------------------------------------------------------------------------+
```

---

## 📂 Session 1: Environment Preparation & Local Socket Exposure

The objective of this session is to establish correct environment context for the unprivileged `songket` user and activate the rootless Podman API socket.

### Step 1.1: Verify User Lingering
Verify that systemd lingering is enabled on the host to ensure user-session services persist after logout.
```bash
# Run as superuser on host
loginctl enable-linger songket
```

### Step 1.2: Set Session Environment Variables
Define the required runtime and D-Bus variables for rootless systemd execution.
```bash
export XDG_RUNTIME_DIR="/run/user/2001"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/2001/bus"
```

### Step 1.3: Enable Podman Rootless Socket
Activate the unprivileged Podman API listening socket.
```bash
systemctl --user enable --now podman.socket
```

### Step 1.4: Verify Socket Access
Ensure the socket file is initialized and owned by `songket:songket` (`2001:2001`).
```bash
ls -la /run/user/2001/podman/podman.sock
```

---

## 📦 Session 2: DockPod Service Provisioning

The objective of this session is to retrieve the DockPod binary and deploy it as a systemd user service under the unprivileged `songket` context.

### Step 2.1: Create Target Folders
Initialize storage and local execution folders under `/var/srv/songketmail/dockpod` or user home:
```bash
mkdir -p ~/.local/bin
mkdir -p /var/srv/songketmail/dockpod/data
```

### Step 2.2: Download the DockPod Binary
Fetch the latest stable Go binary of DockPod:
```bash
curl -fsSL -o ~/.local/bin/dockpod https://dockpod.io/releases/latest/dockpod
chmod +x ~/.local/bin/dockpod
```

### Step 2.3: Write the Declarative systemd Service Unit
Create the user-level systemd service file at `~/.config/systemd/user/dockpod.service`:
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

### Step 2.4: Start and Enable the Service
Reload the user-level systemd daemon and activate the DockPod service:
```bash
systemctl --user daemon-reload
systemctl --user enable --now dockpod.service
```

### Step 2.5: Verify Service Logs
Ensure the service has bound correctly to local ports `:8080` (web) and `:8090` (MCP):
```bash
systemctl --user status dockpod.service
```

---

## 🌐 Session 3: Nginx SSL/TLS Ingress Configuration

The objective of this session is to routing external web requests and WebSocket streams securely to the DockPod local listener using Nginx.

### Step 3.1: Create Site Configuration Block
Modify the Nginx ingress configuration under `/var/srv/songketmail/nginx/conf/nginx.conf` or equivalent virtual hosting file:
```nginx
# Panel Proxy Route
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
```

### Step 3.2: Create MCP Proxy Route
Configure a separate route to isolate SSE (Server-Sent Events) streams for the MCP server:
```nginx
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

### Step 3.3: Restart Nginx Container
```bash
systemctl --user restart songketmail_pod-pod
```

---

## 🛡️ Session 4: Security Hardening & MCP Key Generation

The objective of this session is to harden the network posture and generate secure API keys to link external AI clients.

### Step 4.1: Verify Firewall Rules
Ensure public access to ports `8080` and `8090` is dropped at the host firewall level, routing all external traffic strictly over SSL/TLS port `443` through Nginx:
```bash
# UFW setup examples (run as root)
ufw deny 8080/tcp
ufw deny 8090/tcp
```

### Step 4.2: First-Run Administrator Creation
Log in to the newly deployed panel at `https://panel.songketmail.local/` and register the primary admin account with a secure, high-entropy password.

### Step 4.3: Generate MCP Token
Navigate to **Settings -> API Keys -> Generate Key**, name the token `Google-Jules-Client`, and safely document the generated key:
```
dp_mcp_xxxxxxxxxxxxxxxxxxxx
```

---

## 🚀 Session 5: Agentic Integration & Automated Verification

The objective of this session is to establish connection with the Google Jules client and execute automated diagnostic runs.

### Step 5.1: Configure Client Settings
Add the remote SSE server definition inside the client configuration (`claude_desktop_config.json` or the Jules environment context):
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

### Step 5.2: Run Diagnostic Validation Queries
From the AI client's chat interface, execute the following validation commands to ensure the integration functions natively:
```
"List all containers running under SongketMail"
"Retrieve the latest log lines for the postfix container"
"What is the CPU and memory consumption of our postgres database?"
```

### Step 5.3: Document Output Metrics
Document and store the verification response within `docs/dockpod-metrics.md` to establish an audit baseline.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

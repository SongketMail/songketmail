---
okf_version: 0.1
type: agent_skill
title: "DockPod Integration Skill"
name: dockpod-integration
description: "Instructs AI agents on unprivileged Podman socket activation, DockPod daemon configuration, and MCP SSE secure routing via BunkerWeb proxy."
resource: "file:///.agents/skills/dockpod-integration/SKILL.md"
timestamp: 2026-07-04T12:00:00Z
---

# 📊 DockPod Integration Skill

This skill teaches Google Antigravity and other AI agents how to integrate the DockPod control plane and Model Context Protocol (MCP) server for remote container management and AI-assisted diagnostics.

## 🎯 When to use this skill
- Use this skill when deploying, auditing, or troubleshooting the DockPod unprivileged management layer.
- Use this skill when connecting remote AI clients or configuring SSL proxy routing for MCP Server-Sent Events (SSE).

## 🔌 Local Socket Activation
To allow the DockPod daemon to interact with rootless Podman without root privileges, the user-level Podman API socket must be enabled:
```bash
systemctl --user enable --now podman.socket
```
Verify socket presence at `/run/user/2001/podman/podman.sock`.

## 📦 DockPod Provisioning and Service Configuration
The DockPod Go binary is deployed as a user systemd service.

1.  **Binary Location**:
    Keep the executable under `~/.local/bin/dockpod`.
2.  **User Systemd Configuration (`~/.config/systemd/user/dockpod.service`)**:
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

## 🔒 SSL Routing via BunkerWeb Ingress
To ensure secure external connection, DockPod's web interface (port 8080) and MCP stream interface (port 8090) are reverse-proxied and terminated by BunkerWeb with SSL/TLS.

1.  **DockPod Panel Configuration**:
    Configure routing to `http://127.0.0.1:8080` with websocket support.
2.  **MCP SSE Streaming Isolation**:
    Since MCP streams use Server-Sent Events (SSE), response buffering must be disabled:
    ```nginx
    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Host $host;
        ...
    }
    ```

## 🗝️ API Keys & Client Configuration
Remote AI clients connect securely to DockPod via MCP.

1.  Generate an API key from the DockPod dashboard (**Settings -> API Keys**).
2.  Configure your local AI desktop client (e.g., `claude_desktop_config.json`):
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

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*

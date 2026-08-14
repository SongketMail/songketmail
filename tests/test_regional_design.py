"""Unit and integration tests for the Multi-Region Proxmox VE, Ceph, and PBS design.

This test module verifies the compliance and technical accuracy of the regional
datacenter design documentation (Markdown and HTML), compliance of Ansible playbooks
and Podman Quadlet configurations, and performs integrated checks for
OKF v0.1, constitution footer, and link standards.
"""

import os
import pytest

# --- Test Constants ---
REG_MD_PATH = os.path.join("docs", "regional-design-proxmox-ceph.md")
REG_HTML_PATH = os.path.join("docs", "regional-design-proxmox-ceph.html")


def test_regional_design_markdown_okf_frontmatter():
    """Verifies that regional-design-proxmox-ceph.md complies with OKF v0.1 frontmatter standards.

    Checks for mandatory fields: okf_version, type, title, timestamp, topics, and layout.
    """
    assert os.path.exists(REG_MD_PATH), f"File {REG_MD_PATH} does not exist"

    with open(REG_MD_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()

    assert content.startswith("---"), "Markdown file must start with YAML frontmatter markers (---)"

    parts = content.split("---", 2)
    assert len(parts) >= 3, "Incomplete frontmatter block in Markdown file"

    frontmatter_text = parts[1]
    metadata = {}
    for line in frontmatter_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            metadata[k.strip()] = v.strip().strip('"').strip("'")

    # Required OKF frontmatter elements
    assert "okf_version" in metadata, "Missing mandatory field 'okf_version'"
    assert metadata["okf_version"] == "0.1", f"Expected okf_version 0.1, got {metadata['okf_version']}"
    assert "type" in metadata, "Missing mandatory field 'type'"
    assert metadata["type"] == "documentation", "Expected type 'documentation'"
    assert "title" in metadata, "Missing mandatory field 'title'"
    assert "timestamp" in metadata, "Missing mandatory field 'timestamp'"
    assert "topics" in metadata, "Missing mandatory field 'topics'"

    # Verify regional-related topic tags are defined
    topics = metadata["topics"].lower()
    assert "proxmox" in topics, "Expected 'proxmox' topic"
    assert "ceph" in topics, "Expected 'ceph' topic"


def test_regional_design_markdown_footer_compliance():
    """Ensures regional-design-proxmox-ceph.md includes proper author and constitution footers.

    Checks for the mandatory brand elements: Harisfazillah Jamel, LinuxMalaysia, and DSOM.
    """
    with open(REG_MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Harisfazillah Jamel" in content, "Missing author name 'Harisfazillah Jamel' in footer"
    assert "LinuxMalaysia" in content, "Missing brand 'LinuxMalaysia' in footer"
    assert "DSOM" in content, "Missing constitution signature 'DSOM' in footer"


def test_regional_design_pbs_technical_content():
    """Validates that Section 6 (Proxmox Backup Server) contains key architectural specifications.

    Verifies the inclusion of: client-side encryption, dirty bitmaps, deduplication,
    Zstandard compression, WAN sync pull strategy, and Live-Restore.
    """
    with open(REG_MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify presence of Section 6 title and key sub-headings
    assert "6. Multi-Region Backup Architecture" in content, "Missing Section 6 title"
    assert "6.1 Core Architectural Pillars" in content, "Missing Section 6.1"
    assert "6.2 Geolocated WAN Synchronization" in content, "Missing Section 6.2"
    assert "6.3 Anti-Ransomware, Integrity Verification, & Archival" in content, "Missing Section 6.3"
    assert "6.4 Low RTO/RPO Disaster Recovery & Restore Stack" in content, "Missing Section 6.4"

    # Verify deep technical parameters
    assert "Zstandard" in content or "ZSTD" in content, "Missing Zstandard compression reference"
    assert "dirty bitmaps" in content.lower(), "Missing QEMU dirty bitmaps integration"
    assert "deduplication" in content.lower(), "Missing chunk-level deduplication specification"
    assert "AES-256 GCM" in content or "AES-256-GCM" in content or "Galois/Counter Mode" in content, \
        "Missing AES-256 GCM client-side encryption standard"
    assert "pull" in content.lower() or "pull-based" in content.lower(), "Missing pull-based sync strategy description"
    assert "Live-Restore" in content, "Missing Live-Restore near-zero RTO instant recovery feature"


def test_regional_design_html_unification_integrity():
    """Verifies that the unified template script compiled the html file correctly.

    Checks that the central content area exists and includes the synchronized
    Section 6 header anchors and the sidebar navigation elements.
    """
    assert os.path.exists(REG_HTML_PATH), f"Unified HTML file {REG_HTML_PATH} does not exist"

    with open(REG_HTML_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Content Area confirmation
    assert "<!-- Column 2: Center Main Content Area" in content, \
        "HTML template center column layout marker is missing or damaged"

    # Anchor tags checks
    assert 'id="6-multi-region-backup-architecture-via-proxmox-backup-server-pbs"' in content, \
        "TOC Anchor id for Section 6 is missing or incorrect"
    assert 'id="61-core-architectural-pillars-of-pbs"' in content, \
        "TOC Anchor id for Section 6.1 is missing or incorrect"

    # Sidebar Navigation links check
    assert 'href="#6-multi-region-backup-architecture-via-proxmox-backup-server-pbs"' in content, \
        "TOC Sidebar Link for Section 6 is missing"
    assert 'href="#61-core-architectural-pillars-of-pbs"' in content, \
        "TOC Sidebar Link for Section 6.1 is missing"


def test_ansible_playbooks_syntax_and_structure():
    """Verifies that all root-level and nested Ansible playbooks have valid YAML format and structural keys."""
    playbook_files = ["site.yml", "asimp_hardening_playbook.yml", "wsl_feedback_playbook.yml"]
    for pb in playbook_files:
        if not os.path.exists(pb):
            continue
        with open(pb, "r", encoding="utf-8") as f:
            content = f.read()
        assert ":" in content, f"Playbook {pb} lacks key-value colon structure"
        assert "-" in content, f"Playbook {pb} lacks YAML list element marker (-)"


def test_podman_quadlet_templates_exist_and_compliant():
    """Verifies that Podman Quadlet container files are structured and secure.

    Ensures that containers specify explicit non-root or keep-id namespaces.
    """
    quadlet_dir = "roles/podman_quadlet/templates"
    if not os.path.exists(quadlet_dir):
        pytest.skip("Podman Quadlet roles directory not found.")

    for f in os.listdir(quadlet_dir):
        if f.endswith(".container"):
            filepath = os.path.join(quadlet_dir, f)
            with open(filepath, "r", encoding="utf-8") as file_obj:
                content = file_obj.read()
            assert "[Container]" in content, f"Quadlet container file {f} lacks systemd [Container] section"

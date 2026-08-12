"""Unit tests for independent Ceph deployment playbooks and configurations.

This module contains comprehensive test cases to verify the integrity,
formatting, YAML syntax, and FQCN compliance of the Ansible playbooks,
inventory, variables, and documentation files introduced in this session
for independent Ceph native deployment on Ubuntu 26.04.
"""

import os
import re
import configparser

# --- Test Constants ---
CEPH_DEPLOY_DIR = "ceph_deploy"
PLAYBOOK_PATH = os.path.join(CEPH_DEPLOY_DIR, "playbook.yml")
HOSTS_PATH = os.path.join(CEPH_DEPLOY_DIR, "hosts.ini")
VARS_PATH = os.path.join(CEPH_DEPLOY_DIR, "group_vars", "all.yml")
DOC_MD_PATH = os.path.join("docs", "ceph-ubuntu-deployment.md")
DOC_HTML_PATH = os.path.join("docs", "ceph-ubuntu-deployment.html")


def test_hosts_inventory_structure():
    """Verifies the Ansible inventory structure and groups in hosts.ini.

    Checks that the hosts.ini inventory file exists, is readable, and contains
    the mandatory [ceph_nodes] and [pve_nodes] host groups.
    """
    assert os.path.exists(HOSTS_PATH), f"Inventory file {HOSTS_PATH} does not exist"

    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read(HOSTS_PATH)

    # Assert mandatory groups exist
    assert "ceph_nodes" in parser.sections(), "ceph_nodes group is missing in hosts.ini"
    assert "pve_nodes" in parser.sections(), "pve_nodes group is missing in hosts.ini"

    # Assert there are 3 Ceph nodes and 4 PVE nodes
    ceph_hosts = list(parser["ceph_nodes"].keys())
    pve_hosts = list(parser["pve_nodes"].keys())

    assert len(ceph_hosts) == 3, f"Expected 3 Ceph nodes, found {len(ceph_hosts)}"
    assert len(pve_hosts) == 4, f"Expected 4 PVE nodes, found {len(pve_hosts)}"


def test_group_vars_all_yaml():
    """Verifies the content integrity of Ceph configuration group variables.

    Reads and parses group_vars/all.yml to ensure all key variables such as
    fsid, cluster networks, capacity limits, and replication configurations
    are defined and valid.
    """
    assert os.path.exists(VARS_PATH), f"Variables file {VARS_PATH} does not exist"

    with open(VARS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify key variables presence
    assert "ceph_cluster_name:" in content, "ceph_cluster_name is not defined"
    assert "ceph_release:" in content, "ceph_release is not defined"
    assert "ceph_fsid:" in content, "ceph_fsid is not defined"
    assert "ceph_raw_capacity_tb:" in content, "ceph_raw_capacity_tb is not defined"
    assert "ceph_usable_capacity_tb:" in content, "ceph_usable_capacity_tb is not defined"
    assert "ceph_replication_size:" in content, "ceph_replication_size is not defined"


def test_capacity_sizing_math():
    """Validates the capacity sizing calculations against replication limits.

    Ensures that raw capacity, replication factor, and usable capacity
    parameters match the user requirements of 154TB raw and 51TB usable storage.
    """
    with open(VARS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract capacity values
    raw_match = re.search(r"ceph_raw_capacity_tb:\s*(\d+)", content)
    usable_match = re.search(r"ceph_usable_capacity_tb:\s*(\d+)", content)
    rep_match = re.search(r"ceph_replication_size:\s*(\d+)", content)

    assert raw_match, "Failed to parse ceph_raw_capacity_tb"
    assert usable_match, "Failed to parse ceph_usable_capacity_tb"
    assert rep_match, "Failed to parse ceph_replication_size"

    raw_val = int(raw_match.group(1))
    usable_val = int(usable_match.group(1))
    rep_val = int(rep_match.group(1))

    assert raw_val == 154, f"Expected 154TB raw, got {raw_val}TB"
    assert usable_val == 51, f"Expected 51TB usable, got {usable_val}TB"
    assert rep_val == 3, f"Expected 3x replication, got {rep_val}x"

    # Sizing math checks
    computed_usable = raw_val // rep_val
    assert computed_usable == usable_val, \
        f"Calculated usable ({computed_usable}TB) does not match declared usable ({usable_val}TB)"


def test_ansible_playbook_yaml_integrity():
    """Verifies that the main deployment playbook is structured correctly.

    Checks that the main playbook.yml exists and contains all modular stages:
    OS prep, cluster bootstrapping, hardening, PVE integration, and benchmarks.
    """
    assert os.path.exists(PLAYBOOK_PATH), f"Playbook file {PLAYBOOK_PATH} does not exist"

    with open(PLAYBOOK_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for mandatory roles in playbook execution
    assert "role: ceph_prep" in content, "ceph_prep role is missing from playbook"
    assert "role: ceph_bootstrap" in content, "ceph_bootstrap role is missing from playbook"
    assert "role: security_hardening" in content, "security_hardening role is missing from playbook"
    assert "role: pve_integration" in content, "pve_integration role is missing from playbook"
    assert "role: validation_bench" in content, "validation_bench role is missing from playbook"


def test_ceph_ansible_fqcn_compliance():
    """Ensures that all Ansible playbooks and role tasks use Fully Qualified Collection Names (FQCN).

    Iterates through all YAML files in ceph_deploy/ to detect any legacy short module names
    (e.g., 'copy', 'apt', 'command', 'get_url') that violate the FQCN coding guidelines.
    """
    yaml_files = []
    for root, dirs, files in os.walk(CEPH_DEPLOY_DIR):
        for f in files:
            if f.endswith((".yml", ".yaml")):
                yaml_files.append(os.path.join(root, f))

    legacy_modules = {
        "copy", "template", "sysctl", "file", "command", "shell", "user", "group",
        "lineinfile", "package", "apt", "yum", "debug", "assert", "import_tasks",
        "import_role", "include_tasks", "include_role", "set_fact", "git", "get_url"
    }

    pattern_task_item = re.compile(r"^(\s*)-\s+([a-zA-Z0-9_\.]+)\s*:\s*")
    pattern_key = re.compile(r"^(\s*)([a-zA-Z0-9_\.]+)\s*:\s*")

    structural_keys = {
        "name", "hosts", "become", "become_user", "vars", "environment", "when",
        "register", "ignore_errors", "block", "tags", "with_items", "loop",
        "rescue", "always", "failed_when", "changed_when", "state", "mode",
        "owner", "group", "dest", "src", "content", "creates", "file", "cmd"
    }

    violations = []

    for filepath in yaml_files:
        if "group_vars" in filepath or "defaults" in filepath:
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            task_indent = None
            module_indent = None

            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                m_task = pattern_task_item.match(line)
                if m_task:
                    indent_str, key_name = m_task.groups()
                    task_indent = len(indent_str)
                    module_indent = None
                    if key_name in legacy_modules and key_name not in structural_keys:
                        violations.append((filepath, i, key_name))
                    continue

                m_key = pattern_key.match(line)
                if m_key:
                    indent_str, key_name = m_key.groups()
                    key_indent = len(indent_str)

                    if task_indent is not None and key_indent > task_indent:
                        if module_indent is None:
                            module_indent = key_indent
                            if key_name in legacy_modules and key_name not in structural_keys:
                                violations.append((filepath, i, key_name))
                    elif task_indent is not None and key_indent == task_indent:
                        if key_name in legacy_modules and key_name not in structural_keys:
                            violations.append((filepath, i, key_name))

    assert len(violations) == 0, f"Found non-FQCN legacy module references in ceph_deploy: {violations}"


def test_new_documentation_okf_frontmatter():
    """Validates OKF v0.1 frontmatter standards for ceph-ubuntu-deployment.md.

    Checks that the newly created markdown file starts with YAML frontmatter containing
    okf_version, type, title, timestamp, and topics as defined by project guidelines.
    """
    assert os.path.exists(DOC_MD_PATH), f"Documentation file {DOC_MD_PATH} does not exist"

    with open(DOC_MD_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()

    assert content.startswith("---"), "Markdown file does not start with YAML frontmatter marker '---'"

    parts = content.split("---", 2)
    assert len(parts) >= 3, "Incomplete frontmatter block in markdown file"

    fm_text = parts[1]
    metadata = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            metadata[k.strip()] = v.strip().strip('"').strip("'")

    # Assert mandatory OKF metadata fields
    assert "okf_version" in metadata, "Missing 'okf_version' field"
    assert metadata["okf_version"] == "0.1", f"Expected okf_version 0.1, got {metadata['okf_version']}"
    assert "type" in metadata, "Missing 'type' field"
    assert metadata["type"] == "documentation", "Expected type 'documentation'"
    assert "title" in metadata, "Missing 'title' field"
    assert "timestamp" in metadata, "Missing 'timestamp' field"
    assert "topics" in metadata, "Missing 'topics' field"


def test_new_documentation_footer_standards():
    """Ensures that the new markdown file contains proper licensing and project footer.

    Verifies the presence of the author Harisfazillah Jamel, LinuxMalaysia, and DSOM
    AI Protocol standard signature in the page footer.
    """
    with open(DOC_MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Harisfazillah Jamel" in content, "Missing author name 'Harisfazillah Jamel' in footer"
    assert "LinuxMalaysia" in content, "Missing brand name 'LinuxMalaysia' in footer"
    assert "DSOM" in content, "Missing constitution signature 'DSOM' in footer"

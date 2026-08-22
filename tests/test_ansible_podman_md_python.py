#!/usr/bin/env python3
"""
tests/test_ansible_podman_md_python.py - Comprehensive unit test suite
verifying Ansible playbook structure/FQCN compliance, Podman Quadlet templates
and keep-id configuration, Markdown files OKF metadata/footer layout compliance,
and Python utility helper functions inside scripts/.
"""

import os
import re
import sys
from unittest.mock import MagicMock, patch, mock_open

# Add the project root to sys.path so that 'scripts' module can be imported cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- Helpers ---

def get_yaml_files(root_dir="."):
    """Recursively retrieves all .yml and .yaml files in the repository."""
    yaml_files = []
    for root, dirs, files in os.walk(root_dir):
        if '.git' in root or '.pytest_cache' in root or '__pycache__' in root:
            continue
        for f in files:
            if f.endswith(('.yml', '.yaml')):
                yaml_files.append(os.path.join(root, f))
    return sorted(yaml_files)


def get_quadlet_files():
    """Retrieves all templates under roles/podman_quadlet/templates/."""
    quadlet_dir = "roles/podman_quadlet/templates"
    files = []
    if os.path.exists(quadlet_dir):
        for f in os.listdir(quadlet_dir):
            full_path = os.path.join(quadlet_dir, f)
            if os.path.isfile(full_path):
                files.append(full_path)
    return sorted(files)


def get_markdown_files():
    """Collects Markdown files from the repository, excluding Git, pytest cache, bytecode cache, and docs-source directories.
    
    Returns:
        list[str]: Sorted paths to the Markdown files found.
    """
    md_files = []
    for root, dirs, files in os.walk('.'):
        if '.git' in root or '.pytest_cache' in root or '__pycache__' in root or 'docs-source' in root:
            continue
        for f in files:
            if f.endswith('.md'):
                md_files.append(os.path.join(root, f))
    return sorted(md_files)


# --- 1. Ansible Playbook Unit Tests ---

def test_ansible_playbooks_yaml_validity():
    """Verifies that all Ansible playbooks/task lists are valid, parsable files."""
    yaml_files = get_yaml_files()
    assert len(yaml_files) > 0, "No Ansible/YAML configuration files found."

    for filepath in yaml_files:
        # Check basic bracket/brace and colon formatting of YAML structure
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Verify document contains basic structure (e.g. YAML separator or indented lists/maps)
        has_structure = False
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("---") or ":" in stripped or stripped.startswith("-"):
                has_structure = True
                break
        assert has_structure, f"File {filepath} does not look like a structured YAML file."


def test_ansible_playbooks_fqcn_compliance():
    """
    Ensures that Ansible playbooks and role tasks use Fully Qualified Collection Names (FQCN)
    and avoid deprecated or legacy non-FQCN short module names (e.g. 'copy', 'template').
    """
    yaml_files = get_yaml_files()

    legacy_modules = {
        'copy', 'template', 'sysctl', 'file', 'command', 'shell', 'user', 'group',
        'lineinfile', 'package', 'apt', 'yum', 'debug', 'assert', 'import_tasks',
        'import_role', 'include_tasks', 'include_role', 'set_fact', 'git', 'get_url'
    }

    # Regex patterns for matching keys
    pattern_task_item = re.compile(r'^(\s*)-\s+([a-zA-Z0-9_\.]+)\s*:\s*')
    pattern_key = re.compile(r'^(\s*)([a-zA-Z0-9_\.]+)\s*:\s*')

    # Exclude common non-module structural keywords
    structural_keys = {
        'name', 'hosts', 'become', 'become_user', 'vars', 'environment', 'when',
        'register', 'ignore_errors', 'block', 'tags', 'with_items', 'loop',
        'rescue', 'always', 'failed_when', 'changed_when', 'state', 'mode',
        'owner', 'group', 'dest', 'src', 'content', 'creates', 'file', 'cmd'
    }

    violations = []

    for filepath in yaml_files:
        # Only inspect playbooks and task lists
        if "roles/" not in filepath and "playbooks/" not in filepath and not filepath.endswith("playbook.yml") and filepath != "site.yml":
            continue
        if "group_vars" in filepath or "defaults" in filepath:
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            task_indent = None
            module_indent = None

            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue

                # Compute current line indentation
                current_indent = len(line) - len(line.lstrip())

                # Check if it starts a new list item (typically starts a task)
                m_task = pattern_task_item.match(line)
                if m_task:
                    indent_str, key_name = m_task.groups()
                    task_indent = len(indent_str)
                    module_indent = None # Reset module indent on new task

                    if key_name in legacy_modules and key_name not in structural_keys:
                        violations.append((filepath, i, key_name))
                    continue

                # Check general key-value pairs
                m_key = pattern_key.match(line)
                if m_key:
                    indent_str, key_name = m_key.groups()
                    key_indent = len(indent_str)

                    # If we don't have an established module indent yet and this key is indented
                    # more than the task level, it might be the module name.
                    if task_indent is not None and key_indent > task_indent:
                        if module_indent is None:
                            # This is the first key inside the task (often the module name)
                            module_indent = key_indent
                            if key_name in legacy_modules and key_name not in structural_keys:
                                violations.append((filepath, i, key_name))
                        elif key_indent > module_indent:
                            # Indented deeper than the module block itself - this is a module parameter!
                            # E.g. "shell: /bin/bash" inside "ansible.builtin.user" module
                            continue
                        elif key_indent == module_indent:
                            # Siblings of the module (or other metadata)
                            if key_name in legacy_modules and key_name not in structural_keys:
                                violations.append((filepath, i, key_name))
                    elif task_indent is not None and key_indent == task_indent:
                        # Direct sibling of the task dictionary (e.g. "when:", "register:")
                        if key_name in legacy_modules and key_name not in structural_keys:
                            violations.append((filepath, i, key_name))

    # Assert that zero FQCN violations are found across all Ansible files
    assert len(violations) == 0, f"Found legacy short module declarations (non-FQCN) in tasks: {violations}"


# --- 2. Podman Quadlet Unit Tests ---

def test_podman_quadlet_sections_and_syntax():
    """Verifies that Podman Quadlet configuration files have appropriate systemd headers."""
    quadlet_files = get_quadlet_files()
    assert len(quadlet_files) > 0, "No Podman Quadlet template files found."

    for filepath in quadlet_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Quadlet files must have at least one valid systemd section header
        valid_sections = ["[Container]", "[Pod]", "[Network]", "[Volume]", "[Service]"]
        has_header = any(section in content for section in valid_sections)
        assert has_header, f"Quadlet file {filepath} lacks required systemd section headers: {valid_sections}"


def test_podman_quadlet_keep_id_mapping():
    """
    Verifies that the SongketMail Pod Quadlet config enforces keep-id user namespace mapping
    to maintain storage sovereignty and support rootless file system privileges (UID/GID 2001:2001).
    """
    pod_template = "roles/podman_quadlet/templates/skm_pod.pod"
    assert os.path.exists(pod_template), "skm_pod.pod template file not found."

    with open(pod_template, 'r', encoding='utf-8') as f:
        content = f.read()

    # The UserNS keep-id mapping directive must be defined
    assert "UserNS=keep-id" in content, \
        "SongketMail Pod Quadlet is missing 'UserNS=keep-id' directive, breaking storage sovereignty."
    assert "uid=" in content and "gid=" in content, \
        "skm_pod.pod UserNS should declare explicit UID/GID parameter maps."


def test_podman_quadlet_no_hardcoded_passwords():
    """
    Verifies that Podman Quadlet container templates do not contain plain-text hardcoded passwords
    and instead utilize Jinja2 templating variables.
    """
    quadlet_files = get_quadlet_files()
    assert len(quadlet_files) > 0, "No Podman Quadlet template files found."

    password_env_pattern = re.compile(r'Environment=.*PASSWORD=(?!\{\{)(.+)', re.IGNORECASE)

    violations = []
    for filepath in quadlet_files:
        if not filepath.endswith('.container'):
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                m = password_env_pattern.search(line)
                if m:
                    violations.append((filepath, line_num, line.strip()))

    assert len(violations) == 0, f"Found hardcoded passwords in Quadlet container templates: {violations}"


# --- 3. Markdown Files (OKF and Footer standards) ---

def test_markdown_okf_standard():
    """
    Verifies that all Markdown (.md) documentation files comply with Google OKF v0.1 by including
    valid YAML frontmatter with required version, type, title, timestamp, and topics.
    """
    md_files = get_markdown_files()
    assert len(md_files) > 0, "No Markdown documentation files found."

    for filepath in md_files:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()

        # Must start with frontmatter block
        assert content.startswith("---"), f"Markdown file {filepath} does not start with OKF frontmatter marker '---'"

        parts = content.split("---", 2)
        assert len(parts) >= 3, f"Markdown file {filepath} has incomplete frontmatter block."

        fm_text = parts[1]
        metadata = {}
        for line in fm_text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                k, v = line.split(':', 1)
                metadata[k.strip()] = v.strip().strip('"').strip("'")

        # Validate mandatory OKF v0.1 frontmatter fields
        assert "okf_version" in metadata, f"{filepath} is missing 'okf_version' field."
        assert metadata["okf_version"] == "0.1", f"{filepath} okf_version is not 0.1."
        assert "type" in metadata, f"{filepath} is missing mandatory 'type' classification."
        assert "title" in metadata, f"{filepath} is missing mandatory 'title' text."
        assert "timestamp" in metadata, f"{filepath} is missing 'timestamp' field."
        assert "topics" in metadata, f"{filepath} is missing 'topics' tags."


def test_markdown_footer_compliance():
    """
    Ensures that Markdown documentation files contain the authorized project constitution footer
    referencing Harisfazillah Jamel, LinuxMalaysia, and DSOM AI Protocol standards.
    """
    md_files = get_markdown_files()
    for filepath in md_files:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # The document should end with licensing and constitution references
        assert "Harisfazillah Jamel" in content, f"Markdown file {filepath} lacks author reference in footer."
        assert "LinuxMalaysia" in content or "DSOM" in content, \
            f"Markdown file {filepath} lacks DSOM AI Protocol or LinuxMalaysia constitution in footer."


# --- 4. Python Utility Helper Script Tests ---

def test_link_checker_is_external_or_special():
    """Unit tests for the helper function check_links.is_external_or_special."""
    from scripts import check_links

    # Verify exact behaviour on known cases
    assert check_links.is_external_or_special("https://google.com") is True
    assert check_links.is_external_or_special("mailto:test@example.com") is True
    assert check_links.is_external_or_special("#section-anchor") is True
    assert check_links.is_external_or_special("./local-file.md") is False


@patch("os.path.isdir", return_value=True)
@patch("os.walk")
def test_link_checker_all_links_success(mock_walk, mock_isdir):
    """Mocks file search to verify check_links.check_all_links() success path."""
    from scripts import check_links

    # Simulate walking documentation directory
    mock_walk.return_value = [
        ("docs", [], ["index.md"]),
    ]

    # Mock open function using built-in mock_open
    m_open = mock_open(read_data="This is a [link](./references.md)")

    with patch("builtins.open", m_open), \
         patch("os.path.exists", return_value=True):
        success = check_links.check_all_links()
        assert success is True


def test_unify_templates_generate_slug():
    """Unit tests for slug generation logic inside scripts/unify_templates.py."""
    from scripts import unify_templates

    assert unify_templates.generate_slug("<h2>Hello World!</h2>") == "hello-world"
    assert unify_templates.generate_slug("A Simple Heading 123") == "a-simple-heading-123"
    assert unify_templates.generate_slug("---") == ""


def test_verify_mail_web_app_check_port_success():
    """Unit test for check_port() when port is listening."""
    from scripts import verify_mail_web_app

    mock_socket = MagicMock()
    mock_socket.connect_ex.return_value = 0

    with patch("socket.socket", return_value=mock_socket):
        is_active, desc = verify_mail_web_app.check_port(80)
        assert is_active is True
        assert desc == "Listening"


def test_verify_mail_web_app_check_port_failure():
    """Unit test for check_port() when port is occupied or closed."""
    from scripts import verify_mail_web_app

    mock_socket = MagicMock()
    mock_socket.connect_ex.return_value = 111

    with patch("socket.socket", return_value=mock_socket):
        is_active, desc = verify_mail_web_app.check_port(80)
        assert is_active is False
        assert desc == "Not Listening"


def test_update_sidebars_functionality():
    """Unit test for update_sidebars module updating html navigation sidebars."""
    from scripts import update_sidebars

    # Mock file listing to return a test list of files
    with patch("os.listdir", return_value=["test_file_1.html", "asimp-hardening-report.html"]):
        # Mock HTML content featuring Google Jules planning link
        jules_planning_content = """
        <html>
        <body>
        <!-- Sidebar Navigation -->
        <a href="jules-planning.html" class="flex px-3 py-2 text-sm">Planning</a>
        </body>
        </html>
        """
        # Mocking file read/write routines
        m_open = mock_open(read_data=jules_planning_content)
        with patch("builtins.open", m_open):
            update_sidebars.update_html_sidebars()

            # Retrieve write file outputs to check if the ASIMP report link was successfully injected
            # Filter for any open calls with "w" parameter
            write_calls = [call for call in m_open.mock_calls if len(call.args) > 1 and call.args[1] == "w"]
            assert len(write_calls) > 0, "Expected file write to occur during sidebar injection."


def test_agent_skills_compliance():
    """
    Verifies that all 10 agent skills under .agents/skills/ are present,
    comply with combined OKF/Antigravity metadata, and contain the DSOM footer.
    """
    skills_dir = ".agents/skills"
    assert os.path.exists(skills_dir), "Skills directory does not exist."

    expected_skills = [
        "dockpod-integration",
        "jekyll-gh-pages",
        "jules-agent-protocol",
        "jules-sandbox-mode",
        "songketmail-architecture",
        "songketmail-deployment",
        "ceph-deployment",
        "wsl-development-feedback",
        "s3-storage-integration",
        "template-unification"
    ]

    for skill in expected_skills:
        skill_path = os.path.join(skills_dir, skill)
        assert os.path.isdir(skill_path), f"Expected skill directory '{skill}' not found."

        skill_md_path = os.path.join(skill_path, "SKILL.md")
        assert os.path.exists(skill_md_path), f"SKILL.md not found for skill '{skill}'."

        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # Check frontmatter
        assert content.startswith("---"), f"SKILL.md for '{skill}' does not start with frontmatter marker '---'."
        parts = content.split("---", 2)
        assert len(parts) >= 3, f"SKILL.md for '{skill}' has incomplete frontmatter block."

        fm_text = parts[1]
        metadata = {}
        for line in fm_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                metadata[k.strip()] = v.strip().strip('"').strip("'")

        # Antigravity required fields
        assert "name" in metadata, f"SKILL.md for '{skill}' is missing 'name' metadata."
        assert metadata["name"] == skill, f"SKILL.md for '{skill}' has mismatched 'name' metadata. Expected '{skill}', got '{metadata['name']}'."
        assert "description" in metadata, f"SKILL.md for '{skill}' is missing 'description' metadata."

        # OKF required fields
        assert "okf_version" in metadata, f"SKILL.md for '{skill}' is missing 'okf_version' metadata."
        assert "type" in metadata, f"SKILL.md for '{skill}' is missing 'type' metadata."
        assert "title" in metadata, f"SKILL.md for '{skill}' is missing 'title' metadata."
        assert "timestamp" in metadata, f"SKILL.md for '{skill}' is missing 'timestamp' metadata."
        assert "topics" in metadata, f"SKILL.md for '{skill}' is missing 'topics' metadata."

        # Footer check
        assert "Harisfazillah Jamel" in content, f"SKILL.md for '{skill}' is missing author reference in footer."
        assert "LinuxMalaysia" in content or "DSOM" in content, f"SKILL.md for '{skill}' lacks DSOM AI Protocol or LinuxMalaysia constitution in footer."


def test_sync_docs_missing_token_raises_value_error():
    """Verifies sync_docs.main() raises ValueError when DOCS_REPO_TOKEN is unset."""
    import pytest
    from scripts import sync_docs

    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="DOCS_REPO_TOKEN"):
            sync_docs.main([])


def test_sync_docs_missing_source_dir_raises_value_error(tmp_path):
    """Verifies validate_source_docs raises ValueError if source_dir does not exist."""
    import pytest
    from scripts import sync_docs

    non_existent_dir = tmp_path / "non_existent_source"
    with pytest.raises(ValueError, match="does not exist"):
        sync_docs.validate_source_docs(non_existent_dir)


def test_sync_docs_missing_docs_json_raises_value_error(tmp_path):
    """Verifies validate_source_docs raises ValueError if docs.json is missing."""
    import pytest
    from scripts import sync_docs

    source_dir = tmp_path / "empty_source"
    source_dir.mkdir()
    with pytest.raises(ValueError, match="docs.json"):
        sync_docs.validate_source_docs(source_dir)


def test_sync_docs_file_count_below_floor_raises_value_error(tmp_path):
    """Verifies validate_source_docs raises ValueError if file count is below min_files."""
    import pytest
    import json
    from scripts import sync_docs

    source_dir = tmp_path / "sparse_source"
    source_dir.mkdir()
    docs_json = source_dir / "docs.json"
    docs_json.write_text(json.dumps({"navigation": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="fewer than the required minimum threshold"):
        sync_docs.validate_source_docs(source_dir, min_files=5)


def test_sync_docs_unresolved_nav_page_raises_value_error(tmp_path):
    """Verifies validate_source_docs raises ValueError if a page in docs.json fails to resolve."""
    import pytest
    import json
    from scripts import sync_docs

    source_dir = tmp_path / "missing_page_source"
    source_dir.mkdir()
    docs_json = source_dir / "docs.json"
    docs_json.write_text(json.dumps({"navigation": [{"pages": ["nonexistent_page"]}]}), encoding="utf-8")

    # Create dummy files to exceed min_files threshold
    for i in range(5):
        (source_dir / f"dummy_{i}.txt").write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match=r"references page\(s\) that do not exist"):
        sync_docs.validate_source_docs(source_dir, min_files=5)


def test_sync_docs_dry_run_mode_success():
    """Verifies sync_docs.main(["--dry-run"]) passes validation without DOCS_REPO_TOKEN."""
    from scripts import sync_docs

    with patch.dict(os.environ, {}, clear=True):
        # Should complete gracefully without raising token errors or running git push
        sync_docs.main(["--dry-run"])


def test_sync_docs_deletion_cap_exceeded_raises_value_error():
    """Verifies sync_docs.main() raises ValueError if deletion count exceeds max_deletions cap."""
    import pytest
    from scripts import sync_docs
    from pathlib import Path

    mock_target = MagicMock()
    mock_target.exists.return_value = True

    # Return 15 target files to trigger deletion cap (since source has 0 target matches)
    target_items = [MagicMock(is_file=lambda: True, parts=["file_" + str(i)], relative_to=lambda t, i=i: Path(f"target_file_{i}.mdx")) for i in range(15)]
    mock_target.rglob.return_value = target_items

    with patch.dict(os.environ, {"DOCS_REPO_TOKEN": "test_token_123"}), \
         patch("scripts.sync_docs.Path") as mock_path, \
         patch("scripts.sync_docs.run"), \
         patch("scripts.sync_docs.shutil.rmtree"), \
         patch("scripts.sync_docs.validate_source_docs", return_value=[Path("docs-source/docs.json")]), \
         patch("scripts.sync_docs.compute_file_diff", return_value=([], [], [Path(f"del_{i}.mdx") for i in range(15)])):

        def path_side_effect(arg):
            """
            Redirect the documentation repository path to the mocked target.
            
            Parameters:
            	arg: Path-like value to resolve.
            
            Returns:
            	The mocked target for "/tmp/docs-repo"; otherwise, a Path for the input.
            """
            if str(arg) == "/tmp/docs-repo":
                return mock_target
            return Path(arg)

        mock_path.side_effect = path_side_effect
        with pytest.raises(ValueError, match="Deletion cap exceeded"):
            sync_docs.main([])


@patch("scripts.sync_docs.run")
@patch("scripts.sync_docs.shutil.rmtree")
@patch("scripts.sync_docs.shutil.copytree")
@patch("subprocess.run")
def test_sync_docs_main_success_flow(mock_sub_run, mock_copytree, mock_rmtree, mock_run):
    """Verifies sync_docs.main() cloning, copying, committing, and pushing workflow."""
    from scripts import sync_docs
    from pathlib import Path

    mock_diff_res = MagicMock()
    mock_diff_res.returncode = 1
    mock_sub_run.return_value = mock_diff_res

    fake_tmp = MagicMock()
    fake_tmp.exists.return_value = True

    git_item = MagicMock()
    git_item.name = ".git"
    git_item.is_dir.return_value = True

    dir_item = MagicMock()
    dir_item.name = "old_dir"
    dir_item.is_dir.return_value = True

    file_item = MagicMock()
    file_item.name = "old_file.mdx"
    file_item.is_dir.return_value = False

    fake_tmp.iterdir.return_value = [git_item, dir_item, file_item]

    with patch.dict(os.environ, {"DOCS_REPO_TOKEN": "test_token_123"}), \
         patch("scripts.sync_docs.Path") as mock_path:
        # Redirect /tmp/docs-repo Path instantiation to fake_tmp
        def path_side_effect(arg):
            """
            Map the temporary documentation repository path to its test fixture.
            
            Parameters:
                arg: A path-like value to resolve.
            
            Returns:
                The fake temporary path for `/tmp/docs-repo`; otherwise, a `Path` for the supplied value.
            """
            if str(arg) == "/tmp/docs-repo":
                return fake_tmp
            return Path(arg)

        mock_path.side_effect = path_side_effect
        sync_docs.main([])

    # Verify run calls include git clone, git config, git add, git commit, git push
    run_cmds = [call.args[0] for call in mock_run.call_args_list]
    assert any("clone" in cmd for cmd in run_cmds)
    assert any("commit" in cmd for cmd in run_cmds)
    assert any("push" in cmd for cmd in run_cmds)

    # Verify shutil calls
    rmtree_paths = [call.args[0] for call in mock_rmtree.call_args_list]
    assert fake_tmp in rmtree_paths or dir_item in rmtree_paths

    mock_copytree.assert_called_with(Path("docs-source"), fake_tmp, dirs_exist_ok=True)

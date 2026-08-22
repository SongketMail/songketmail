#!/usr/bin/env python3
"""
tests/test_ansible_podman_md_python.py - Comprehensive unit test suite
verifying Ansible playbook structure/FQCN compliance, Podman Quadlet templates
and keep-id configuration, Markdown files OKF metadata/footer layout compliance,
and Python utility helper functions inside scripts/.
"""

import json
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
    """Retrieves all Markdown (.md) files in the repository."""
    md_files = []
    for root, dirs, files in os.walk('.'):
        if '.git' in root or '.pytest_cache' in root or '__pycache__' in root:
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
    from scripts import sync_docs

    with patch.dict(os.environ, {}, clear=True):
        try:
            sync_docs.main()
            assert False, "Expected ValueError when DOCS_REPO_TOKEN is missing"
        except ValueError as exc:
            assert "DOCS_REPO_TOKEN" in str(exc)


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
         patch("scripts.sync_docs.Path", return_value=fake_tmp):
        sync_docs.main()

    # Verify run calls include git clone, git config, git add, git commit, git push
    run_cmds = [call.args[0] for call in mock_run.call_args_list]
    assert any("clone" in cmd for cmd in run_cmds)
    assert any("commit" in cmd for cmd in run_cmds)
    assert any("push" in cmd for cmd in run_cmds)


# --- 5. Documentation Sync Pipeline Tests (sync_docs.py, workflow, docs-source) ---

def test_sync_docs_run_uses_shell_for_string_commands():
    """run() must invoke subprocess.run with shell=True when given a raw string command."""
    from scripts import sync_docs

    with patch("scripts.sync_docs.subprocess.run") as mock_sub_run:
        sync_docs.run("echo hello")

    mock_sub_run.assert_called_once_with("echo hello", cwd=None, check=True, shell=True)


def test_sync_docs_run_disables_shell_for_list_commands():
    """run() must invoke subprocess.run with shell=False and forward cwd when given a token list."""
    from scripts import sync_docs

    with patch("scripts.sync_docs.subprocess.run") as mock_sub_run:
        sync_docs.run(["git", "status"], cwd="/tmp/repo")

    mock_sub_run.assert_called_once_with(["git", "status"], cwd="/tmp/repo", check=True, shell=False)


@patch("scripts.sync_docs.run")
@patch("scripts.sync_docs.shutil.copytree")
@patch("scripts.sync_docs.shutil.rmtree")
@patch("subprocess.run")
def test_sync_docs_main_skips_initial_cleanup_when_tmp_missing(mock_sub_run, mock_rmtree, mock_copytree, mock_run):
    """main() must not call shutil.rmtree on the clone target when it does not already exist."""
    from scripts import sync_docs

    mock_diff_res = MagicMock()
    mock_diff_res.returncode = 1
    mock_sub_run.return_value = mock_diff_res

    fake_tmp = MagicMock()
    fake_tmp.exists.return_value = False
    fake_tmp.iterdir.return_value = []

    with patch.dict(os.environ, {"DOCS_REPO_TOKEN": "test_token"}), \
         patch("scripts.sync_docs.Path", return_value=fake_tmp):
        sync_docs.main()

    mock_rmtree.assert_not_called()


@patch("scripts.sync_docs.run")
@patch("scripts.sync_docs.shutil.copytree")
@patch("scripts.sync_docs.shutil.rmtree")
@patch("subprocess.run")
def test_sync_docs_main_no_changes_skips_commit_and_push(mock_sub_run, mock_rmtree, mock_copytree, mock_run, capsys):
    """main() must skip 'git commit'/'git push' and print 'No changes' when the staged diff is empty."""
    from scripts import sync_docs

    mock_diff_res = MagicMock()
    mock_diff_res.returncode = 0  # `git diff --staged --quiet` found no differences
    mock_sub_run.return_value = mock_diff_res

    fake_tmp = MagicMock()
    fake_tmp.exists.return_value = False
    fake_tmp.iterdir.return_value = []

    with patch.dict(os.environ, {"DOCS_REPO_TOKEN": "test_token"}), \
         patch("scripts.sync_docs.Path", return_value=fake_tmp):
        sync_docs.main()

    run_cmds = [call.args[0] for call in mock_run.call_args_list]
    assert any("clone" in cmd for cmd in run_cmds), "Clone should still happen before the diff check."
    assert not any("commit" in cmd for cmd in run_cmds), "No commit should be made when there are no changes."
    assert not any("push" in cmd for cmd in run_cmds), "No push should be made when there are no changes."

    captured = capsys.readouterr()
    assert "No changes" in captured.out


@patch("scripts.sync_docs.run")
@patch("scripts.sync_docs.shutil.copytree")
@patch("scripts.sync_docs.shutil.rmtree")
@patch("subprocess.run")
def test_sync_docs_main_preserves_git_directory_during_wipe(mock_sub_run, mock_rmtree, mock_copytree, mock_run):
    """main() must never delete the '.git' entry while wiping old docs content, but must remove
    other directories via rmtree and other files via unlink."""
    from scripts import sync_docs

    mock_diff_res = MagicMock()
    mock_diff_res.returncode = 1
    mock_sub_run.return_value = mock_diff_res

    git_item = MagicMock()
    git_item.name = ".git"

    dir_item = MagicMock()
    dir_item.name = "old_dir"
    dir_item.is_dir.return_value = True

    file_item = MagicMock()
    file_item.name = "old_file.mdx"
    file_item.is_dir.return_value = False

    fake_tmp = MagicMock()
    fake_tmp.exists.return_value = True
    fake_tmp.iterdir.return_value = [git_item, dir_item, file_item]

    with patch.dict(os.environ, {"DOCS_REPO_TOKEN": "test_token"}), \
         patch("scripts.sync_docs.Path", return_value=fake_tmp):
        sync_docs.main()

    # The .git directory must never be removed or unlinked
    git_item.unlink.assert_not_called()
    assert all(c.args[0] is not git_item for c in mock_rmtree.call_args_list), \
        ".git directory must be preserved during the wipe step."

    # Non-git directory entries are removed via rmtree; files via unlink
    mock_rmtree.assert_any_call(dir_item)
    file_item.unlink.assert_called_once()


@patch("scripts.sync_docs.run")
@patch("scripts.sync_docs.shutil.copytree")
@patch("scripts.sync_docs.shutil.rmtree")
@patch("subprocess.run")
def test_sync_docs_main_embeds_token_in_clone_url(mock_sub_run, mock_rmtree, mock_copytree, mock_run):
    """main() must build the authenticated clone URL using the DOCS_REPO_TOKEN and DOCS_REPO constant."""
    from scripts import sync_docs

    mock_diff_res = MagicMock()
    mock_diff_res.returncode = 1
    mock_sub_run.return_value = mock_diff_res

    fake_tmp = MagicMock()
    fake_tmp.exists.return_value = False
    fake_tmp.iterdir.return_value = []

    with patch.dict(os.environ, {"DOCS_REPO_TOKEN": "s3cr3t-token"}), \
         patch("scripts.sync_docs.Path", return_value=fake_tmp):
        sync_docs.main()

    clone_cmds = [call.args[0] for call in mock_run.call_args_list if "clone" in call.args[0]]
    assert len(clone_cmds) == 1, "Expected exactly one 'git clone' invocation."

    clone_cmd = clone_cmds[0]
    assert any("x-access-token:s3cr3t-token@github.com" in part for part in clone_cmd), \
        "Clone URL must embed the DOCS_REPO_TOKEN as an x-access-token credential."
    assert any(sync_docs.DOCS_REPO in part for part in clone_cmd), \
        "Clone URL must target the configured DOCS_REPO."
    assert "--branch" in clone_cmd and sync_docs.BRANCH in clone_cmd


@patch("scripts.sync_docs.run")
@patch("scripts.sync_docs.shutil.copytree")
@patch("scripts.sync_docs.shutil.rmtree")
@patch("subprocess.run")
def test_sync_docs_main_copies_source_dir_into_tmp_with_overwrite(mock_sub_run, mock_rmtree, mock_copytree, mock_run):
    """main() must copy SOURCE_DIR into the cloned repo path, overwriting existing content."""
    from scripts import sync_docs

    mock_diff_res = MagicMock()
    mock_diff_res.returncode = 1
    mock_sub_run.return_value = mock_diff_res

    fake_tmp = MagicMock()
    fake_tmp.exists.return_value = False
    fake_tmp.iterdir.return_value = []

    with patch.dict(os.environ, {"DOCS_REPO_TOKEN": "test_token"}), \
         patch("scripts.sync_docs.Path", return_value=fake_tmp):
        sync_docs.main()

    mock_copytree.assert_called_once_with(sync_docs.SOURCE_DIR, fake_tmp, dirs_exist_ok=True)


def test_sync_docs_workflow_file_structure():
    """Verifies the sync-docs GitHub Actions workflow declares the expected trigger and job steps."""
    path = ".github/workflows/sync-docs.yml"
    assert os.path.exists(path), "sync-docs.yml workflow file not found."

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "name: Sync Docs" in content
    assert "branches: [main]" in content, "Workflow should trigger only on the main branch."
    assert "docs-source/**" in content, "Workflow should be path-filtered to docs-source changes."
    assert "actions/checkout@v4" in content
    assert "actions/setup-python@v5" in content
    assert 'python-version: "3.11"' in content
    assert "DOCS_REPO_TOKEN" in content
    assert "secrets.DOCS_REPO_TOKEN" in content, "The token must be sourced from repository secrets."
    assert "python scripts/sync_docs.py" in content


def test_sync_docs_workflow_does_not_trigger_on_pull_request():
    """Ensures the docs sync workflow only reacts to pushes, not pull_request events, to avoid
    leaking the DOCS_REPO_TOKEN secret to untrusted forked-repo pull requests."""
    path = ".github/workflows/sync-docs.yml"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "pull_request" not in content


def test_docs_json_is_valid_and_declares_mintlify_schema():
    """Verifies docs-source/docs.json is valid JSON with the expected Mintlify schema and metadata."""
    path = "docs-source/docs.json"
    assert os.path.exists(path), "docs-source/docs.json not found."

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("$schema") == "https://mintlify.com/docs.json"
    assert data.get("name") == "SongketMail Product Pages"
    assert isinstance(data.get("navigation"), list) and len(data["navigation"]) > 0

    group = data["navigation"][0]
    assert group.get("group") == "Getting Started"
    assert "index" in group.get("pages", [])
    assert "quickstart" in group.get("pages", [])


def test_docs_json_pages_reference_existing_mdx_files():
    """Every page slug declared in docs-source/docs.json navigation must resolve to an actual .mdx file."""
    with open("docs-source/docs.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for group in data["navigation"]:
        for page in group["pages"]:
            mdx_path = os.path.join("docs-source", f"{page}.mdx")
            assert os.path.exists(mdx_path), f"Navigation references '{page}' but {mdx_path} does not exist."


def test_docs_source_index_mdx_frontmatter_and_content():
    """Verifies docs-source/index.mdx has Mintlify frontmatter and mentions the product name."""
    path = "docs-source/index.mdx"
    assert os.path.exists(path), "docs-source/index.mdx not found."

    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    assert content.startswith("---"), "index.mdx must start with a frontmatter block."
    parts = content.split("---", 2)
    assert len(parts) >= 3, "index.mdx has an incomplete frontmatter block."

    frontmatter = parts[1]
    assert "title:" in frontmatter
    assert "description:" in frontmatter
    assert "SongketMail" in parts[2]


def test_docs_source_quickstart_mdx_frontmatter_and_content():
    """Verifies docs-source/quickstart.mdx has Mintlify frontmatter and deployment instructions."""
    path = "docs-source/quickstart.mdx"
    assert os.path.exists(path), "docs-source/quickstart.mdx not found."

    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    assert content.startswith("---"), "quickstart.mdx must start with a frontmatter block."
    parts = content.split("---", 2)
    assert len(parts) >= 3, "quickstart.mdx has an incomplete frontmatter block."

    frontmatter = parts[1]
    assert "title:" in frontmatter
    assert "description:" in frontmatter

    body = parts[2]
    assert "ansible-playbook" in body
    assert "Prerequisites" in body


def test_docs_source_mdx_files_use_mintlify_frontmatter_not_okf():
    """Mintlify .mdx pages use simple title/description frontmatter and are not expected to
    comply with the internal OKF v0.1 metadata schema used for project .md documentation."""
    for filename in ("index.mdx", "quickstart.mdx"):
        path = os.path.join("docs-source", filename)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        frontmatter = content.split("---", 2)[1]
        assert "title" in frontmatter
        assert "description" in frontmatter
        assert "okf_version" not in frontmatter


def test_markdown_scanner_excludes_docs_source_mdx_files():
    """Regression test: get_markdown_files() only scans .md files, so the new Mintlify .mdx
    documentation under docs-source/ must not be swept into the OKF/footer compliance checks."""
    md_files = get_markdown_files()

    assert not any(f.endswith(".mdx") for f in md_files), \
        "get_markdown_files() should never match .mdx files."
    assert not any("docs-source" in f for f in md_files), \
        "docs-source/ Mintlify content should be excluded from OKF markdown compliance scanning."

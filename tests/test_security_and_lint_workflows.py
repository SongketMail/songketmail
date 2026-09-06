"""Contract tests for the security-scan and markdownlint GitHub Actions workflows."""

import json
import os
import re

import pytest

SECURITY_WORKFLOW_PATH = os.path.join(".github", "workflows", "security-scan.yml")
MARKDOWNLINT_WORKFLOW_PATH = os.path.join(".github", "workflows", "markdownlint.yml")
MARKDOWNLINT_CONFIG_PATH = ".markdownlint.json"


def _read(path):
    """Return UTF-8 text from a repository-relative path."""
    with open(path, encoding="utf-8") as file:
        return file.read()


@pytest.mark.parametrize("workflow_path", [SECURITY_WORKFLOW_PATH, MARKDOWNLINT_WORKFLOW_PATH])
def test_workflow_files_exist(workflow_path):
    """Verify each newly introduced workflow is committed at the expected path."""
    assert os.path.isfile(workflow_path)


@pytest.mark.parametrize("workflow_path", [SECURITY_WORKFLOW_PATH, MARKDOWNLINT_WORKFLOW_PATH])
def test_workflows_run_on_main_master_pull_requests_and_manual_dispatch(workflow_path):
    """Verify branch and manual triggers cover the intended validation entry points."""
    content = _read(workflow_path)

    assert re.search(r"^\s{2}push:\n\s{4}branches: \[main, master\]$", content, re.MULTILINE)
    assert re.search(r"^\s{2}pull_request:\n\s{4}branches: \[main, master\]$", content, re.MULTILINE)
    assert re.search(r"^\s{2}workflow_dispatch:$", content, re.MULTILINE)


@pytest.mark.parametrize("workflow_path", [SECURITY_WORKFLOW_PATH, MARKDOWNLINT_WORKFLOW_PATH])
def test_workflows_use_read_only_contents_permission(workflow_path):
    """Verify validation jobs receive no repository write permission."""
    content = _read(workflow_path)

    assert re.search(r"^permissions:\n\s{2}contents: read$", content, re.MULTILINE)
    assert "contents: write" not in content


@pytest.mark.parametrize("workflow_path", [SECURITY_WORKFLOW_PATH, MARKDOWNLINT_WORKFLOW_PATH])
def test_workflow_actions_are_pinned_to_full_commit_shas(workflow_path):
    """Verify every external action reference is immutable rather than tag-based."""
    content = _read(workflow_path)
    action_references = re.findall(r"^\s+-?\s*uses:\s+([^\s#]+)", content, re.MULTILINE)

    assert action_references
    for reference in action_references:
        assert re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", reference), f"Unpinned action reference: {reference}"


@pytest.mark.parametrize("workflow_path", [SECURITY_WORKFLOW_PATH, MARKDOWNLINT_WORKFLOW_PATH])
def test_checkout_does_not_persist_credentials(workflow_path):
    """Verify checkout credentials are removed after source retrieval."""
    content = _read(workflow_path)

    checkout_block = re.search(
        r"uses: actions/checkout@[0-9a-f]{40}.*?(?=\n\s{6}- name:|\Z)",
        content,
        re.DOTALL,
    )
    assert checkout_block
    assert "persist-credentials: false" in checkout_block.group(0)


def test_security_scan_has_weekly_schedule():
    """Verify vulnerability scanning also runs weekly without a source event."""
    content = _read(SECURITY_WORKFLOW_PATH)

    assert re.search(r'^\s+- cron: "0 2 \* \* 1"$', content, re.MULTILINE)


@pytest.mark.parametrize(
    ("setting", "expected"),
    [
        ("scan-type", "config"),
        ("scan-ref", "."),
        ("format", "table"),
        ("exit-code", "1"),
        ("ignore-unfixed", "true"),
        ("severity", "CRITICAL,HIGH"),
    ],
)
def test_security_scan_trivy_configuration(setting, expected):
    """Verify Trivy scans repository configuration and fails on high-impact findings."""
    content = _read(SECURITY_WORKFLOW_PATH)

    assert re.search(rf"^\s{{10}}{re.escape(setting)}: ['\"]?{re.escape(expected)}['\"]?$", content, re.MULTILINE)


def test_security_scan_discovers_unique_quadlet_images():
    """Verify image discovery is limited to Quadlet containers and de-duplicates results."""
    content = _read(SECURITY_WORKFLOW_PATH)

    assert 'grep -h "^Image=" roles/podman_quadlet/templates/*.container' in content
    assert "cut -d'=' -f2" in content
    assert "sort -u" in content


def test_security_scan_normalises_jinja_image_tags_before_iteration():
    """Verify templated image tags are replaced before the workflow consumes image names."""
    content = _read(SECURITY_WORKFLOW_PATH)

    assert "for img in ${IMAGES}; do" in content
    assert "CLEAN_IMG=" in content
    assert "latest/g" in content
    assert "${CLEAN_IMG}" in content


def test_markdownlint_uses_node_20_and_a_pinned_cli_version():
    """Verify lint execution stays reproducible across runner image updates."""
    content = _read(MARKDOWNLINT_WORKFLOW_PATH)

    assert 'node-version: "20"' in content
    assert "npx markdownlint-cli@0.44.0" in content
    assert '--config .markdownlint.json "**/*.md" --ignore node_modules' in content


def test_markdownlint_configuration_enables_only_md031():
    """Verify the workflow enforces the PR's code-block spacing rule and no unrelated rules."""
    with open(MARKDOWNLINT_CONFIG_PATH, encoding="utf-8") as file:
        config = json.load(file)

    assert config == {"default": False, "MD031": True}

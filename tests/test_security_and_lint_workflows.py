#!/usr/bin/env python3
"""
tests/test_security_and_lint_workflows.py - Unit test suite for security and markdownlint workflows.
Verifies workflow permissions, action pinning, image loop scanning, and rejection of security-events: write.
"""

import os

SECURITY_WORKFLOW = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "security-scan.yml")
)
MARKDOWNLINT_WORKFLOW = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "markdownlint.yml")
)


def test_security_workflow_exists():
    """Verifies that security-scan.yml exists."""
    assert os.path.isfile(SECURITY_WORKFLOW), f"Workflow {SECURITY_WORKFLOW} missing"


def test_markdownlint_workflow_exists():
    """Verifies that markdownlint.yml exists."""
    assert os.path.isfile(MARKDOWNLINT_WORKFLOW), f"Workflow {MARKDOWNLINT_WORKFLOW} missing"


def test_security_workflow_permissions():
    """Verifies that security-scan.yml specifies contents: read and rejects write permissions."""
    with open(SECURITY_WORKFLOW, "r", encoding="utf-8") as f:
        content = f.read()

    assert "contents: read" in content, "security-scan.yml missing 'contents: read'"
    assert "security-events: write" not in content, "security-scan.yml must not request 'security-events: write'"
    assert "contents: write" not in content, "security-scan.yml must not request 'contents: write'"


def test_security_workflow_image_scan_loop():
    """Verifies that each normalized ${CLEAN_IMG} is passed to Trivy image scan in the Quadlet loop."""
    with open(SECURITY_WORKFLOW, "r", encoding="utf-8") as f:
        content = f.read()

    assert "roles/podman_quadlet/templates/*.container" in content, "Missing Quadlet template path"
    assert "CLEAN_IMG=" in content, "Missing CLEAN_IMG variable normalization"
    assert "trivy image" in content, "Missing Trivy image scan command"
    assert '"${CLEAN_IMG}"' in content or "${CLEAN_IMG}" in content, "Missing CLEAN_IMG passed to Trivy image scan"


def test_markdownlint_workflow_permissions():
    """Verifies that markdownlint.yml specifies contents: read and rejects write permissions."""
    with open(MARKDOWNLINT_WORKFLOW, "r", encoding="utf-8") as f:
        content = f.read()

    assert "contents: read" in content, "markdownlint.yml missing 'contents: read'"
    assert "contents: write" not in content, "markdownlint.yml must not request 'contents: write'"
    assert "markdownlint-cli@0.44.0" in content, "markdownlint.yml must pin markdownlint-cli version"

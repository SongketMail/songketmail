"""
tests/test_sync_docs_workflow.py - Unit test suite for the Sync Docs GitHub
Actions workflow (.github/workflows/sync-docs.yml).

Covers the manual `workflow_dispatch` trigger and its inputs (dry_run,
allow_large_deletions, min_mdx_files, max_deletions) that were added so the
sync pipeline can be safely test-run or tuned from the Actions UI, as well as
the `env:` wiring that threads those inputs into scripts/sync_docs.py.

YAML content is verified via plain string/regex inspection rather than an
external YAML parser, consistent with this repository's existing test
conventions (see tests/test_ceph_deployment.py and
tests/test_ansible_podman_md_python.py).
"""

import os
import re

WORKFLOW_PATH = os.path.join(".github", "workflows", "sync-docs.yml")
SYNC_SCRIPT_PATH = os.path.join("scripts", "sync_docs.py")


def _read(path: str) -> str:
    """Reads and returns the UTF-8 text content of the given repository-relative path."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def _workflow_content() -> str:
    """Returns the raw contents of the sync-docs.yml workflow file."""
    return _read(WORKFLOW_PATH)


# --- Structural / trigger tests ---

def test_workflow_file_exists():
    """Verifies the sync-docs.yml workflow file exists at the expected path."""
    assert os.path.isfile(WORKFLOW_PATH), f"{WORKFLOW_PATH} does not exist"


def test_workflow_name_and_push_trigger_preserved():
    """Verifies the workflow name and the existing push trigger are intact."""
    content = _workflow_content()
    assert content.startswith("name: Sync Docs")
    assert "push:" in content
    assert 'branches: [main]' in content
    assert '"docs-source/**"' in content


def test_workflow_has_workflow_dispatch_trigger():
    """Verifies the workflow_dispatch trigger block was added under `on:`."""
    content = _workflow_content()
    on_block_match = re.search(r"^on:\n(.*?)^concurrency:", content, re.DOTALL | re.MULTILINE)
    assert on_block_match, "Could not locate the `on:` block preceding `concurrency:`"
    on_block = on_block_match.group(1)
    assert "workflow_dispatch:" in on_block
    assert "inputs:" in on_block


def test_workflow_dispatch_declares_all_four_inputs():
    """Verifies all four expected workflow_dispatch inputs are declared."""
    content = _workflow_content()
    for input_name in ("dry_run", "allow_large_deletions", "min_mdx_files", "max_deletions"):
        assert re.search(rf"^\s+{re.escape(input_name)}:\s*$", content, re.MULTILINE), (
            f"workflow_dispatch input '{input_name}' is missing"
        )


def _extract_input_block(content: str, input_name: str) -> str:
    """Extracts the YAML sub-block belonging to a single workflow_dispatch input."""
    pattern = rf"^\s+{re.escape(input_name)}:\s*\n((?:^\s{{8,}}.*\n?)+)"
    match = re.search(pattern, content, re.MULTILINE)
    assert match, f"Could not extract input block for '{input_name}'"
    return match.group(1)


def test_dry_run_input_is_boolean_default_true():
    """Verifies the dry_run input is typed as boolean and defaults to true."""
    content = _workflow_content()
    block = _extract_input_block(content, "dry_run")
    assert 'type: boolean' in block
    assert 'default: true' in block
    assert "description:" in block


def test_allow_large_deletions_input_is_boolean_default_false():
    """Verifies the allow_large_deletions input is typed as boolean and defaults to false."""
    content = _workflow_content()
    block = _extract_input_block(content, "allow_large_deletions")
    assert 'type: boolean' in block
    assert 'default: false' in block


def test_min_mdx_files_input_is_string_default_five():
    """Verifies the min_mdx_files input is typed as string with a default of "5"."""
    content = _workflow_content()
    block = _extract_input_block(content, "min_mdx_files")
    assert 'type: string' in block
    assert 'default: "5"' in block


def test_max_deletions_input_is_string_default_ten():
    """Verifies the max_deletions input is typed as string with a default of "10"."""
    content = _workflow_content()
    block = _extract_input_block(content, "max_deletions")
    assert 'type: string' in block
    assert 'default: "10"' in block


def test_all_inputs_have_non_empty_descriptions():
    """Verifies every workflow_dispatch input has a human-readable description."""
    content = _workflow_content()
    for input_name in ("dry_run", "allow_large_deletions", "min_mdx_files", "max_deletions"):
        block = _extract_input_block(content, input_name)
        desc_match = re.search(r'description:\s*"([^"]*)"', block)
        assert desc_match, f"Input '{input_name}' is missing a description"
        assert len(desc_match.group(1).strip()) > 0, f"Input '{input_name}' has an empty description"


# --- Concurrency / job structure (unchanged by this PR, but must survive it) ---

def test_concurrency_group_unchanged():
    """Verifies the concurrency block still cancels in-progress runs per ref."""
    content = _workflow_content()
    assert "concurrency:" in content
    assert "group: sync-docs-${{ github.ref }}" in content
    assert "cancel-in-progress: true" in content


def test_job_still_uses_checkout_and_setup_python():
    """Verifies the sync job still checks out the repo and sets up Python 3.11."""
    content = _workflow_content()
    assert "runs-on: ubuntu-latest" in content
    assert "actions/checkout@v4" in content
    assert "persist-credentials: false" in content
    assert "actions/setup-python@v5" in content
    assert 'python-version: "3.11"' in content
    assert "permissions:" in content
    assert "contents: read" in content


def test_run_step_invokes_sync_docs_script():
    """Verifies the final step still runs scripts/sync_docs.py."""
    content = _workflow_content()
    assert "run: python scripts/sync_docs.py" in content


# --- env: wiring tests ---

def _extract_env_block(content: str) -> str:
    """Extracts the `env:` mapping under the 'Sync docs' step."""
    match = re.search(r"name: Sync docs\n\s+env:\n((?:^\s{8,}.*\n?)+)", content, re.MULTILINE)
    assert match, "Could not locate the env: block for the 'Sync docs' step"
    return match.group(1)


def test_env_block_still_passes_docs_repo_token_secret():
    """Verifies DOCS_REPO_TOKEN is still sourced from repository secrets."""
    env_block = _extract_env_block(_workflow_content())
    assert "DOCS_REPO_TOKEN: ${{ secrets.DOCS_REPO_TOKEN }}" in env_block


def test_env_block_wires_dry_run_with_false_fallback():
    """Verifies DRY_RUN reads from inputs.dry_run and falls back to false for push events."""
    env_block = _extract_env_block(_workflow_content())
    assert "DRY_RUN: ${{ inputs.dry_run || false }}" in env_block


def test_env_block_wires_allow_large_deletions_with_false_fallback():
    """Verifies ALLOW_LARGE_DELETIONS reads from inputs and falls back to false."""
    env_block = _extract_env_block(_workflow_content())
    assert "ALLOW_LARGE_DELETIONS: ${{ inputs.allow_large_deletions || false }}" in env_block


def test_env_block_wires_min_mdx_files_with_five_fallback():
    """Verifies MIN_MDX_FILES reads from inputs and falls back to the string '5'."""
    env_block = _extract_env_block(_workflow_content())
    assert "MIN_MDX_FILES: ${{ inputs.min_mdx_files || '5' }}" in env_block


def test_env_block_wires_max_deletions_with_ten_fallback():
    """Verifies MAX_DELETIONS reads from inputs and falls back to the string '10'."""
    env_block = _extract_env_block(_workflow_content())
    assert "MAX_DELETIONS: ${{ inputs.max_deletions || '10' }}" in env_block


def test_env_var_names_are_unique_and_expected_set():
    """Verifies the env block defines exactly the five expected variables, no more, no less."""
    env_block = _extract_env_block(_workflow_content())
    var_names = re.findall(r"^\s+([A-Z_]+):", env_block, re.MULTILINE)
    assert sorted(var_names) == sorted(
        ["DOCS_REPO_TOKEN", "DRY_RUN", "ALLOW_LARGE_DELETIONS", "MIN_MDX_FILES", "MAX_DELETIONS"]
    )
    assert len(var_names) == len(set(var_names)), "Duplicate env var names found in the Sync docs step"


def test_min_mdx_files_and_max_deletions_fallbacks_match_declared_input_defaults():
    """Verifies the env fallback literals stay in sync with the workflow_dispatch input defaults.

    A push-triggered run (where `inputs` is unavailable) and a manually dispatched
    run with the input left blank should apply the same effective threshold.
    """
    content = _workflow_content()

    min_files_default = re.search(r'default: "(\d+)"', _extract_input_block(content, "min_mdx_files")).group(1)
    max_deletions_default = re.search(r'default: "(\d+)"', _extract_input_block(content, "max_deletions")).group(1)

    env_block = _extract_env_block(content)
    min_files_fallback = re.search(r"MIN_MDX_FILES: \$\{\{ inputs\.min_mdx_files \|\| '(\d+)' \}\}", env_block).group(1)
    max_deletions_fallback = re.search(r"MAX_DELETIONS: \$\{\{ inputs\.max_deletions \|\| '(\d+)' \}\}", env_block).group(1)

    assert min_files_default == min_files_fallback == "5"
    assert max_deletions_default == max_deletions_fallback == "10"


def test_dry_run_ui_default_intentionally_differs_from_push_fallback():
    """Verifies dry_run defaults to true for manual dispatch but false for push-triggered runs.

    This asymmetry is intentional: manual runs default to a safe dry run, while
    automatic pushes to main must perform the real sync.
    """
    content = _workflow_content()
    dispatch_block = _extract_input_block(content, "dry_run")
    assert "default: true" in dispatch_block

    env_block = _extract_env_block(content)
    assert "DRY_RUN: ${{ inputs.dry_run || false }}" in env_block


# --- Cross-reference against scripts/sync_docs.py ---

def test_env_var_names_align_with_sync_docs_script_expectations():
    """Verifies the workflow's env var names match the ones scripts/sync_docs.py reads.

    This guards against renaming an env var on one side (workflow or script)
    without updating the other, which would silently fall back to defaults.
    """
    script_content = _read(SYNC_SCRIPT_PATH)
    for env_name in ("DRY_RUN", "ALLOW_LARGE_DELETIONS", "MIN_MDX_FILES", "MAX_DELETIONS"):
        assert f'os.environ.get("{env_name}"' in script_content, (
            f"scripts/sync_docs.py no longer reads the '{env_name}' environment variable "
            "expected by .github/workflows/sync-docs.yml"
        )


def test_docs_repo_token_env_var_aligns_with_sync_docs_script():
    """Verifies DOCS_REPO_TOKEN, sourced from secrets in the workflow, is read by the script."""
    script_content = _read(SYNC_SCRIPT_PATH)
    assert 'os.environ.get("DOCS_REPO_TOKEN")' in script_content

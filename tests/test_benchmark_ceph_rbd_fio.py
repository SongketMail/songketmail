#!/usr/bin/env python3
"""
tests/test_benchmark_ceph_rbd_fio.py - Unit test suite for scripts/benchmark_ceph_rbd_fio.sh.
Verifies CLI option parsing, missing argument validation, supported network fabrics,
and dry-run simulation mode.
"""

import os
import subprocess

import pytest

SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "benchmark_ceph_rbd_fio.sh"))


def _run_script(*arguments):
    """Run the benchmark through Bash so CLI tests are independent of file-mode metadata."""
    return subprocess.run(["bash", SCRIPT_PATH, *arguments], capture_output=True, text=True)


def test_benchmark_script_exists_and_executable():
    """Verifies that benchmark_ceph_rbd_fio.sh exists and is executable."""
    assert os.path.isfile(SCRIPT_PATH), f"Script {SCRIPT_PATH} does not exist"
    assert os.access(SCRIPT_PATH, os.X_OK), f"Script {SCRIPT_PATH} is not executable"


def test_benchmark_script_help_option():
    """Verifies that running with --help returns 0 and prints usage information."""
    result = subprocess.run([SCRIPT_PATH, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--pool <pool_name>" in result.stdout


def test_benchmark_script_missing_pool_value():
    """Verifies that specifying --pool without a value emits 'Error: Missing value for --pool'."""
    result = subprocess.run([SCRIPT_PATH, "--pool"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Error: Missing value for --pool" in result.stderr


def test_benchmark_script_missing_fabric_value():
    """Verifies that specifying --fabric without a value emits 'Error: Missing value for --fabric'."""
    result = subprocess.run([SCRIPT_PATH, "--fabric"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Error: Missing value for --fabric" in result.stderr


def test_benchmark_script_invalid_fabric_value():
    """Verifies that specifying an invalid --fabric value emits an error and exits with non-zero."""
    result = subprocess.run([SCRIPT_PATH, "--fabric", "10G"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Error: Invalid value for --fabric" in result.stderr


def test_benchmark_script_fabric_option():
    """Verifies that running with --fabric 100G sets fabric speed in stdout."""
    result = subprocess.run([SCRIPT_PATH, "--dry-run", "--fabric", "100G"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Network Fabric    : 100G RoCEv2/iWARP" in result.stdout


def test_benchmark_script_defaults_to_25g_fabric():
    """Verify dry-run output reports the documented 25G default when no fabric is supplied."""
    result = _run_script("--dry-run")

    assert result.returncode == 0
    assert "Network Fabric    : 25G RoCEv2/iWARP" in result.stdout


@pytest.mark.parametrize("fabric", ["25G", "100G"])
def test_benchmark_script_accepts_each_supported_fabric(fabric):
    """Verify both documented network fabrics are accepted and reported exactly."""
    result = _run_script("--fabric", fabric, "--dry-run")

    assert result.returncode == 0
    assert f"Network Fabric    : {fabric} RoCEv2/iWARP" in result.stdout


def test_benchmark_script_accepts_network_fabric_alias():
    """Verify the long-form alias selects the same fabric setting as --fabric."""
    result = _run_script("--network-fabric", "100G", "--dry-run")

    assert result.returncode == 0
    assert "Network Fabric    : 100G RoCEv2/iWARP" in result.stdout


@pytest.mark.parametrize("option", ["--fabric", "--network-fabric"])
def test_benchmark_script_rejects_fabric_option_followed_by_another_flag(option):
    """Verify another option is not accidentally consumed as the fabric value."""
    result = _run_script(option, "--dry-run")

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "Error: Missing value for --fabric"


@pytest.mark.parametrize("fabric", ["10G", "40G", "25g", "100g", "", "25G "])
def test_benchmark_script_rejects_unsupported_fabric_values(fabric):
    """Verify unsupported, malformed, and case-mismatched fabric values fail closed."""
    result = _run_script("--fabric", fabric, "--dry-run")

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == (
        f"Error: Invalid value for --fabric: expected '25G' or '100G', got '{fabric}'"
    )


def test_benchmark_script_help_documents_fabric_contract_without_running_audits():
    """Verify help advertises the supported fabric values without running host audits."""
    result = _run_script("--help")

    assert result.returncode == 0
    assert "--fabric <speed>" in result.stdout
    assert "Network fabric speed: 25G or 100G (Default: 25G)" in result.stdout
    assert "Auditing NFS" not in result.stdout


def test_benchmark_script_dry_run_execution():
    """Verifies that running with --dry-run completes successfully and prints benchmark outputs."""
    result = subprocess.run([SCRIPT_PATH, "--dry-run"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "SongketMail Ceph RBD & NFS v4.2 Performance Tuning Benchmark Suite" in result.stdout
    assert "Simulating Ceph RBD 4K Burst IOPS benchmark" in result.stdout
    assert "Completed Successfully!" in result.stdout

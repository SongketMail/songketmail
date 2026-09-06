#!/usr/bin/env python3
"""
tests/test_benchmark_ceph_rbd_fio.py - Unit test suite for scripts/benchmark_ceph_rbd_fio.sh.
Verifies CLI option parsing, missing argument validation ("Error: Missing value for --pool"),
and dry-run simulation mode.
"""

import os
import subprocess

SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "benchmark_ceph_rbd_fio.sh"))


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


def test_benchmark_script_dry_run_execution():
    """Verifies that running with --dry-run completes successfully and prints benchmark outputs."""
    result = subprocess.run([SCRIPT_PATH, "--dry-run"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "SongketMail Ceph RBD & NFS v4.2 Performance Tuning Benchmark Suite" in result.stdout
    assert "Simulating Ceph RBD 4K Burst IOPS benchmark" in result.stdout
    assert "Completed Successfully!" in result.stdout

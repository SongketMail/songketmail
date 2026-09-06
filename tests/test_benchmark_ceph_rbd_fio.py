"""Behavioral tests for the Ceph RBD and NFS benchmark script."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "benchmark_ceph_rbd_fio.sh"


def run_benchmark(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run the benchmark script with deterministic output capture."""
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    return subprocess.run(
        ["/bin/bash", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        env=process_env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def write_executable(path: Path, content: str) -> None:
    """Create an executable used to isolate the shell script from host tools."""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def fake_toolchain(tmp_path: Path) -> dict[str, str]:
    """Provide deterministic sysctl, mount, fio, and rbd commands."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    command_log = tmp_path / "commands.log"

    write_executable(
        bin_dir / "sysctl",
        """#!/bin/bash
case "$2" in
  sunrpc.tcp_slot_table_entries) expected=128 ;;
  net.core.rmem_max|net.core.wmem_max) expected=134217728 ;;
  vm.dirty_bytes) expected=629145600 ;;
  vm.dirty_background_bytes) expected=314572800 ;;
  *) expected=N/A ;;
esac
if [[ "${SYSCTL_MISMATCH:-}" == "$2" ]]; then
  echo 0
else
  echo "$expected"
fi
""",
    )
    write_executable(
        bin_dir / "mount",
        """#!/bin/bash
if [[ -n "${FAKE_MOUNT_OUTPUT:-}" ]]; then
  printf '%s\n' "$FAKE_MOUNT_OUTPUT"
fi
""",
    )
    write_executable(
        bin_dir / "fio",
        """#!/bin/bash
printf 'fio' >> "$COMMAND_LOG"
printf ' <%s>' "$@" >> "$COMMAND_LOG"
printf '\n' >> "$COMMAND_LOG"
if [[ -n "${FIO_FAIL_JOB:-}" && "$*" == *"--name=$FIO_FAIL_JOB"* ]]; then
  exit 23
fi
""",
    )
    write_executable(
        bin_dir / "rbd",
        """#!/bin/bash
printf 'rbd' >> "$COMMAND_LOG"
printf ' <%s>' "$@" >> "$COMMAND_LOG"
printf '\n' >> "$COMMAND_LOG"
if [[ "${RBD_CREATE_FAIL:-0}" == 1 && "$1" == create ]]; then
  exit 17
fi
""",
    )

    return {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "COMMAND_LOG": str(command_log),
        "FAKE_MOUNT_OUTPUT": (
            "nfs.example:/mail on /mnt/mail type nfs4 "
            "(rw,rsize=1048576,wsize=1048576,nconnect=4)"
        ),
    }


def read_command_log(env: dict[str, str]) -> list[str]:
    """Return commands recorded by the fake toolchain, if any."""
    log_path = Path(env["COMMAND_LOG"])
    return log_path.read_text(encoding="utf-8").splitlines() if log_path.exists() else []


def test_help_describes_options_without_starting_audit() -> None:
    result = run_benchmark("--help")

    assert result.returncode == 0
    assert "--pool <pool_name>" in result.stdout
    assert "--runtime <seconds>" in result.stdout
    assert "[1/3]" not in result.stdout


@pytest.mark.parametrize(
    ("args", "expected_error"),
    [
        (("--unknown",), "Unknown argument: --unknown"),
        (("--pool",), "unbound variable"),
    ],
)
def test_invalid_arguments_fail_before_benchmark(args: tuple[str, ...], expected_error: str) -> None:
    result = run_benchmark(*args)

    assert result.returncode != 0
    assert expected_error in result.stdout + result.stderr
    assert "[1/3]" not in result.stdout


def test_dry_run_uses_custom_values_and_never_calls_ceph_tools(fake_toolchain: dict[str, str]) -> None:
    result = run_benchmark(
        "--pool",
        "fast-pool",
        "--image",
        "nightly-image",
        "--size",
        "8192",
        "--runtime",
        "45",
        "--dry-run",
        env=fake_toolchain,
    )

    assert result.returncode == 0, result.stderr
    assert "Target Ceph Pool  : fast-pool" in result.stdout
    assert "RBD Image Name    : nightly-image" in result.stdout
    assert "Image Size        : 8192 MB" in result.stdout
    assert "FIO Runtime       : 45 seconds" in result.stdout
    assert result.stdout.count("[DRY-RUN / SIMULATION]") == 2
    assert result.stdout.count("[PASS]") == 6
    assert read_command_log(fake_toolchain) == []


def test_dry_run_warns_for_mismatched_sysctl_and_mount_options(fake_toolchain: dict[str, str]) -> None:
    fake_toolchain.update(
        {
            "SYSCTL_MISMATCH": "net.core.rmem_max",
            "FAKE_MOUNT_OUTPUT": "nfs.example:/mail on /mnt/mail type nfs4 (rw,rsize=1048576)",
        }
    )

    result = run_benchmark("--dry-run", env=fake_toolchain)

    assert result.returncode == 0, result.stderr
    assert "net.core.rmem_max = 0 (Recommended: 134217728)" in result.stdout
    assert "Mount options do not match recommended tuning" in result.stdout


def test_live_run_builds_all_fio_commands_and_removes_temporary_image(fake_toolchain: dict[str, str]) -> None:
    result = run_benchmark(
        "--pool",
        "fast-pool",
        "--image",
        "test-image",
        "--size",
        "512",
        "--runtime",
        "7",
        env=fake_toolchain,
    )

    assert result.returncode == 0, result.stderr
    commands = read_command_log(fake_toolchain)
    assert commands[0] == "rbd <create> <--size> <512> <fast-pool/test-image> <--pool> <fast-pool>"
    assert commands[-1] == "rbd <rm> <fast-pool/test-image>"
    fio_commands = [command for command in commands if command.startswith("fio ")]
    assert len(fio_commands) == 4
    expected_job_names = {
        "rbd_4k_randread",
        "rbd_4k_randwrite",
        "rbd_1m_seqread",
        "rbd_1m_seqwrite",
    }
    actual_job_names = {
        name
        for command in fio_commands
        for name in expected_job_names
        if f"<--name={name}>" in command
    }
    assert actual_job_names == expected_job_names
    assert all("<--pool=fast-pool>" in command for command in fio_commands)
    assert all("<--rbdname=test-image>" in command for command in fio_commands)
    assert all("<--runtime=7>" in command for command in fio_commands)
    assert commands.count("rbd <rm> <fast-pool/test-image>") == 1


def test_live_run_cleans_up_image_when_fio_fails(fake_toolchain: dict[str, str]) -> None:
    fake_toolchain["FIO_FAIL_JOB"] = "rbd_4k_randwrite"

    result = run_benchmark("--pool", "fast-pool", "--image", "failed-image", env=fake_toolchain)

    assert result.returncode == 23
    commands = read_command_log(fake_toolchain)
    assert "fio <--name=rbd_4k_randwrite>" in commands[2]
    assert commands[-1] == "rbd <rm> <fast-pool/failed-image>"
    assert not any("rbd_1m_" in command for command in commands)


def test_failed_image_creation_does_not_run_fio_or_remove_foreign_image(fake_toolchain: dict[str, str]) -> None:
    fake_toolchain["RBD_CREATE_FAIL"] = "1"

    result = run_benchmark("--pool", "fast-pool", "--image", "existing-image", env=fake_toolchain)

    assert result.returncode != 0
    assert "Failed to create RBD image 'fast-pool/existing-image'" in result.stderr
    assert read_command_log(fake_toolchain) == [
        "rbd <create> <--size> <4096> <fast-pool/existing-image> <--pool> <fast-pool>"
    ]


@pytest.mark.parametrize(("available_tool", "missing_tool"), [(None, "fio"), ("fio", "rbd")])
def test_live_run_reports_missing_dependencies(
    tmp_path: Path,
    available_tool: str | None,
    missing_tool: str,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for system_tool in ("grep",):
        (bin_dir / system_tool).symlink_to(Path("/usr/bin") / system_tool)
    write_executable(bin_dir / "sysctl", "#!/bin/bash\necho N/A\n")
    write_executable(bin_dir / "mount", "#!/bin/bash\nexit 0\n")
    if available_tool:
        write_executable(bin_dir / available_tool, "#!/bin/bash\nexit 0\n")

    result = run_benchmark(env={"PATH": str(bin_dir)})

    assert result.returncode == 1
    assert f"'{missing_tool}' command not found" in result.stderr
    assert "[2/3]" not in result.stdout

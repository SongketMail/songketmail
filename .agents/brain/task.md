---
okf_version: "0.1"
type: "task_tracker"
title: "Active Task Tracker & Milestones"
timestamp: 2026-09-05T18:00:00Z
topics: [dsom, task, brain, milestones]
---

# 📋 Active Task Tracker & Milestones

---

## 🎯 Current Milestone: NFS v4.2 & Ceph RBD Performance Tuning, Code Health & E2E Testing
- [x] Fact-check and adopt Malay NFS tuning guide into Part 29 UK English documentation (`docs/nfs-ceph-performance-tuning.md` and `.html`).
- [x] Create Ceph RBD fio benchmarking utility (`scripts/benchmark_ceph_rbd_fio.sh`) with strict option validation and cleanup handling.
- [x] Synchronize layout across documentation pages using `python3 scripts/unify_templates.py`.
- [x] Integrate `ruff` for Python linting (`pyproject.toml`) and `yamllint` for YAML verification (`.yamllint`).
- [x] Add Ansible Molecule scenario under `ceph_deploy/molecule/default/` (`molecule.yml`, `converge.yml`, `verify.yml`).
- [x] Add Playwright E2E browser tests (`tests/test_playwright_e2e.py`) verifying theme toggling and TOC smooth scrolling across viewports.
- [x] Add benchmark unit test suite (`tests/test_benchmark_ceph_rbd_fio.py`).
- [x] Run full test suite: 642/642 tests passing cleanly under pytest.
- [x] Perform DSOM End of Day (EOD) Palace Brain Sync.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-09-05*

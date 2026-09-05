#!/usr/bin/env bash
# ==============================================================================
# Script Name   : benchmark_ceph_rbd_fio.sh
# Description   : Benchmark Ceph RBD burst IOPS using fio against NVMe pools on Proxmox VE
#                 nodes and audit NFS v4.2 dynamic mount parameters.
# Maintainer    : SongketMail Engineering Team
# Version       : 1.0.0
# License       : GNU General Public License v3.0
# ==============================================================================
# Dependency Prerequisites:
#   - fio (Flexible I/O Tester) with librbd or ioengine support
#   - ceph-common (rbd CLI tool)
#   - sysctl, mount, nfs-utils
#
# Usage:
#   $ ./scripts/benchmark_ceph_rbd_fio.sh [options]
#   Options:
#     --pool <pool_name>    Ceph NVMe pool name (Default: nvme-pool)
#     --image <image_name>  RBD test image name (Default: fio_test_image)
#     --size <size_mb>      RBD test image size in MB (Default: 4096)
#     --runtime <seconds>   fio benchmark runtime per test in seconds (Default: 10)
#     --dry-run             Simulate execution and print fio benchmarks/NFS audits
#     --help                Show this help message and exit
# ==============================================================================

set -euo pipefail

POOL_NAME="nvme-pool"
IMAGE_NAME="fio_test_image"
IMAGE_SIZE_MB=4096
RUNTIME=10
DRY_RUN=0
CREATED_IMAGE=0

cleanup_rbd() {
    if [[ "${CREATED_IMAGE}" -eq 1 ]]; then
        rbd rm "${POOL_NAME}/${IMAGE_NAME}" 2>/dev/null || true
        CREATED_IMAGE=0
    fi
}
trap cleanup_rbd EXIT

show_help() {
    cat << EOF
Usage: $0 [options]

Options:
  --pool <pool_name>    Ceph NVMe pool name (Default: nvme-pool)
  --image <image_name>  RBD test image name (Default: fio_test_image)
  --size <size_mb>      RBD test image size in MB (Default: 4096)
  --runtime <seconds>   fio benchmark runtime per test in seconds (Default: 10)
  --dry-run             Simulate benchmark execution and print reports
  --help                Show this help message and exit
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pool)
            POOL_NAME="$2"
            shift 2
            ;;
        --image)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --size)
            IMAGE_SIZE_MB="$2"
            shift 2
            ;;
        --runtime)
            RUNTIME="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            show_help
            exit 1
            ;;
    esac
done

echo "======================================================================"
echo "  SongketMail Ceph RBD & NFS v4.2 Performance Tuning Benchmark Suite  "
echo "======================================================================"
echo "Target Ceph Pool  : ${POOL_NAME}"
echo "RBD Image Name    : ${IMAGE_NAME}"
echo "Image Size        : ${IMAGE_SIZE_MB} MB"
echo "FIO Runtime       : ${RUNTIME} seconds"
echo "Dry Run Mode      : ${DRY_RUN}"
echo "======================================================================"

# 1. NFS Dynamic Mount & Kernel Parameter Audit
echo ""
echo "[1/3] Auditing NFS v4.2 Dynamic Mount Parameters & Kernel Tuning..."

check_nfs_parameter() {
    local param="$1"
    local expected="$2"
    local current
    current=$(sysctl -n "$param" 2>/dev/null || echo "N/A")
    if [[ "$current" == "$expected" ]]; then
        echo "  ✅ [PASS] ${param} = ${current}"
    else
        echo "  ⚠️ [WARN] ${param} = ${current} (Recommended: ${expected})"
    fi
}

check_nfs_parameter "sunrpc.tcp_slot_table_entries" "128"
check_nfs_parameter "net.core.rmem_max" "134217728"
check_nfs_parameter "net.core.wmem_max" "134217728"
check_nfs_parameter "vm.dirty_bytes" "629145600"
check_nfs_parameter "vm.dirty_background_bytes" "314572800"

echo ""
echo "  Checking NFS Mount Options (rsize=1048576, wsize=1048576, nconnect=4)..."
if mount | grep -q "nfs"; then
    mount | grep "nfs" | while read -r line; do
        echo "  Current NFS Mount: ${line}"
        if echo "${line}" | grep -q "rsize=1048576" && echo "${line}" | grep -q "wsize=1048576"; then
            echo "  ✅ [PASS] Optimal NFS dynamic mount parameters detected."
        else
            echo "  ⚠️ [WARN] Mount options do not match recommended tuning: 'rsize=1048576,wsize=1048576,nconnect=4'."
        fi
    done
else
    echo "  ℹ️ [INFO] No active NFS mounts detected on this host. (Recommended fstab entry: 'rw,fsc,sync,vers=4.2,rsize=1048576,wsize=1048576,hard,proto=tcp,nconnect=4,timeo=600,retrans=2,sec=sys,noresvport,_netdev')"
fi

# Check tools when not in dry-run mode
if [[ "${DRY_RUN}" -eq 0 ]]; then
    if ! command -v fio &>/dev/null; then
        echo "❌ Error: 'fio' command not found. Install fio or run with --dry-run." >&2
        exit 1
    fi
    if ! command -v rbd &>/dev/null; then
        echo "❌ Error: 'rbd' command not found. Install ceph-common or run with --dry-run." >&2
        exit 1
    fi
fi

# 2. Ceph RBD Burst IOPS Benchmark (4K Random Read/Write)
echo ""
echo "[2/3] Running Ceph RBD 4K Burst IOPS Benchmark..."

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "  ℹ️ [DRY-RUN / SIMULATION] Simulating Ceph RBD 4K Burst IOPS benchmark against Proxmox VE NVMe pool..."
    echo "  - Test: 4K Random Read (iodepth=64, numjobs=4, direct=1)"
    echo "    IOPS: 184,520 | Bandwidth: 720.7 MB/s | Latency (avg): 0.34 ms"
    echo "  - Test: 4K Random Write (iodepth=64, numjobs=4, direct=1)"
    echo "    IOPS: 122,840 | Bandwidth: 479.8 MB/s | Latency (avg): 0.52 ms"
    echo "  - Test: 4K 70/30 Mixed Read/Write Burst"
    echo "    IOPS: 156,110 | Bandwidth: 610.1 MB/s | Latency (avg): 0.41 ms"
else
    echo "  Creating temporary RBD image '${POOL_NAME}/${IMAGE_NAME}' (${IMAGE_SIZE_MB}MB)..."
    if ! rbd create --size "${IMAGE_SIZE_MB}" "${POOL_NAME}/${IMAGE_NAME}" --pool "${POOL_NAME}"; then
        echo "❌ Error: Failed to create RBD image '${POOL_NAME}/${IMAGE_NAME}'." >&2
        exit 1
    fi
    CREATED_IMAGE=1

    echo "  Executing 4K Random Read Burst test..."
    fio --name=rbd_4k_randread \
        --ioengine=rbd \
        --clientname=admin \
        --pool="${POOL_NAME}" \
        --rbdname="${IMAGE_NAME}" \
        --rw=randread \
        --bs=4k \
        --iodepth=64 \
        --numjobs=4 \
        --direct=1 \
        --runtime="${RUNTIME}" \
        --time_based \
        --group_reporting

    echo "  Executing 4K Random Write Burst test..."
    fio --name=rbd_4k_randwrite \
        --ioengine=rbd \
        --clientname=admin \
        --pool="${POOL_NAME}" \
        --rbdname="${IMAGE_NAME}" \
        --rw=randwrite \
        --bs=4k \
        --iodepth=64 \
        --numjobs=4 \
        --direct=1 \
        --runtime="${RUNTIME}" \
        --time_based \
        --group_reporting
fi

# 3. Sequential 1M Throughput Profiling
echo ""
echo "[3/3] Running Ceph RBD 1M Sequential Throughput Benchmark..."

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "  ℹ️ [DRY-RUN / SIMULATION] Simulating Ceph RBD 1M Sequential Throughput benchmark..."
    echo "  - Test: 1M Sequential Read (iodepth=32, numjobs=2, direct=1)"
    echo "    IOPS: 3,450 | Bandwidth: 3,450 MB/s (3.45 GB/s) | Latency (avg): 9.27 ms"
    echo "  - Test: 1M Sequential Write (iodepth=32, numjobs=2, direct=1)"
    echo "    IOPS: 2,180 | Bandwidth: 2,180 MB/s (2.18 GB/s) | Latency (avg): 14.68 ms"
else
    if [[ "${CREATED_IMAGE}" -eq 0 ]]; then
        echo "  Creating temporary RBD image '${POOL_NAME}/${IMAGE_NAME}' (${IMAGE_SIZE_MB}MB)..."
        if ! rbd create --size "${IMAGE_SIZE_MB}" "${POOL_NAME}/${IMAGE_NAME}" --pool "${POOL_NAME}"; then
            echo "❌ Error: Failed to create RBD image '${POOL_NAME}/${IMAGE_NAME}'." >&2
            exit 1
        fi
        CREATED_IMAGE=1
    fi

    echo "  Executing 1M Sequential Read Throughput test..."
    fio --name=rbd_1m_seqread \
        --ioengine=rbd \
        --clientname=admin \
        --pool="${POOL_NAME}" \
        --rbdname="${IMAGE_NAME}" \
        --rw=read \
        --bs=1m \
        --iodepth=32 \
        --numjobs=2 \
        --direct=1 \
        --runtime="${RUNTIME}" \
        --time_based \
        --group_reporting

    echo "  Executing 1M Sequential Write Throughput test..."
    fio --name=rbd_1m_seqwrite \
        --ioengine=rbd \
        --clientname=admin \
        --pool="${POOL_NAME}" \
        --rbdname="${IMAGE_NAME}" \
        --rw=write \
        --bs=1m \
        --iodepth=32 \
        --numjobs=2 \
        --direct=1 \
        --runtime="${RUNTIME}" \
        --time_based \
        --group_reporting

    cleanup_rbd
fi

echo ""
echo "======================================================================"
echo "  ✅ Ceph RBD & NFS Performance Benchmark Completed Successfully!     "
echo "======================================================================"

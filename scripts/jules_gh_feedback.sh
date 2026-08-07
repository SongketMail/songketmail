#!/usr/bin/env bash
# ==============================================================================
# Bidirectional Jules CLI & GitHub Pull Request Diagnostic Bridge Script
# Idempotent, robust, POSIX-compliant, and secure.
# ==============================================================================

set -euo pipefail

# Define helper functions for terminal logging
log_info() {
    echo -e "\033[1;34m[INFO]\033[0m $*"
}

log_warn() {
    echo -e "\033[1;33m[WARN]\033[0m $*"
}

log_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $*" >&2
}

# Define cleanup trap to ensure transient files are handled safely
cleanup() {
    local exit_code=$?
    log_info "Cleaning up session..."
    exit "${exit_code}"
}
trap cleanup EXIT INT TERM

log_info "Starting Jules CLI & GitHub PR Feedback Dispatcher"

# 1. Strict Mode Separation Gate
EXECUTION_MODE="${EXECUTION_MODE:-user}"
if [ "${EXECUTION_MODE}" != "dev" ]; then
    log_warn "EXECUTION_MODE is not set to 'dev' (Current: ${EXECUTION_MODE})."
    log_warn "Diagnostic hooks are isolated and bypassed for standard users."
    exit 0
fi

log_info "Development Mode Active. Proceeding with telemetry aggregation."

# 2. Check for telemetry source JSON report
TELEMETRY_FILE="/tmp/jules_telemetry.json"
if [ ! -f "${TELEMETRY_FILE}" ]; then
    log_error "Telemetry source file '${TELEMETRY_FILE}' not found! Run the playbook first."
    exit 1
fi

log_info "Parsing telemetry reports from ${TELEMETRY_FILE}..."

# Ensure jq is installed
if ! command -v jq &>/dev/null; then
    log_error "Missing dependency 'jq'. Please install jq to parse telemetry data."
    exit 1
fi

# Extract and sanitize report metrics
TIMESTAMP=$(jq -r '.timestamp // "unknown"' "${TELEMETRY_FILE}")
KERNEL_INFO=$(jq -r '.host_info.kernel // "unknown"' "${TELEMETRY_FILE}")

# Initialize Markdown content block
REPORT_MD=""
REPORT_MD+="### 🧪 WSL 2 Ubuntu 26.04 Multi-OS Matrix Test Report\n"
REPORT_MD+="**Execution Timestamp:** \`${TIMESTAMP}\`\n"
REPORT_MD+="**Host Kernel:** \`${KERNEL_INFO}\`\n\n"
REPORT_MD+="| Distro | Image | Status | Exit Code | Logs / Details |\n"
REPORT_MD+="|---|---|---|---|---|\n"

# Loop over the distro results using jq
while IFS= read -r row; do
    DISTRO_NAME=$(echo "${row}" | jq -r '.name // "unknown"')
    DISTRO_IMAGE=$(echo "${row}" | jq -r '.image // "unknown"')
    DISTRO_STATUS=$(echo "${row}" | jq -r '.status // "unknown"')
    DISTRO_EXIT=$(echo "${row}" | jq -r '.exit_code // "0"')
    DISTRO_LOGS=$(echo "${row}" | jq -r '.logs // ""' | tr -d '\n' | tr -d '"')

    # Status icon coloring representation
    if [ "${DISTRO_STATUS}" = "SUCCESS" ]; then
        STATUS_ICON="🟢 SUCCESS"
    else
        STATUS_ICON="🔴 FAILED"
    fi

    REPORT_MD+="| ${DISTRO_NAME} | \`${DISTRO_IMAGE}\` | ${STATUS_ICON} | \`${DISTRO_EXIT}\` | ${DISTRO_LOGS} |\n"
done < <(jq -c '.results[]' "${TELEMETRY_FILE}")

# Add differential diagnostics footer
REPORT_MD+="\n\n**Differential Diagnostics:**\n"
REPORT_MD+="\`\`\`\n"
REPORT_MD+="$(jq -r '.results[] | "Distro: " + .name + "\nDiff: " + .diff' "${TELEMETRY_FILE}")\n"
REPORT_MD+="\`\`\`\n"

# 3. Stream Structured Feedback into Google Jules CLI Session / API
log_info "Dispatching diagnostic feedback to Google Jules CLI/API..."
JULES_TASK_ID="${JULES_TASK_ID:-}"
JULES_API_URL="${JULES_API_URL:-}"
JULES_API_TOKEN="${JULES_API_TOKEN:-}"

if command -v jules &>/dev/null; then
    log_info "Active jules CLI binary detected. Posting chat message..."
    # Format and pass the telemetry report text straight into jules chat
    printf "%b" "${REPORT_MD}" | jules chat --message-stdin || log_warn "Jules CLI direct call failed."
elif [ -n "${JULES_API_URL}" ] && [ -n "${JULES_API_TOKEN}" ] && [ -n "${JULES_TASK_ID}" ]; then
    log_info "No local jules CLI, dispatching feedback using REST endpoint: ${JULES_API_URL}"
    JSON_BODY=$(jq -n \
        --arg body "$(printf "%b" "${REPORT_MD}")" \
        --arg task_id "${JULES_TASK_ID}" \
        '{task_id: $task_id, message: $body}')
    curl -s -X POST \
        -H "Authorization: Bearer ${JULES_API_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "${JSON_BODY}" \
        "${JULES_API_URL}/tasks/${JULES_TASK_ID}/feedback" || log_warn "Jules API endpoint call failed."
else
    log_warn "Jules CLI and API token configurations are unavailable. Skipping Jules CLI dispatch."
fi

# 4. Stream feedback comments directly to active GitHub Pull Request
log_info "Dispatching diagnostic report to active GitHub PR..."
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
GITHUB_PR_NUMBER="${GITHUB_PR_NUMBER:-}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-}"

if command -v gh &>/dev/null && [ -n "${GITHUB_TOKEN}" ] && [ -n "${GITHUB_PR_NUMBER}" ]; then
    log_info "GitHub CLI found. Submitting comment to Pull Request #${GITHUB_PR_NUMBER}..."
    printf "%b" "${REPORT_MD}" | gh pr comment "${GITHUB_PR_NUMBER}" --body-file - || log_warn "gh CLI failed to submit comment."
elif [ -n "${GITHUB_TOKEN}" ] && [ -n "${GITHUB_PR_NUMBER}" ] && [ -n "${GITHUB_REPOSITORY}" ]; then
    log_info "gh CLI missing, falling back to direct GitHub REST API endpoint..."
    JSON_BODY=$(jq -n \
        --arg body "$(printf "%b" "${REPORT_MD}")" \
        '{body: $body}')

    curl -s -X POST \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Content-Type: application/json" \
        -d "${JSON_BODY}" \
        "https://api.github.com/repos/${GITHUB_REPOSITORY}/issues/${GITHUB_PR_NUMBER}/comments" > /dev/null || log_warn "GitHub REST API call failed."
else
    log_warn "GitHub credentials (GITHUB_TOKEN, GITHUB_PR_NUMBER, GITHUB_REPOSITORY) are unavailable. Skipping PR update."
fi

log_info "Telemetry and Feedback Bridge executed successfully."

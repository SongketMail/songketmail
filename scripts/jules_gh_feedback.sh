#!/usr/bin/env bash
# ==============================================================================
# Bidirectional Jules CLI & GitHub Pull Request Diagnostic Bridge Script
# Idempotent, robust, POSIX-compliant, and secure.
# ==============================================================================

set -euo pipefail

# Set strict umask to restrict telemetry artifacts to the owner
umask 077

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
    log_info "Cleaning up session..."
    if [[ -n "${PAYLOAD_FILE:-}" && -f "${PAYLOAD_FILE}" ]]; then
        rm -f "${PAYLOAD_FILE}"
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Helper function to invoke GitHub API with deduplicated parameters
github_api_request() {
    local method="$1"
    local path_or_url="$2"
    local data_payload="${3:-}"

    # Determine absolute URL
    local url="${path_or_url}"
    if [[ ! "${url}" =~ ^https?:// ]]; then
        url="https://api.github.com/${url}"
    fi

    local -a curl_opts=(
        "-s"
        "-X" "${method}"
        "-H" "Authorization: token ${GITHUB_TOKEN}"
        "-H" "Accept: application/vnd.github.v3+json"
        "--connect-timeout" "10"
        "--max-time" "30"
    )

    if [[ -n "${data_payload}" ]]; then
        curl_opts+=(
            "-H" "Content-Type: application/json"
            "-d" "${data_payload}"
        )
    fi

    curl "${curl_opts[@]}" "${url}"
}

log_info "Starting Jules CLI & GitHub PR Feedback Dispatcher"

# 1. Strict Mode Separation Gate
EXECUTION_MODE="${EXECUTION_MODE:-user}"
if [[ "${EXECUTION_MODE}" != "dev" ]]; then
    log_warn "EXECUTION_MODE is not set to 'dev' (Current: ${EXECUTION_MODE})."
    log_warn "Diagnostic hooks are isolated and bypassed for standard users."
    exit 0
fi

log_info "Development Mode Active. Proceeding with telemetry aggregation."

# 2. Check for telemetry source JSON report
TELEMETRY_FILE="${TELEMETRY_FILE_PATH:-/tmp/jules_telemetry.json}"
if [[ ! -f "${TELEMETRY_FILE}" ]]; then
    log_error "Telemetry source file '${TELEMETRY_FILE}' not found!"
    exit 1
fi

log_info "Parsing telemetry reports from ${TELEMETRY_FILE}..."

# Ensure jq is installed
if ! command -v jq &>/dev/null; then
    log_error "Missing dependency 'jq'. Please install jq to parse telemetry data."
    exit 1
fi

# Validate telemetry file content before parsing
if ! jq empty "${TELEMETRY_FILE}" 2>/dev/null; then
    log_error "Telemetry file contains invalid JSON or is empty."
    exit 1
fi

# Extract and sanitize report metrics
TIMESTAMP=$(jq -r '.timestamp // "unknown"' "${TELEMETRY_FILE}")
KERNEL_INFO=$(jq -r '.host_info.kernel // "unknown"' "${TELEMETRY_FILE}")

# Initialize Markdown content block with stable tracking marker
REPORT_MD=""
REPORT_MD+="<!-- songketmail-telemetry-marker -->\n"
REPORT_MD+="### 🧪 WSL 2 Ubuntu 26.04 Multi-OS Matrix Test Report\n"
REPORT_MD+="**Execution Timestamp:** \`${TIMESTAMP}\`\n"
REPORT_MD+="**Host Kernel:** \`${KERNEL_INFO}\`\n\n"
REPORT_MD+="| Distro | Image | Status | Exit Code | Logs / Details |\n"
REPORT_MD+="|---|---|---|---|---|\n"

# Verify that results exist to prevent synthetic passed results on empty logs
RESULTS_COUNT=$(jq '.results | length' "${TELEMETRY_FILE}")
if [[ -z "${RESULTS_COUNT}" ]] || (( RESULTS_COUNT == 0 )); then
    log_error "Parsed 0 test results. Propagation failure state."
    exit 1
fi

# Loop over the distro results using jq
while IFS= read -r row; do
    DISTRO_NAME=$(echo "${row}" | jq -r '.name // "unknown"')
    DISTRO_IMAGE=$(echo "${row}" | jq -r '.image // "unknown"')
    DISTRO_STATUS=$(echo "${row}" | jq -r '.status // "unknown"')
    DISTRO_EXIT=$(echo "${row}" | jq -r '.exit_code // "0"')
    DISTRO_LOGS=$(echo "${row}" | jq -r '.logs // ""' | tr -d '\n' | tr -d '"')

    # Status icon coloring representation
    if [[ "${DISTRO_STATUS}" == "SUCCESS" ]]; then
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

# Write the report to a secure temp payload file
PAYLOAD_FILE=$(mktemp -t jules_payload.XXXXXX)
chmod 0600 "${PAYLOAD_FILE}"
printf "%b" "${REPORT_MD}" > "${PAYLOAD_FILE}"

# 3. Stream Structured Feedback into Google Jules CLI Session / API
log_info "Dispatching diagnostic feedback to Google Jules CLI/API..."
JULES_TASK_ID="${JULES_TASK_ID:-}"
JULES_API_URL="${JULES_API_URL:-}"
JULES_API_TOKEN="${JULES_API_TOKEN:-}"

if command -v jules &>/dev/null; then
    log_info "Active jules CLI binary detected. Posting chat message using jules remote new flow..."
    # Format and pass the telemetry report file straight into jules remote new flow
    jules remote new --task-id "${JULES_TASK_ID}" --report-file "${PAYLOAD_FILE}" || log_warn "Jules remote new call failed."
elif [[ -n "${JULES_API_URL}" ]] && [[ -n "${JULES_API_TOKEN}" ]] && [[ -n "${JULES_TASK_ID}" ]]; then
    log_info "No local jules CLI, dispatching feedback using REST endpoint: ${JULES_API_URL}"
    JSON_BODY=$(jq -n \
        --arg body "$(cat "${PAYLOAD_FILE}")" \
        --arg task_id "${JULES_TASK_ID}" \
        '{task_id: $task_id, message: $body}')
    curl -s -X POST \
        -H "Authorization: Bearer ${JULES_API_TOKEN}" \
        -H "Content-Type: application/json" \
        --connect-timeout 10 --max-time 30 \
        -d "${JSON_BODY}" \
        "${JULES_API_URL}/tasks/${JULES_TASK_ID}/feedback" || log_warn "Jules API endpoint call failed."
else
    log_warn "Jules CLI and API token configurations are unavailable. Skipping Jules CLI dispatch."
fi

# 4. Stream feedback comments directly to active GitHub Pull Request (Idempotently)
log_info "Dispatching diagnostic report to active GitHub PR..."
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
GITHUB_PR_NUMBER="${GITHUB_PR_NUMBER:-}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-}"

if command -v gh &>/dev/null && [[ -n "${GITHUB_TOKEN}" ]] && [[ -n "${GITHUB_PR_NUMBER}" ]]; then
    log_info "GitHub CLI found. Finding any existing automated comment to update..."
    EXISTING_COMMENT_ID=$(gh api "repos/${GITHUB_REPOSITORY}/issues/${GITHUB_PR_NUMBER}/comments" --jq ".[] | select(.body | contains(\"<!-- songketmail-telemetry-marker -->\")) | .id" | head -n 1)

    if [[ -n "${EXISTING_COMMENT_ID}" ]]; then
        log_info "Updating existing comment ID ${EXISTING_COMMENT_ID}..."
        gh api -X PATCH "repos/${GITHUB_REPOSITORY}/issues/comments/${EXISTING_COMMENT_ID}" -F body=@"${PAYLOAD_FILE}" > /dev/null || log_warn "Failed to update comment via gh api."
    else
        log_info "Creating new Pull Request comment..."
        gh pr comment "${GITHUB_PR_NUMBER}" --body-file "${PAYLOAD_FILE}" || log_warn "gh CLI failed to submit comment."
    fi
elif [[ -n "${GITHUB_TOKEN}" ]] && [[ -n "${GITHUB_PR_NUMBER}" ]] && [[ -n "${GITHUB_REPOSITORY}" ]]; then
    log_info "gh CLI missing, falling back to direct GitHub REST API endpoint..."

    # Query existing comments using helper function
    EXISTING_COMMENT_ID=$(github_api_request "GET" "repos/${GITHUB_REPOSITORY}/issues/${GITHUB_PR_NUMBER}/comments" \
        | jq -r ".[] | select(.body | contains(\"<!-- songketmail-telemetry-marker -->\")) | .id" | head -n 1)

    if [[ -n "${EXISTING_COMMENT_ID}" && "${EXISTING_COMMENT_ID}" != "null" ]]; then
        log_info "Updating existing comment ID ${EXISTING_COMMENT_ID} via REST..."
        JSON_BODY=$(jq -n --arg body "$(cat "${PAYLOAD_FILE}")" '{body: $body}')
        github_api_request "PATCH" "repos/${GITHUB_REPOSITORY}/issues/comments/${EXISTING_COMMENT_ID}" "${JSON_BODY}" > /dev/null || log_warn "GitHub REST API patch failed."
    else
        log_info "Creating new comment via REST..."
        JSON_BODY=$(jq -n --arg body "$(cat "${PAYLOAD_FILE}")" '{body: $body}')
        github_api_request "POST" "repos/${GITHUB_REPOSITORY}/issues/${GITHUB_PR_NUMBER}/comments" "${JSON_BODY}" > /dev/null || log_warn "GitHub REST API post failed."
    fi
else
    log_warn "GitHub credentials (GITHUB_TOKEN, GITHUB_PR_NUMBER, GITHUB_REPOSITORY) are unavailable. Skipping PR update."
fi

log_info "Telemetry and Feedback Bridge executed successfully."

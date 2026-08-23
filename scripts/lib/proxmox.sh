#!/bin/bash
# Shared Proxmox API helpers.
#
# Source from a script in scripts/:
#     source "$(dirname "${BASH_SOURCE[0]}")/lib/proxmox.sh"
#
# Required environment:
#     PROXMOX_HOST               Proxmox host or IP (no default — must be set explicitly)
#     PROXMOX_API_TOKEN_ID       e.g. terraform@pam!terraform
#     PROXMOX_API_TOKEN_SECRET   token secret
#
# Optional environment:
#     PROXMOX_API_URL            overrides the derived https://$PROXMOX_HOST:8006/api2/json
#     PROXMOX_NODE               node name (default: pve)
#     PROXMOX_CA_BUNDLE          CA bundle for the Proxmox certificate
#     PROXMOX_TLS_INSECURE=1     skip certificate verification (opt-in, not the default)

set -euo pipefail

: "${PROXMOX_HOST:?must be set, e.g. export PROXMOX_HOST=proxmox.example.com}"

PROXMOX_API_URL="${PROXMOX_API_URL:-https://${PROXMOX_HOST}:8006/api2/json}"
PROXMOX_NODE="${PROXMOX_NODE:-pve}"

# Fall back to the TF_VAR_* names so the same shell that runs Terraform works here.
PROXMOX_API_TOKEN_ID="${PROXMOX_API_TOKEN_ID:-${TF_VAR_proxmox_api_token_id:-}}"
PROXMOX_API_TOKEN_SECRET="${PROXMOX_API_TOKEN_SECRET:-${TF_VAR_proxmox_api_token_secret:-}}"

if [ -z "$PROXMOX_API_TOKEN_ID" ] || [ -z "$PROXMOX_API_TOKEN_SECRET" ]; then
    echo "Error: PROXMOX_API_TOKEN_ID and PROXMOX_API_TOKEN_SECRET must be set" >&2
    echo "       (or TF_VAR_proxmox_api_token_id / TF_VAR_proxmox_api_token_secret)" >&2
    echo "Example:" >&2
    echo "  export PROXMOX_API_TOKEN_ID='terraform@pam!terraform'" >&2
    echo "  read -rs PROXMOX_API_TOKEN_SECRET && export PROXMOX_API_TOKEN_SECRET" >&2
    exit 1
fi

# Build the TLS half of the curl argument list once.
_proxmox_curl_tls_opts() {
    if [ -n "${PROXMOX_CA_BUNDLE:-}" ]; then
        printf '%s\n' --cacert "$PROXMOX_CA_BUNDLE"
    fi
    if [ "${PROXMOX_TLS_INSECURE:-0}" = "1" ]; then
        printf '%s\n' --insecure
    fi
}

# Warn once if certificate verification has been turned off.
if [ "${PROXMOX_TLS_INSECURE:-0}" = "1" ]; then
    echo "Warning: PROXMOX_TLS_INSECURE=1 — TLS certificate verification is disabled." >&2
fi

# proxmox_api METHOD ENDPOINT [extra curl args...]
#
# The token is passed through a curl config file on stdin rather than argv, so it
# does not show up in `ps` output. Non-2xx responses fail the script (--fail-with-body)
# instead of being silently treated as success.
proxmox_api() {
    local method=$1
    local endpoint=$2
    shift 2

    local -a opts=(--silent --show-error --fail-with-body --request "$method")
    local tls_opt
    while IFS= read -r tls_opt; do
        [ -n "$tls_opt" ] && opts+=("$tls_opt")
    done < <(_proxmox_curl_tls_opts)

    printf 'header = "Authorization: PVEAPIToken=%s=%s"\n' \
        "$PROXMOX_API_TOKEN_ID" "$PROXMOX_API_TOKEN_SECRET" \
        | curl "${opts[@]}" --config - "$@" "${PROXMOX_API_URL}${endpoint}"
}

# proxmox_api_status METHOD ENDPOINT [extra curl args...]
#
# Prints the HTTP status code and discards the body. Use this for existence checks
# instead of grepping the response text for "404" or "does not exist" — Proxmox
# error wording is not a stable API.
proxmox_api_status() {
    local method=$1
    local endpoint=$2
    shift 2

    local -a opts=(--silent --show-error --request "$method"
                   --output /dev/null --write-out '%{http_code}')
    local tls_opt
    while IFS= read -r tls_opt; do
        [ -n "$tls_opt" ] && opts+=("$tls_opt")
    done < <(_proxmox_curl_tls_opts)

    printf 'header = "Authorization: PVEAPIToken=%s=%s"\n' \
        "$PROXMOX_API_TOKEN_ID" "$PROXMOX_API_TOKEN_SECRET" \
        | curl "${opts[@]}" --config - "$@" "${PROXMOX_API_URL}${endpoint}"
}

# proxmox_confirm PROMPT
#
# Returns 0 only on an explicit "yes". Non-interactive callers must set
# PROXMOX_ASSUME_YES=1 deliberately; an absent stdin is treated as "no".
proxmox_confirm() {
    local prompt=$1
    if [ "${PROXMOX_ASSUME_YES:-0}" = "1" ]; then
        echo "$prompt -> assuming yes (PROXMOX_ASSUME_YES=1)"
        return 0
    fi
    if [ ! -t 0 ]; then
        echo "Error: $prompt" >&2
        echo "       stdin is not a terminal; set PROXMOX_ASSUME_YES=1 to proceed." >&2
        return 1
    fi
    local reply
    read -r -p "$prompt [type 'yes' to confirm] " reply
    [ "$reply" = "yes" ]
}

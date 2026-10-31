#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
# Re-read Rocky evidence at its recorded /work paths without executing models.
set -euo pipefail

if [[ $# != 1 || ( $1 != regressions && $1 != producer ) ]]; then
    echo 'Usage: rocky_audit.bash regressions|producer' >&2
    exit 2
fi
portable_audit_mode=$1
portable_audit_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
portable_audit_options=(
    --rm -i -v "$portable_audit_root:/work" -w /work
    -e "ARTIFACT_UID=$(id -u)" -e "ARTIFACT_GID=$(id -g)"
)
if [[ $portable_audit_mode == producer ]]; then
    if [[ ${GITHUB_OUTPUT:-} != /* || ! -f ${GITHUB_OUTPUT:-} || -L ${GITHUB_OUTPUT:-}
        || ! ${GITHUB_RUN_ID:-} =~ ^[1-9][0-9]*$
        || ! ${GITHUB_RUN_ATTEMPT:-} =~ ^[1-9][0-9]*$
        || ( ${PRODUCER_PRIOR_RESULT:-} != success && ${PRODUCER_PRIOR_RESULT:-} != failure ) ]]; then
        echo 'Producer audit requires the current output file and run context' >&2
        exit 2
    fi
    portable_audit_options+=(
        -v "$GITHUB_OUTPUT:/tmp/github-output" -e GITHUB_OUTPUT=/tmp/github-output
        -e "GITHUB_RUN_ID=$GITHUB_RUN_ID" -e "GITHUB_RUN_ATTEMPT=$GITHUB_RUN_ATTEMPT"
        -e "PRODUCER_PRIOR_RESULT=$PRODUCER_PRIOR_RESULT"
    )
fi
exec docker run "${portable_audit_options[@]}" \
    rockylinux/rockylinux:8.10@sha256:f5529992e67440c1a4ae7788244d4381c6909159a88eacd95b7523ae47ced82e \
    bash -s -- "$portable_audit_mode" <<'ROCKY_AUDIT'
set -euo pipefail
dnf -y install python3.11 git util-linux
exec setpriv --reuid "$ARTIFACT_UID" --regid "$ARTIFACT_GID" --clear-groups \
    bash -c '
        set -euo pipefail
        portable_owner_home=$(mktemp -d /tmp/verilator-owner-home.XXXXXX)
        export HOME="$portable_owner_home"
        if [[ $1 == regressions ]]; then
            exec python3.11 ci/portable/check_results.py
        fi
        exec python3.11 ci/portable/review_artifacts.py producer \
            --expected-head "$(git rev-parse HEAD)" --run-id "$GITHUB_RUN_ID" \
            --platform rocky8-x86_64 --producer-root /work \
            --prior-result "$PRODUCER_PRIOR_RESULT" --output out/producer-core-review.json
    ' portable-rocky-audit "$1"
ROCKY_AUDIT

#!/usr/bin/env bash
# Runs the abuse binary with Ngó Sen's release profile, then again with overflow checks, and checks
# that a panic aborts: the control case must die of SIGABRT (exit 134), not unwind (exit 101).
set -euo pipefail
cd "$(dirname "$0")/.."

# The binary's personal files live here; removed on exit, even when the binary aborts.
TIMSEN_ABUSE_DIR="$(mktemp -d)"
export TIMSEN_ABUSE_DIR
trap 'rm -rf "$TIMSEN_ABUSE_DIR"' EXIT

profile=(--config 'profile.release.panic="abort"' --config 'profile.release.lto=true'
  --config 'profile.release.codegen-units=1')
run() { cargo run -q --locked --release -p timsen --example abuse "${profile[@]}" "$@"; }

run
run --config 'profile.release.overflow-checks=true'

status=0
run -- --control 2>/dev/null || status=$?
if [ "$status" -ne 134 ]; then
  echo "control case exited $status, not 134: a panic would not abort" >&2
  exit 1
fi
echo "control case aborted as it should"

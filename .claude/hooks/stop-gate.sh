#!/bin/sh
# Stop hook: blocks the stop when lint, the type check or tests/arch fail.
input=$(cat)
# Do not block again while already continuing because of this hook.
case "$input" in *'"stop_hook_active": true'*|*'"stop_hook_active":true'*) exit 0 ;; esac
command -v uv >/dev/null 2>&1 || { echo "stop-gate: uv not found, skipping" >&2; exit 0; }
cd "$CLAUDE_PROJECT_DIR" || exit 0
out=$(make gate 2>&1); status=$?
if [ "$status" -ne 0 ]; then
  printf '%s\n' "$out" | tail -n 60 >&2
  echo "Stop blocked: 'make gate' (lint, types, tests/arch) failed. Fix it before stopping." >&2
  exit 2
fi
exit 0

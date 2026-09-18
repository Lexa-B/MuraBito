#!/usr/bin/env bash
# Build, then run automation tests headless. Usage: test.sh [TestPathPrefix]
# Exits 0 only if at least one test ran and none failed.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
FILTER="${1:-MuraBito}"

"$(dirname "${BASH_SOURCE[0]}")/build.sh"

LOG_DIR="$EXP_DIR/Saved/TestLogs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/test-$(date +%Y%m%d-%H%M%S).log"

set +e
"$EDITOR_CMD" "$PROJECT" \
  -ExecCmds="Automation RunTests $FILTER" \
  -TestExit="Automation Test Queue Empty" \
  -unattended -nullrhi -nosplash -nosound -stdout -FullStdOutLogOutput \
  > "$LOG" 2>&1
CODE=$?
set -e

rg --no-line-number "Test Completed\. Result=" "$LOG" || true
PASSED=$(rg -c "Test Completed\. Result=\{Success\}" "$LOG" || true)
FAILED=$(rg -c "Test Completed\. Result=\{Fail" "$LOG" || true)
PASSED=${PASSED:-0}
FAILED=${FAILED:-0}

echo "passed: $PASSED  failed: $FAILED  editor exit code: $CODE"
echo "log: $LOG"
# Note: the editor's own exit code is not a pass/fail signal here. -TestExit force-exits via
# FUnixPlatformMisc::RequestExit(true, ...), which always _exit(1)s on that path regardless of
# test outcome (see Engine/Source/Runtime/Core/Private/Unix/UnixPlatformMisc.cpp). Pass/fail is
# decided from the automation log instead.
if [[ "$FAILED" -ne 0 || "$PASSED" -eq 0 ]]; then
  rg --no-line-number "Error: |Expected " "$LOG" | head -40 || true
  echo "TESTS FAILED"
  exit 1
fi
echo "TESTS PASSED"

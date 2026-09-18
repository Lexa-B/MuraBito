#!/usr/bin/env bash
# Shared settings, sourced by the other scripts.
# Set UE_ROOT to use a different Unreal Engine 5.8 install.
set -euo pipefail

UE_ROOT="${UE_ROOT:-/home/lexa/DevProjects/_GameDev/_GameEngines/UnrealEngine/5.8.2}"
EXP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$EXP_DIR/MuraBito.uproject"
# Named UE_EDITOR, not EDITOR: EDITOR is a common shell env var (default text editor), and
# assigning it here would clobber the user's own exported $EDITOR for any child process.
UE_EDITOR="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
UE_EDITOR_CMD="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"
BUILD_SH="$UE_ROOT/Engine/Build/BatchFiles/Linux/Build.sh"

for f in "$UE_EDITOR" "$UE_EDITOR_CMD" "$BUILD_SH"; do
  if [[ ! -x "$f" ]]; then
    echo "error: no Unreal Engine install at UE_ROOT=$UE_ROOT (missing $f)" >&2
    exit 1
  fi
done

# Refuse to build while any Unreal Editor is running. A running editor makes rebuilt modules
# load under a new hot-reload name, so tests would silently run stale code. Close the editor
# yourself; these scripts never stop it for you.
require_no_running_editor() {
  local running
  running=$(pgrep -a -f '/UnrealEditor(-Cmd)?( |$)' || true)
  if [[ -n "$running" ]]; then
    echo "error: an Unreal Editor is running. Close it, then retry:" >&2
    echo "$running" >&2
    exit 1
  fi
}

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

# Any running Unreal Editor from this engine install, whatever project it has open, makes
# UnrealBuildTool build editor targets in hot-reload mode (see HotReload.cs, ShouldDoHotReloadFromIDE):
# modules get a numbered suffix for the open editor to load, and UnrealEditor.modules is left alone.
# That is what we want when the editor has this project open. These scripts never stop an editor.
note_running_editor() {
  local running
  running=$(pgrep -a -f '/UnrealEditor(-Cmd)?( |$)' || true)
  if [[ -n "$running" ]]; then
    echo "note: an Unreal Editor is running, so this is a hot-reload build for it to pick up:" >&2
    echo "$running" >&2
  fi
}

# Headless tests run on a private copy of the project, built without hot reload. A hot-reload
# build leaves UnrealEditor.modules pointing at the previous modules, so a fresh engine process
# started on this checkout while an editor is open would run stale code.
TEST_MIRROR="${MURABITO_TEST_MIRROR:-${XDG_CACHE_HOME:-$HOME/.cache}/murabito/exp-04-test-mirror}"

# Windowed runs need the desktop session's display. A shell whose parent process lives outside
# the graphical session (for example a terminal multiplexer server started as a systemd user
# service) has no DISPLAY or WAYLAND_DISPLAY, and the engine then crashes during RHI init. Fill
# them in from the systemd user environment, which the desktop session exports.
require_display() {
  if [[ -n "${DISPLAY-}" || -n "${WAYLAND_DISPLAY-}" ]]; then
    return
  fi
  local line
  while IFS= read -r line; do
    case "$line" in
      DISPLAY=*|WAYLAND_DISPLAY=*|XAUTHORITY=*) export "$line" ;;
    esac
  done < <(systemctl --user show-environment 2>/dev/null || true)
  if [[ -z "${DISPLAY-}" && -z "${WAYLAND_DISPLAY-}" ]]; then
    echo "error: no DISPLAY or WAYLAND_DISPLAY here or in the systemd user session; run from a desktop terminal" >&2
    exit 1
  fi
  echo "note: using the desktop session's display (DISPLAY=${DISPLAY-} WAYLAND_DISPLAY=${WAYLAND_DISPLAY-})" >&2
}

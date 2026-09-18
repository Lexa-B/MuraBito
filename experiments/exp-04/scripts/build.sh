#!/usr/bin/env bash
# Build the editor target (Development, Linux). Extra args go to UnrealBuildTool.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
require_no_running_editor
"$BUILD_SH" MuraBitoEditor Linux Development -Project="$PROJECT" -WaitMutex "$@"

#!/usr/bin/env bash
# Run standalone in a window. Pass -Seed=N for a different terrain.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
exec "$UE_EDITOR" "$PROJECT" -game -windowed -ResX=1600 -ResY=900 -log "$@"

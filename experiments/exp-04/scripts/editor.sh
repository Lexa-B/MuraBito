#!/usr/bin/env bash
# Open the project in the editor. Press Play to run the world.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
exec "$UE_EDITOR" "$PROJECT" "$@"

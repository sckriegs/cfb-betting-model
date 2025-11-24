#!/bin/bash
# Helper script to run commands without Poetry permission issues

cd "$(dirname "$0")"
export DYLD_LIBRARY_PATH="/usr/local/opt/libomp/lib:$DYLD_LIBRARY_PATH"
source $(poetry env info --path)/bin/activate
python -m src.cli.main "$@"

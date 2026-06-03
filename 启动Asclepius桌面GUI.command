#!/bin/zsh
set -e

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$SCRIPT_DIR/src"

python3 -m gerodrug_sim.desktop

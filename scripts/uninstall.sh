#!/usr/bin/env sh
set -eu

INSTALL_DIR=${MEMINGO_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/memingo}
BIN_DIR=${MEMINGO_BIN_DIR:-$HOME/.local/bin}

rm -rf "$INSTALL_DIR"
rm -f "$BIN_DIR/memingo"
printf 'Memingo removed from %s\n' "$INSTALL_DIR"

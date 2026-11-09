#!/usr/bin/env sh
set -eu

INSTALL_DIR=${MEMINGO_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/memingo}
if [ -n "${MEMINGO_BIN_DIR:-}" ]; then
  BIN_DIR=$MEMINGO_BIN_DIR
elif { [ -n "${TERMUX_VERSION:-}" ] || { [ -n "${PREFIX:-}" ] && [ -d "$PREFIX/etc/termux" ]; }; } && [ -n "${PREFIX:-}" ]; then
  BIN_DIR=$PREFIX/bin
else
  BIN_DIR=$HOME/.local/bin
fi

rm -rf "$INSTALL_DIR"
rm -f "$BIN_DIR/memingo" "$BIN_DIR/mgoa" "$BIN_DIR/memingo.cmd" "$BIN_DIR/mgoa.cmd"
printf 'Memingo and mgoa removed from %s\n' "$INSTALL_DIR"

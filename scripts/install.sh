#!/usr/bin/env sh
set -eu

SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
INSTALL_DIR=${MEMINGO_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/memingo}
IS_TERMUX=0
if [ -n "${TERMUX_VERSION:-}" ] || { [ -n "${PREFIX:-}" ] && [ -d "$PREFIX/etc/termux" ]; }; then
  IS_TERMUX=1
fi
if [ -n "${MEMINGO_BIN_DIR:-}" ]; then
  BIN_DIR=$MEMINGO_BIN_DIR
elif [ "$IS_TERMUX" -eq 1 ] && [ -n "${PREFIX:-}" ]; then
  BIN_DIR=$PREFIX/bin
else
  BIN_DIR=$HOME/.local/bin
fi
PYTHON=${MEMINGO_PYTHON:-}

if [ -z "$PYTHON" ]; then
  PYTHON=$(command -v python3 || command -v python || true)
fi

if [ -z "$PYTHON" ]; then
  echo "Memingo necesita Python 3.10 o superior." >&2
  echo "Instala Python desde tu gestor del sistema y vuelve a ejecutar el instalador." >&2
  exit 1
fi

if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  echo "Memingo necesita Python 3.10 o superior." >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
rm -rf "$INSTALL_DIR/memingo" "$INSTALL_DIR/launcher.py" "$INSTALL_DIR/mgoa.py"
cp -R "$SOURCE_DIR/memingo" "$INSTALL_DIR/memingo"
cp "$SOURCE_DIR/scripts/launcher.py" "$INSTALL_DIR/launcher.py"
cp "$SOURCE_DIR/scripts/mgoa.py" "$INSTALL_DIR/mgoa.py"
find "$INSTALL_DIR/memingo" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$INSTALL_DIR/memingo" -type f -name '*.py[co]' -delete 2>/dev/null || true

cat > "$BIN_DIR/memingo" <<EOF
#!/usr/bin/env sh
exec "$PYTHON" -I "$INSTALL_DIR/launcher.py" "\$@"
EOF
chmod +x "$BIN_DIR/memingo"

cat > "$BIN_DIR/mgoa" <<EOF
#!/usr/bin/env sh
exec "$PYTHON" -I "$INSTALL_DIR/mgoa.py" "\$@"
EOF
chmod +x "$BIN_DIR/mgoa"

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
if [ "$IS_TERMUX" -eq 1 ]; then
  PATH_LINE=""
elif [ "$BIN_DIR" != "$HOME/.local/bin" ]; then
  PATH_LINE="export PATH=\"$BIN_DIR:\$PATH\""
fi

add_path_line() {
  profile=$1
  [ -n "$profile" ] || return 0
  touch "$profile"
  if ! grep -Fq "$BIN_DIR" "$profile" 2>/dev/null; then
    printf '\n# Memingo\n%s\n' "$PATH_LINE" >> "$profile"
  fi
}

if [ -n "$PATH_LINE" ]; then
  add_path_line "$HOME/.profile"
  add_path_line "$HOME/.bashrc"
fi
case "${SHELL:-}" in
  */zsh) [ -z "$PATH_LINE" ] || add_path_line "$HOME/.zprofile" ;;
  */fish)
    if [ -n "$PATH_LINE" ]; then
      mkdir -p "$HOME/.config/fish"
      if ! grep -Fq "$BIN_DIR" "$HOME/.config/fish/config.fish" 2>/dev/null; then
        printf '\n# Memingo\nfish_add_path %s\n' "$BIN_DIR" >> "$HOME/.config/fish/config.fish"
      fi
    fi
    ;;
esac

if [ "$IS_TERMUX" -eq 1 ]; then
  printf 'Memingo installed for Termux.\n'
else
  printf 'Memingo installed successfully.\n'
fi
printf 'Runtime: %s\n' "$INSTALL_DIR"
printf 'Commands: %s/memingo, %s/mgoa\n' "$BIN_DIR" "$BIN_DIR"
if [ "$IS_TERMUX" -eq 1 ]; then
  printf 'Run: hash -r && memingo --version && mgoa --version\n'
else
  printf 'Run this now if memingo or mgoa is not found:\n  export PATH="%s:$PATH"\n  hash -r\n  memingo --version\n  mgoa --version\n' "$BIN_DIR"
fi

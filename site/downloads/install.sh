#!/usr/bin/env sh
set -eu

REPO_URL=${MEMINGO_REPO_URL:-https://github.com/Reaccionador2Jeje/Memingo/archive/refs/heads/main.zip}
INSTALL_DIR=${MEMINGO_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/memingo}
BIN_DIR=${MEMINGO_BIN_DIR:-$HOME/.local/bin}
PYTHON=${MEMINGO_PYTHON:-$(command -v python3 || true)}
TMP_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t memingo)
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

if [ -z "$PYTHON" ]; then
  echo "Memingo necesita Python 3.10 o superior." >&2
  exit 1
fi

if ! "$PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
  echo "Memingo necesita Python 3.10 o superior." >&2
  exit 1
fi

mkdir -p "$TMP_DIR/download" "$INSTALL_DIR" "$BIN_DIR"
if command -v curl >/dev/null 2>&1; then
  curl -L --fail "$REPO_URL" -o "$TMP_DIR/memingo.zip"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$TMP_DIR/memingo.zip" "$REPO_URL"
else
  echo "Memingo necesita curl o wget para descargar el runtime." >&2
  exit 1
fi

unzip -q "$TMP_DIR/memingo.zip" -d "$TMP_DIR/download"
SOURCE_DIR=$(find "$TMP_DIR/download" -mindepth 1 -maxdepth 1 -type d | head -n 1)
if [ ! -d "$SOURCE_DIR/memingo" ]; then
  echo "No se pudo encontrar el runtime de Memingo." >&2
  exit 1
fi

rm -rf "$INSTALL_DIR/memingo"
cp -R "$SOURCE_DIR/memingo" "$INSTALL_DIR/memingo"
cp "$SOURCE_DIR/scripts/launcher.py" "$INSTALL_DIR/launcher.py"

cat > "$BIN_DIR/memingo" <<EOF
#!/usr/bin/env sh
exec "$PYTHON" -I "$INSTALL_DIR/launcher.py" "\$@"
EOF
chmod +x "$BIN_DIR/memingo"

printf 'Memingo installed at %s\n' "$INSTALL_DIR"
printf 'Command installed at %s\n' "$BIN_DIR/memingo"

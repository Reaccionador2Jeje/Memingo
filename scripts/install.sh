#!/usr/bin/env sh
set -eu

SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
INSTALL_DIR=${MEMINGO_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/memingo}
BIN_DIR=${MEMINGO_BIN_DIR:-$HOME/.local/bin}
PYTHON=${MEMINGO_PYTHON:-$(command -v python3 || true)}

if [ -z "$PYTHON" ]; then
    echo "Memingo necesita Python 3.10 o superior." >&2
    echo "Instala Python desde tu sistema o desde https://www.python.org/" >&2
    exit 1
fi

if ! "$PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    echo "Memingo necesita Python 3.10 o superior." >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
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

case ":${PATH:-}:" in
    *:"$BIN_DIR":*) ;;
    *) echo "Add $BIN_DIR to PATH to run: memingo" ;;
esac

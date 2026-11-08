#!/usr/bin/env sh
set -eu

REPO_URL=${MEMINGO_REPO_URL:-https://github.com/Reaccionador2Jeje/Memingo/archive/refs/heads/main.zip}
INSTALL_DIR=${MEMINGO_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/memingo}
BIN_DIR=${MEMINGO_BIN_DIR:-$HOME/.local/bin}
PYTHON=${MEMINGO_PYTHON:-}

if [ -z "$PYTHON" ]; then
  PYTHON=$(command -v python3 || command -v python || true)
fi

if [ -z "$PYTHON" ]; then
  cat >&2 <<'MSG'
Memingo necesita Python 3.10 o superior.
Linux: sudo apt install python3 (Debian/Ubuntu) o usa tu gestor de paquetes.
macOS: brew install python3, o instala Python desde python.org.
Luego vuelve a ejecutar este instalador.
MSG
  exit 1
fi

if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  echo "Memingo necesita Python 3.10 o superior." >&2
  exit 1
fi

TMP_DIR=$("$PYTHON" -c 'import tempfile; print(tempfile.mkdtemp(prefix="memingo-"))')
export MEMINGO_INSTALL_DIR="$INSTALL_DIR"
export MEMINGO_BIN_DIR="$BIN_DIR"
export MEMINGO_REPO_URL="$REPO_URL"
export MEMINGO_PYTHON="$PYTHON"
export MEMINGO_TMP_DIR="$TMP_DIR"

"$PYTHON" - "$REPO_URL" "$INSTALL_DIR" "$BIN_DIR" "$PYTHON" <<'PY'
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

repo_url, install_dir, bin_dir, python_path = sys.argv[1:5]
tmp_dir = Path(os.environ["MEMINGO_TMP_DIR"])
archive = tmp_dir / "memingo.zip"
extract_dir = tmp_dir / "source"

try:
    with urllib.request.urlopen(repo_url, timeout=60) as response:
        archive.write_bytes(response.read())
except Exception as error:
    print(f"Memingo: no se pudo descargar el runtime: {error}", file=sys.stderr)
    raise SystemExit(1)

extract_dir.mkdir(parents=True, exist_ok=True)
try:
    bundle = zipfile.ZipFile(archive)
except (zipfile.BadZipFile, OSError) as error:
    print(f"Memingo: archivo de instalación inválido: {error}", file=sys.stderr)
    raise SystemExit(1)
with bundle:
    root = extract_dir.resolve()
    for member in bundle.infolist():
        member_path = Path(member.filename)
        if member_path.is_absolute() or ".." in member_path.parts:
            print(f"Memingo: ruta insegura en el archivo: {member.filename}", file=sys.stderr)
            raise SystemExit(1)
        target = (root / member.filename).resolve()
        if root != target and root not in target.parents:
            print(f"Memingo: ruta insegura en el archivo: {member.filename}", file=sys.stderr)
            raise SystemExit(1)
        if (member.external_attr >> 16) & 0o170000 == 0o120000:
            print(f"Memingo: enlace simbólico no permitido: {member.filename}", file=sys.stderr)
            raise SystemExit(1)
    bundle.extractall(root)

source = next((item for item in extract_dir.iterdir() if item.is_dir() and (item / "memingo").is_dir()), None)
if source is None:
    print("Memingo: la descarga no contiene el runtime.", file=sys.stderr)
    raise SystemExit(1)

install = Path(install_dir)
bin_path = Path(bin_dir)
try:
    install.mkdir(parents=True, exist_ok=True)
    bin_path.mkdir(parents=True, exist_ok=True)

    package_target = install / "memingo"
    launcher_target = install / "launcher.py"
    mgoa_target = install / "mgoa.py"
    if package_target.exists():
        shutil.rmtree(package_target)
    shutil.copytree(source / "memingo", package_target)
    shutil.copy2(source / "scripts" / "launcher.py", launcher_target)
    shutil.copy2(source / "scripts" / "mgoa.py", mgoa_target)

    wrapper = bin_path / "memingo"
    wrapper.write_text(
        "#!/usr/bin/env sh\n"
        f'exec "{python_path}" -I "{launcher_target}" "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    mgoa_wrapper = bin_path / "mgoa"
    mgoa_wrapper.write_text(
        "#!/usr/bin/env sh\n"
        f'exec "{python_path}" -I "{mgoa_target}" "$@"\n',
        encoding="utf-8",
    )
    mgoa_wrapper.chmod(0o755)
except OSError as error:
    print(f"Memingo: no se pudo instalar el runtime: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Memingo installed successfully.")
print(f"Runtime: {install}")
print(f"Commands: {wrapper}, {mgoa_wrapper}")
print()
print("Si memingo o mgoa no se encuentran, ejecuta:")
print(f'  export PATH="{bin_path}:$PATH"')
print("  hash -r")
print("  memingo --version")
print("  mgoa --version")

path_line = f'export PATH="{bin_path}:$PATH"'
for profile in (Path.home() / ".profile", Path.home() / ".bashrc"):
    try:
        text = profile.read_text(encoding="utf-8") if profile.exists() else ""
        if str(bin_path) not in text:
            with profile.open("a", encoding="utf-8") as file:
                file.write("\n# Memingo\n" + path_line + "\n")
    except OSError:
        pass
PY

import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
version = "0.2.0"

version_file = ROOT / "memingo" / "version.py"
match = re.search(r'__version__\s*=\s*"([^"]+)"', version_file.read_text(encoding="utf-8"))
if match:
    version = match.group(1)

if len(sys.argv) > 1:
    version = sys.argv[1]

DIST.mkdir(parents=True, exist_ok=True)
staging = DIST / "memingo-release-staging"
if staging.exists():
    shutil.rmtree(staging)

for directory in ("memingo", "scripts", "examples", "tests"):
    shutil.copytree(
        ROOT / directory,
        staging / directory,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
for file_name in ("README.md", "LANGUAGE.md", "LICENSE", "pyproject.toml", "TODO.md", "memingo.toml.example"):
    source = ROOT / file_name
    if source.exists():
        shutil.copy2(source, staging / file_name)

archive = DIST / f"memingo-{version}-all-platforms"
archive_path = Path(str(archive) + ".zip")
if archive_path.exists():
    archive_path.unlink()
shutil.make_archive(str(archive), "zip", staging)
shutil.rmtree(staging)
print(archive_path)

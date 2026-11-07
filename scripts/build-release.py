import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
version = "0.1.0"

if len(sys.argv) > 1:
    version = sys.argv[1]

DIST.mkdir(parents=True, exist_ok=True)
staging = DIST / "memingo-release-staging"
if staging.exists():
    shutil.rmtree(staging)

for directory in ("memingo", "scripts", "examples", "tests"):
    shutil.copytree(ROOT / directory, staging / directory)
for file_name in ("README.md", "LICENSE", "pyproject.toml", "TODO.md", "memingo.toml.example"):
    source = ROOT / file_name
    if source.exists():
        shutil.copy2(source, staging / file_name)

archive = DIST / f"memingo-{version}-all-platforms"
if Path(str(archive) + ".zip").exists():
    Path(str(archive) + ".zip").unlink()
shutil.make_archive(str(archive), "zip", staging)
shutil.rmtree(staging)
print(archive.with_suffix(".zip"))

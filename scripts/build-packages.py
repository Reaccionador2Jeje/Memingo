#!/usr/bin/env python3
import argparse
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def read_version():
    version_file = ROOT / "memingo" / "__init__.py"
    match = re.search(r'__version__\s*=\s*"([^"]+)"', version_file.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError("Could not read the Memingo version")
    return match.group(1)


def ensure_command(name, package_hint):
    if shutil.which(name):
        return True
    print(f"Memingo package builder: {name} is required ({package_hint})", file=sys.stderr)
    return False


def copy_runtime(staging):
    runtime = staging / "usr" / "lib" / "memingo"
    runtime.mkdir(parents=True)
    shutil.copytree(ROOT / "memingo", runtime / "memingo", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(ROOT / "scripts" / "launcher.py", runtime / "launcher.py")
    shutil.copy2(ROOT / "scripts" / "mgoa.py", runtime / "mgoa.py")


def write_wrappers(staging):
    bin_dir = staging / "usr" / "bin"
    bin_dir.mkdir(parents=True)
    for name, launcher in (("memingo", "launcher.py"), ("mgoa", "mgoa.py")):
        wrapper = bin_dir / name
        wrapper.write_text(
            "#!/usr/bin/sh\n"
            f'exec /usr/bin/python3 -I /usr/lib/memingo/{launcher} "$@"\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o755)


def build_deb(version):
    if not ensure_command("dpkg-deb", "install the dpkg package"):
        return None

    staging = DIST / "memingo-deb-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    copy_runtime(staging)
    write_wrappers(staging)

    control_dir = staging / "DEBIAN"
    control_dir.mkdir()
    (control_dir / "control").write_text(
        "Package: memingo\n"
        "Version: %s\n"
        "Section: devel\n"
        "Priority: optional\n"
        "Architecture: all\n"
        "Depends: python3 (>= 3.10)\n"
        "Maintainer: Memingo <noreply@example.com>\n"
        "Description: Meme-inspired programming language and package manager\n"
        " Memingo includes the memingo interpreter and the mgoa package manager.\n" % version,
        encoding="utf-8",
    )

    output = DIST / f"memingo_{version}_all.deb"
    if output.exists():
        output.unlink()
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(staging), str(output)], check=True)
    shutil.rmtree(staging)
    return output


def build_rpm(version):
    if not ensure_command("rpmbuild", "install rpm-build"):
        return None

    rpm_version = version.replace("-", "_")
    with tempfile.TemporaryDirectory(prefix="memingo-rpm-") as temporary:
        temporary_path = Path(temporary)
        topdir = temporary_path / "rpmbuild"
        for directory in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
            (topdir / directory).mkdir(parents=True)

        source_root = temporary_path / f"memingo-{rpm_version}"
        source_root.mkdir()
        shutil.copytree(ROOT / "memingo", source_root / "memingo", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(ROOT / "scripts" / "launcher.py", source_root / "launcher.py")
        shutil.copy2(ROOT / "scripts" / "mgoa.py", source_root / "mgoa.py")

        source_archive = topdir / "SOURCES" / f"memingo-{rpm_version}.tar.gz"
        with tarfile.open(source_archive, "w:gz") as archive:
            archive.add(source_root, arcname=f"memingo-{rpm_version}")

        spec = topdir / "SPECS" / "memingo.spec"
        spec.write_text(
            f"Name: memingo\n"
            f"Version: {rpm_version}\n"
            "Release: 1%{?dist}\n"
            "Summary: Meme-inspired programming language and package manager\n"
            "License: BSD-3-Clause\n"
            "BuildArch: noarch\n"
            "Requires: python3 >= 3.10\n"
            "Source0: memingo-%{version}.tar.gz\n\n"
            "%description\n"
            "Memingo includes the memingo interpreter and the mgoa package manager.\n\n"
            "%prep\n"
            "%setup -q\n\n"
            "%build\n\n"
            "%install\n"
            "rm -rf %{buildroot}\n"
            "mkdir -p %{buildroot}/usr/lib/memingo %{buildroot}/usr/bin\n"
            "cp -a memingo %{buildroot}/usr/lib/memingo/\n"
            "install -m 0644 launcher.py %{buildroot}/usr/lib/memingo/launcher.py\n"
            "install -m 0644 mgoa.py %{buildroot}/usr/lib/memingo/mgoa.py\n"
            "cat > %{buildroot}/usr/bin/memingo <<'EOF_WRAPPER'\n"
            "#!/usr/bin/sh\n"
            "exec /usr/bin/python3 -I /usr/lib/memingo/launcher.py \"$@\"\n"
            "EOF_WRAPPER\n"
            "cat > %{buildroot}/usr/bin/mgoa <<'EOF_WRAPPER'\n"
            "#!/usr/bin/sh\n"
            "exec /usr/bin/python3 -I /usr/lib/memingo/mgoa.py \"$@\"\n"
            "EOF_WRAPPER\n"
            "chmod 0755 %{buildroot}/usr/bin/memingo %{buildroot}/usr/bin/mgoa\n\n"
            "%files\n"
            "%defattr(-,root,root,-)\n"
            "/usr/lib/memingo\n"
            "/usr/bin/memingo\n"
            "/usr/bin/mgoa\n",
            encoding="utf-8",
        )

        subprocess.run(["rpmbuild", "-ba", "--define", f"_topdir {topdir}", str(spec)], check=True)
        built_rpms = list((topdir / "RPMS").rglob("*.rpm"))
        if not built_rpms:
            raise RuntimeError("rpmbuild completed without producing an RPM")
        output = DIST / built_rpms[0].name
        if output.exists():
            output.unlink()
        shutil.copy2(built_rpms[0], output)
        return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build Memingo Debian and RPM packages")
    parser.add_argument("--only", choices=("deb", "rpm"), help="Build only one package format")
    args = parser.parse_args(argv)

    DIST.mkdir(parents=True, exist_ok=True)
    version = read_version()
    outputs = []

    if args.only in (None, "deb"):
        output = build_deb(version)
        if output:
            outputs.append(output)
    if args.only in (None, "rpm"):
        output = build_rpm(version)
        if output:
            outputs.append(output)

    if not outputs:
        return 1
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

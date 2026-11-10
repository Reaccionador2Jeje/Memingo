#!/usr/bin/env python3
"""Copy or download the Memingo IDE Linux packages into dist/.

The Memingo IDE is built in the Memingo-IDE repository. This helper makes
its .deb, .rpm and .pkg.tar.zst artifacts available to the unified Memingo
APT, DNF and pacman repositories.

Environment variables:
  MEMINGO_IDE_ARTIFACTS  Local directory containing the IDE artifacts.
  MEMINGO_IDE_TAG        Release tag to download (default: latest release).
  GITHUB_TOKEN           Optional token for the GitHub API.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
REPOSITORY = "Reaccionador2Jeje/Memingo-IDE"
EXTENSIONS = (".deb", ".rpm", ".pkg.tar.zst")


def copy_local(directory: Path) -> int:
    copied = 0
    for path in sorted(directory.iterdir()):
        if path.is_file() and any(path.name.endswith(extension) for extension in EXTENSIONS):
            DIST.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, DIST / path.name)
            print(DIST / path.name)
            copied += 1
    return copied


def api_request(url: str, token: str | None) -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "memingo-packages"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download(url: str, destination: Path, token: str | None) -> None:
    headers = {"User-Agent": "memingo-packages"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as stream:
        shutil.copyfileobj(response, stream)


def download_release(tag: str | None, token: str | None) -> int:
    if tag:
        url = f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{tag}"
    else:
        url = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
    try:
        release = api_request(url, token)
    except urllib.error.HTTPError as error:
        print(f"No se pudo consultar la release del IDE ({error.code}); se omite.", file=sys.stderr)
        return 0
    except urllib.error.URLError as error:
        print(f"No se pudo conectar con GitHub ({error.reason}); se omite.", file=sys.stderr)
        return 0

    assets = [
        asset
        for asset in release.get("assets", [])
        if any(asset.get("name", "").endswith(extension) for extension in EXTENSIONS)
    ]
    if not assets:
        print("La release del IDE no contiene paquetes Linux; se omite.", file=sys.stderr)
        return 0

    DIST.mkdir(parents=True, exist_ok=True)
    for asset in assets:
        destination = DIST / asset["name"]
        print(destination)
        download(asset["browser_download_url"], destination, token)
    return len(assets)


def main(argv=None) -> int:
    local = os.environ.get("MEMINGO_IDE_ARTIFACTS")
    if local:
        directory = Path(local).expanduser().resolve()
        if not directory.is_dir():
            print(f"Directorio de artefactos del IDE inexistente: {directory}", file=sys.stderr)
            return 1
        count = copy_local(directory)
    else:
        count = download_release(os.environ.get("MEMINGO_IDE_TAG"), os.environ.get("GITHUB_TOKEN"))

    if count == 0:
        print("No se añadieron paquetes del IDE. La release se puede publicar sin ellos.", file=sys.stderr)
    else:
        print(f"{count} paquete(s) del IDE listos en dist/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

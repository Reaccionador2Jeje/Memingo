# Memingo on Arch Linux

Memingo is published through two complementary Arch Linux channels:

1. **Self-hosted pacman repository** (recommended, updated with every release):
   `https://reaccionador2jeje.github.io/Memingo/linux/arch/x86_64`
2. **AUR PKGBUILDs** in this directory, usable with `yay`, `paru` or plain
   `makepkg`.

## Self-hosted pacman repository

```bash
curl -fsSLo /tmp/memingo.asc https://reaccionador2jeje.github.io/Memingo/linux/memingo.asc
sudo install -m 0644 /tmp/memingo.asc /etc/pacman.d/memingo.asc

sudo tee -a /etc/pacman.conf >/dev/null <<'EOF'

[memingo]
SigLevel = Required DatabaseOptional
Server = https://reaccionador2jeje.github.io/Memingo/linux/arch/x86_64
EOF

sudo pacman -Sy
sudo pacman -S memingo            # runtime and mgoa
sudo pacman -S memingo-registry   # offline official registry
sudo pacman -S memingo-vscode     # VS Code extension bundle
sudo pacman -S memingo-full       # everything above
```

`memingo-ide` is available from the same repository once a matching IDE
release has been published.

## AUR packages

| Package | Description |
| --- | --- |
| `memingo` | Runtime, `memingo` and `mgoa` commands |
| `memingo-registry` | Offline copy of the official mgoa registry |
| `memingo-vscode` | VS Code extension and installer helper |
| `memingo-full` | Meta package with the three packages above |
| `memingo-ide-bin` | Prebuilt Memingo IDE from GitHub releases |

With `yay` or `paru`:

```bash
yay -S memingo-full
# or
paru -S memingo-full
```

With plain `pacman` + `makepkg`:

```bash
git clone https://aur.archlinux.org/memingo-full.git
cd memingo-full
makepkg -si
```

The PKGBUILDs build from the tagged source archive on GitHub. They use
`SKIP` checksums because GitHub archive tarballs are generated on demand;
verify the tag and commit before building if you need reproducible inputs.
The AUR `memingo-ide-bin` package repackages the `.pkg.tar.zst` asset from
the Memingo IDE GitHub release.

## Regenerating `.SRCINFO`

After editing a `PKGBUILD`, regenerate its metadata:

```bash
cd packaging/aur/<package>
makepkg --printsrcinfo > .SRCINFO
```

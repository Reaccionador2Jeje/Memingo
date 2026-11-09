# Deploy Memingo to GitHub Pages

Memingo publica paquetes nativos únicamente para distribuciones basadas en APT (DEB) y DNF (RPM). La publicación en AUR queda fuera del alcance del proyecto.

## Automatic deployment

1. Open the repository settings on GitHub.
2. Go to **Pages**.
3. Set **Build and deployment** to **GitHub Actions**.
4. Push to `main` or `master`, or run **Deploy Memingo to GitHub Pages** manually.

The workflow publishes the `site/` directory.

The project Pages URL is:

`https://reaccionador2jeje.github.io/Memingo/`

## Native Linux packages

Build `.deb` and `.rpm` artifacts with:

```bash
python3 scripts/build-packages.py
```

Both packages install the runtime under `/usr/lib/memingo` and expose `memingo` and `mgoa` through `/usr/bin`. CI builds them for pull requests and pushes, and stores them as workflow artifacts named `memingo-linux-packages`.

## Package registry

The `mgoa` registry is published with the site at `https://reaccionador2jeje.github.io/Memingo/mgoa/index.json`. Package sources live in `packages/<name>/`; the generated archives live in `site/mgoa/packages/`.

After changing a package source, rebuild the registry before deploying:

```bash
python3 scripts/build-registry.py
python3 scripts/build-registry.py --check
```

The build script creates reproducible ZIPs, computes their SHA-256 digests and rewrites `site/mgoa/index.json`. Commit the source, the archives and the index together so published checksums stay valid. `tests/test_registry_packages.py` verifies the catalog, archives, checksums, installation and every package `self_test()`.

The package repository workflow can publish metadata and artifacts locally or to GitHub Pages. Package signatures must be verified in a clean system before public distribution.

## Create and publish Linux repositories

The `Publish Linux Package Repositories` workflow runs for `v*` tags. It requires the signing secrets below and stops before deployment if the private key or key ID is missing; unsigned APT/RPM repositories are never published. It deploys to GitHub Pages under:

- APT: `https://reaccionador2jeje.github.io/Memingo/linux/apt/`
- RPM: `https://reaccionador2jeje.github.io/Memingo/linux/rpm/`

Generate one repository signing key locally:

```bash
gpg --full-generate-key
GPG_KEY_ID=$(gpg --list-secret-keys --with-colons | awk -F: '$1 == "sec" {print $5; exit}')
gpg --armor --export "$GPG_KEY_ID" > memingo.asc
gpg --armor --export-secret-keys "$GPG_KEY_ID" | base64 -w0 > memingo-private-key.base64
```

Add these GitHub Actions repository secrets under Settings > Secrets and variables > Actions:

- `MEMINGO_GPG_KEY_ID`: the long key fingerprint or key ID.
- `MEMINGO_GPG_PASSPHRASE`: the key passphrase. Prefer a strong passphrase stored only as this Actions secret; never commit it or paste it into issues, pull requests, or chat.
- `MEMINGO_GPG_PRIVATE_KEY`: the Base64 content of `memingo-private-key.base64`.

Before publishing, the workflow performs a test signature with the configured key, verifies `InRelease` and `Release.gpg`, checks each RPM package signature, and verifies the RPM repository metadata signature. A failed verification stops deployment.

To publish a release:

```bash
git tag v0.2.0
git push origin v0.2.0
```

The public key is exported to `site/linux/memingo.asc`. APT signs `Release` with `InRelease` and `Release.gpg`; RPM signs packages and `repomd.xml`. The APT repository publishes indexes for amd64, arm64, armhf and i386, plus any additional architecture detected in the built packages.

Install from APT after the workflow deploys:

```bash
curl -fsSLo memingo.asc https://reaccionador2jeje.github.io/Memingo/linux/memingo.asc
sudo install -m 0644 memingo.asc /usr/share/keyrings/memingo.asc
echo 'deb [signed-by=/usr/share/keyrings/memingo.asc] https://reaccionador2jeje.github.io/Memingo/linux/apt stable main' | sudo tee /etc/apt/sources.list.d/memingo.list
sudo apt update
sudo apt install memingo
```

Install from RPM repositories:

```bash
sudo tee /etc/yum.repos.d/memingo.repo >/dev/null <<'EOF'
[memingo]
name=Memingo
baseurl=https://reaccionador2jeje.github.io/Memingo/linux/rpm
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://reaccionador2jeje.github.io/Memingo/linux/memingo.asc
EOF
sudo dnf install memingo
```

Do not commit private keys or Base64 private-key output. Verify packages and signatures in a clean container before enabling public distribution.

## Manual local preview

```bash
cd site
python3 -m http.server 4173
```

Open `http://127.0.0.1:4173/`.

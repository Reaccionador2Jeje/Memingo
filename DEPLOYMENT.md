# Deploy Memingo to GitHub Pages

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

To publish a package repository, upload the generated artifacts to an APT or RPM repository service, create repository metadata, sign it, and add the corresponding repository configuration to `memingo.toml` documentation and installer assets. Do not publish the packages until their checksums and signatures have been verified in a clean system.

## Manual local preview

```bash
cd site
python3 -m http.server 4173
```

Open `http://127.0.0.1:4173/`.

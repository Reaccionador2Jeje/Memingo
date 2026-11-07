# Deploy Memingo to GitHub Pages

## Automatic deployment

1. Open the repository settings on GitHub.
2. Go to **Pages**.
3. Set **Build and deployment** to **GitHub Actions**.
4. Push to `main` or `master`, or run **Deploy Memingo to GitHub Pages** manually.

The workflow publishes the `site/` directory.

The project Pages URL is:

`https://reaccionador2jeje.github.io/Memingo/`

## Manual local preview

```bash
cd site
python3 -m http.server 4173
```

Open `http://127.0.0.1:4173/`.

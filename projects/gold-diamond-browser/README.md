# Gold & Diamond Browser

A cross-platform desktop browser powered by **Memingo** and **Qt WebEngine**.

## v0.1.0

- Chromium-based web rendering through Qt WebEngine
- Address bar with URL detection and web search
- Back, forward, reload and home controls
- Multiple tabs
- Keyboard shortcuts: Ctrl+T, Ctrl+W, Ctrl+L and Ctrl+R
- Gold-and-diamond dark interface
- Browser identity and default settings defined in `app.mgo`

## Architecture

- `app.mgo`: Memingo application definition, defaults and generated configuration.
- `gold_diamond_browser/__main__.py`: thin Qt desktop host and WebEngine integration.
- Qt WebEngine provides the web renderer; it is not an engine implemented by Memingo.

The browser configuration is generated at startup by executing `app.mgo` with the Memingo interpreter. The Qt host reads that generated configuration.

## Requirements

- Python 3.10+
- Memingo 0.2+
- Qt for Python (PySide6 with Qt WebEngine)

## Run from this directory

Install Memingo first using its official installer, then:

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS**
```bash
source .venv/bin/activate
```

Install dependencies and start:

```bash
pip install -r requirements.txt
python -m gold_diamond_browser
```

## Notes

Qt WebEngine is based on Chromium and requires its runtime resources and helper process to be included when packaging. Packaging for Windows, Linux and macOS will be added after the first local smoke test.

This is an early browser shell, not yet a hardened daily-use browser. It does not yet include sync, extensions, private browsing, download management or a custom ad/tracker blocker.

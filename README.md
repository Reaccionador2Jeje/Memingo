# Memingo

Memingo is a meme-inspired programming ecosystem for games, apps, servers, packages, the web and the VS Code editor. Version 0.2 includes the interpreter, objects and collections, JSON/HTTP helpers, projects, `mgoa`, a formatter, installers, a CLI, GitHub Pages website and VS Code support.

# Website
Please Visit https://reaccionador2Jeje.github.io/Memingo

## Ecosystem syntax

```mgo
# Vibes are variables
vibe name = "Memingo"
spill "Hello " + name

# When a condition is based, the ritual continues
when 8 > 3 {
    spill "this is based"
} nah {
    spill "that's cringe"
}

vibe i = 1
grind i <= 3 {
    spill i
    i = i + 1
}

# A ritual is a function
ritual factorial(n) {
    when n <= 1 {
        drop 1
    }
    drop n * factorial(n - 1)
}

spill factorial(5)
```

Memingo values are `whole`, `caption`, `party`, `based`, `cringe`, and `ghost`.
Theme keywords include `vibe`, `ritual`, `drop`, `when`, `nah`, `grind`, and `spill`.
Operators include arithmetic, comparison, equality, `&&`, `||`, and `!`.
Built-ins include `headcount()`, `whatkind()`, `json_parse()`, `json_stringify()`, `env()`, `range()`, `keys()`, `push()`, `append()`, `set_value()`, `delete_key()`, `random()`, `random_int()`, `http_get()`, and `http_post()`.
Lists and objects can span multiple lines, including trailing commas.

## MemeCraft

Memingo includes an original playable voxel game inspired by block-building sandboxes. Play it at `site/game.html` or add the `.mgo` world configuration from [examples/minecraft.mgo](examples/minecraft.mgo).


## Memingo Server

Build a JSON HTTP API with a few Memingo rituals:

```mgo
vibe api = http_server()

ritual home(request) {
    drop {status: 200, body: {message: "Hello from Memingo"}}
}

api.get("/", home)
api.listen("127.0.0.1", 8000)
```

Supports GET, POST, PUT and DELETE routes, JSON request bodies, query parameters and custom response headers. See [examples/server.mgo](examples/server.mgo) and the [HTTP API reference](LANGUAGE.md#memingo-server-http-apis). This is a development server; production hosting, middleware and authentication are future work.

## Memingo 1.0 direction

The long-term architecture and phased plan for building concise apps, servers, web projects and games is documented in [ARCHITECTURE.md](ARCHITECTURE.md). The roadmap is tracked in [TODO.md](TODO.md).

## Language reference

See the complete syntax and standard library in [LANGUAGE.md](LANGUAGE.md).

## Core syntax

```mgo
vibe profile = {name: "Ana", role: "builder"}
vibe skills = ["Memingo", "web", "games"]
set_value(profile, "status", "based")

spill profile.name
spill profile["role"]
spill json_stringify(profile)

vibe config = json_parse(env("CONFIG_JSON", "{\\\"mode\\\":\\\"dev\\\"}"))
```

## Standard library highlights

```mgo
spill trim("  memingo  ")
spill join(split("web,games,packages", ","), " + ")
spill sort([3, 1, 2])

ritual double(n) {
    drop n * 2
}

spill map([1, 2, 3], double)
```

Memingo also includes `filter`, `reduce`, `sum`, `min`, `max`, `clamp`, `parse_int`, `parse_float`, `repeat`, `lines`, `unique`, `meme_case`, `shuffle`, `uuid`, `now`, `sleep`, the project-scoped file helpers `read_file`, `write_file`, `file_exists` and `list_files`, and the JSON, environment and HTTP helpers. Shell completions for Bash, Zsh and Fish are available through `memingo completion` and `mgoa completion`. See [LANGUAGE.md](LANGUAGE.md) for the full list.

Activate completions with:

```bash
# Bash: add to ~/.bashrc
source <(memingo completion bash)
source <(mgoa completion bash)

# Zsh: add to ~/.zshrc
source <(memingo completion zsh)
source <(mgoa completion zsh)

# Fish: write permanently
memingo completion fish > ~/.config/fish/completions/memingo.fish
mgoa completion fish > ~/.config/fish/completions/mgoa.fish
```

## Run

```bash
python3 -m memingo run examples/hello.mgo
python3 -m memingo run examples/functions.mgo
python3 -m memingo run examples/minecraft.mgo
python3 -m memingo repl
```

After installing the native command, replace `python3 -m memingo` with `memingo`.

## Test

```bash
python3 -m unittest discover -s tests -v
memingo test
```

## Install Memingo

No `pip` is required. The official installers copy the Memingo runtime and create native commands for both `memingo` and `mgoa`.

### Linux and macOS

```bash
chmod +x scripts/install.sh scripts/uninstall.sh
./scripts/install.sh
export PATH="$HOME/.local/bin:$PATH"
memingo --version
mgoa --version
```

After downloading the public Linux/macOS installer from the website, run it with:

```bash
chmod +x install.sh
sh ./install.sh
export PATH="$HOME/.local/bin:$PATH"
memingo --version
mgoa --version
```

The default command location is `~/.local/bin`. Add that directory to `PATH` if the shell does not find `memingo`.

### Android (Termux)

Termux tiene su propio sistema de paquetes: los paquetes APT de Debian/Ubuntu y RPM de Fedora no se instalan directamente allí. Usa el instalador de Memingo compatible con Termux:

```bash
pkg update
pkg install -y git python
git clone https://github.com/Reaccionador2Jeje/Memingo.git
cd Memingo
sh scripts/install.sh
hash -r
memingo --version
mgoa --version
```

El instalador detecta Termux y coloca `memingo` y `mgoa` en `$PREFIX/bin`. Para actualizar, ejecuta `git pull` y luego `sh scripts/install.sh` desde la carpeta del proyecto. Para desinstalar, ejecuta `sh scripts/uninstall.sh`.

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
# Open a new terminal, then run:
memingo --version
mgoa --version
```

The default install location is `%LOCALAPPDATA%\Memingo`. The installer adds its `bin` directory to the user PATH.

Python 3.10 or newer is required. The installer does not download or install packages through `pip`.

## Release archive

```bash
python3 scripts/build-release.py
```

This creates an all-platform source release in `dist/`. Linux/macOS users run `scripts/install.sh`; Windows users run `scripts/install.ps1`.

## Distribution packages

Build native packages for Debian/Ubuntu (`apt`) and Fedora/RHEL (`dnf`):

```bash
# Debian/Ubuntu (.deb)
python3 scripts/build-packages.py --only deb
# Fedora/RHEL (.rpm)
python3 scripts/build-packages.py --only rpm
# Both
python3 scripts/build-packages.py
```

Artifacts are written to `dist/` as `memingo_<version>_all.deb` and `memingo-<version>-1.noarch.rpm`. On Fedora/RHEL, the RPM release may include a distribution suffix such as `1.fc41`.

Building the `.deb` requires `dpkg-deb` (part of `dpkg`). Building the `.rpm` requires `rpmbuild`. Both packages install the shared runtime and expose both `memingo` and `mgoa` commands:

```bash
sudo apt install rpm        # Debian/Ubuntu
sudo dnf install rpm-build  # Fedora/RHEL
```

Install the generated packages:

```bash
# Debian/Ubuntu
sudo apt install ./dist/memingo_*_all.deb

# Fedora/RHEL
sudo dnf install ./dist/memingo-*.noarch.rpm
```

To create repository metadata locally:

```bash
python3 scripts/build-packages.py
python3 scripts/build-linux-repositories.py
```

Metadata is written to `site/linux/apt` and `site/linux/rpm`. The GitHub Pages release workflow signs and publishes it automatically when `MEMINGO_GPG_*` Actions secrets are configured. Full setup is documented in [DEPLOYMENT.md](DEPLOYMENT.md).

After a signed repository release is published, Debian/Ubuntu users can add the APT source:

```bash
curl -fsSLo memingo.asc https://reaccionador2jeje.github.io/Memingo/linux/memingo.asc
sudo install -m 0644 memingo.asc /usr/share/keyrings/memingo.asc
echo 'deb [signed-by=/usr/share/keyrings/memingo.asc] https://reaccionador2jeje.github.io/Memingo/linux/apt stable main' | sudo tee /etc/apt/sources.list.d/memingo.list
sudo apt update
sudo apt install memingo
```

Fedora/RHEL users can configure DNF with the repository file shown in [DEPLOYMENT.md](DEPLOYMENT.md). Repository publication requires the signing secrets; unsigned repositories are not deployed.

Both packages install the runtime under `/usr/lib/memingo`, the `memingo` and `mgoa` commands in `/usr/bin`, and documentation in `/usr/share/doc/memingo`. Python 3.10 or newer is required.

The CLI now uses an art-directed terminal interface for every interactive subcommand: compact `MEMINGO / COMMAND` headers frame project, package, build, formatting and diagnostic workflows. `run`, `eval`, `completion`, REPL and watcher output remain clean or intentionally interactive so they can be piped safely. mgoa uses the same visual language for package commands. Run `memingo status`, `memingo doctor`, or `mgoa` without arguments for a visual overview.

Project-aware commands create a missing `memingo.toml` automatically. Commands such as `run`, `build`, `info`, `deps`, `clean`, `stats`, `install`, `update`, `add`, `remove`, and the equivalent `mgoa` project commands also generate `main.mgo`, `.env`, `.gitignore`, and the dependencies table when needed.

## Ecosystem commands

```bash
memingo init my-app --name my-app
memingo run
memingo run my-app
memingo eval 'spill 2 + 2'
memingo check examples
memingo dev
memingo test
memingo build
memingo serve public
memingo install
memingo remove meme-core
memingo info
memingo deps
memingo clean
memingo manifest
memingo doctor
memingo update-self
memingo fmt examples
mgoa search
mgoa info hello-memes
mgoa list
mgoa add hello-memes
mgoa install
mgoa update
```

`memingo install`, `memingo update`, `memingo add`, `mgoa install` and `mgoa add` create the project scaffolding and `memingo.toml` automatically when they are missing. An existing manifest is never overwritten. Use `memingo manifest` to create just the missing manifest for the current directory.

## Package manager (mgoa)

The default registry is the curated Memingo registry, but packages do not need to be approved to be installed. `mgoa` supports:

- package names from the configured registry (`mgoa add hello-memes`)
- any registry exposing either an `approved.packages` table or a plain `packages` table
- local directories and ZIP archives
- direct HTTP(S) package archive URLs, with optional `#sha256=<digest>` pinning

```bash
mgoa search
mgoa info hello-memes
mgoa list
mgoa add hello-memes
mgoa add ./mypackage
mgoa add ./mypackage.zip
mgoa add https://example.com/packages/mypackage-1.0.0.zip
mgoa add https://example.com/packages/mypackage-1.0.0.zip#sha256=<digest>
mgoa install
mgoa update
mgoa remove hello-memes
mgoa publish ./mypackage
```

`mgoa info <package>` shows the registry metadata and every published version. `mgoa list` shows the packages recorded in `memingo.toml` and `memingo.lock.json`, including source, approval and install status.

Use `--registry <url>` or `MGOA_REGISTRY` to install from a different registry. The official registry remains the default.

`mgoa` records the package source (URL, registry, or local path) and its checksums in `memingo.lock.json`. `mgoa install` reuses that source, so installs stay reproducible whether or not the package is approved. Safe ZIP extraction, path traversal protection, and SHA-256 verification apply to every source.

### Registry catalog

The curated registry ships with real packages covering math, text, collections, files, validation, CLI output, tests, games and memes. Every package includes a `self_test()` ritual that returns `based` when its checks pass.

| Package | What it provides |
| --- | --- |
| `hello-memes` | Minimal greeting package and `borrow` example |
| `mathkit` | Primes, factorials, GCD/LCM, Fibonacci and digit helpers |
| `statkit` | Average, median, variance, standard deviation and percentiles |
| `stringkit` | Slugs, initials, padding, truncation and palindromes |
| `listkit` | Chunking, flattening, lookups, `pluck`, `zip` and list predicates |
| `jsonkit` | Safe paths, deep updates, merging, picking and omitting keys |
| `envkit` | Typed environment variables: text, int, bool, list and JSON |
| `filekit` | Read/write JSON, lines and text in the current project |
| `randomkit` | Picks, samples, dice, coin flips and random digits |
| `timekit` | Timestamps, durations, weekdays and weekend checks |
| `uuidkit` | Short ids, tokens and UUID validation |
| `validate` | Email, URL, integer, float, hex color and password validators |
| `template` | Tiny text templates, HTML escaping, indentation and wrapping |
| `color` | Hex/RGB conversion, luminance, contrast and lighten/darken |
| `markdown` | Headings, lists, links, quotes and code blocks |
| `csvkit` | Parse, build and query simple CSV data |
| `gamekit` | Health, damage, healing, XP levels and weighted loot |
| `clikit` | Terminal messages, progress bars, byte sizes and banners |
| `testing` | Expectation objects and pass/fail summaries |
| `memes` | Hype, roast, meme case and based-or-cringe helpers |

Package sources live in `packages/<name>/`. Regenerate the published ZIPs, SHA-256 checksums and `site/mgoa/index.json` after changing a package:

```bash
python3 scripts/build-registry.py
python3 scripts/build-registry.py --check
```

Use `--base-url` to preview a registry served from another location. `--check` validates the existing archives and checksums without rewriting them.

Packages can export rituals and vibes using `borrow`:

```mgo
borrow "hello-memes"
greet("Team")
```

## Next steps

The CLI, package manager, web-server launcher, tooling, and native runtime are tracked in [TODO.md](TODO.md).

### Debugging

Run `memingo debug path/to/main.mgo` to execute a source file and emit a JSON statement trace prefixed with `MEMINGO_DEBUG:`. Each event includes its source line, statement type and visible variable snapshot. Mark source lines with `--breakpoints 3,8` to flag matching trace events. The trace is capped at 10,000 statements to prevent unbounded memory use.

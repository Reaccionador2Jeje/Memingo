# Memingo

Memingo is a meme-inspired programming ecosystem for games, apps, servers, packages, the web and the VS Code editor. Version 0.2 includes the interpreter, objects and collections, JSON/HTTP helpers, projects, `mgoa`, a formatter, installers, a CLI, GitHub Pages website and VS Code support.

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

Memingo also includes `filter`, `reduce`, `sum`, `min`, `max`, `clamp`, `parse_int`, `parse_float`, `repeat`, `lines`, `unique`, `now`, `sleep`, the project-scoped file helpers `read_file`, `write_file`, `file_exists` and `list_files`, and the JSON, environment and HTTP helpers. See [LANGUAGE.md](LANGUAGE.md) for the full list.

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

Building the `.deb` requires `dpkg-deb` (part of `dpkg`). Building the `.rpm` requires `rpmbuild`:

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

Both packages install the runtime under `/usr/share/memingo`, the `memingo` and `mgoa` commands in `/usr/bin`, and documentation in `/usr/share/doc/memingo`. Python 3.10 or newer is required.

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

Packages can export rituals and vibes using `borrow`:

```mgo
borrow "hello-memes"
greet("Team")
```

## Next steps

The CLI, package manager, web-server launcher, tooling, and native runtime are tracked in [TODO.md](TODO.md).
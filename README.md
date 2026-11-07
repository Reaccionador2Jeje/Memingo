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

## Ecosystem commands

```bash
memingo init my-app --name my-app
memingo run
memingo run my-app
memingo dev
memingo test
memingo build
memingo serve public
memingo install
memingo remove meme-core
memingo doctor
memingo update-self
memingo fmt examples
mgoa search
mgoa add hello-memes
mgoa install
mgoa update
```

## Memingo Approved (mgoa)

```bash
mgoa search
mgoa add hello-memes
mgoa install
mgoa remove hello-memes
mgoa publish ./mypackage
```

The registry supports SHA-256 digests for package archives. `mgoa publish` writes an archive plus a `.sha256` checksum file, and installations verify the lockfile digest before replacing an installed package.

Packages can export rituals and vibes using `borrow`:

```mgo
borrow "hello-memes"
greet("Team")
```

## Next steps

The CLI, package manager, web-server launcher, tooling, and native runtime are tracked in [TODO.md](TODO.md).
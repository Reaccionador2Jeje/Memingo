# Memingo

Memingo is a programming language with internet-meme-inspired functions for games, servers, apps, and tools. This repository currently contains the first executable MVP of the language and interpreter.

## MVP syntax

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
Built-ins currently include `headcount()` and `whatkind()`.

## Run

```bash
memingo run examples/hello.mgo
memingo run examples/functions.mgo
memingo repl
```

## Test

```bash
python -m unittest discover -s tests -v
```

## Install Memingo

No `pip` is required. The official installers copy the Memingo runtime and create a native command for your platform.

### Linux and macOS

```bash
chmod +x scripts/install.sh scripts/uninstall.sh
./scripts/install.sh
export PATH="$HOME/.local/bin:$PATH"
memingo --version
```

After downloading the public Linux/macOS installer from the website, run it with:

```bash
chmod +x install.sh
sh ./install.sh
export PATH="$HOME/.local/bin:$PATH"
memingo --version
```

The default command location is `~/.local/bin`. Add that directory to `PATH` if the shell does not find `memingo`.

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
# Open a new terminal, then run:
memingo --version
```

The default install location is `%LOCALAPPDATA%\Memingo`. The installer adds its `bin` directory to the user PATH.

Python 3.10 or newer is required. The installer does not download or install packages through `pip`.

## Release archive

```bash
python3 scripts/build-release.py
```

This creates an all-platform source release in `dist/`. Linux/macOS users run `scripts/install.sh`; Windows users run `scripts/install.ps1`.

## Project commands

```bash
memingo init my-app --name my-app
memingo run
memingo dev
memingo test
memingo build
memingo serve public
memingo add meme-core=1.2.0
memingo install
memingo remove meme-core
memingo doctor
memingo update-self
```

## Next steps

The CLI, package manager, web-server launcher, tooling, and native runtime are tracked in [TODO.md](TODO.md).
# Memingo for Visual Studio Code

VS Code language support for Memingo `.mgo` files.

## Features

- Syntax highlighting for all meme-themed keywords
- `.mgo` file icons
- Snippets for variables, rituals, conditions and loops
- Run the active file
- Initialize a project
- Open the REPL
- Serve a project directory
- Search and install `mgoa` packages

## Commands

- `Memingo: Run Current File`
- `Memingo: Initialize Project`
- `Memingo: Open REPL`
- `Memingo: Serve Project`
- `Memingo: Search Packages`
- `Memingo: Install Packages`

## Settings

```json
{
  "memingo.executable": "memingo",
  "memingo.packageManagerExecutable": "mgoa",
  "memingo.pythonExecutable": "python3"
}
```

Set `memingo.executable` or `memingo.packageManagerExecutable` to an empty string to run the source packages through Python.

## Development

```bash
code vscode-extension
```

Press `F5` to open an Extension Development Host.

Install Memingo on your system before running commands. Use `memingo doctor` for diagnostics.

## VS Code for the Web

Memingo supports `vscode.dev` and `github.dev` for syntax highlighting, file icons and snippets.

Commands that require the Memingo CLI or a local shell (`Run`, `REPL`, `Serve` and package management) are not available in the browser editor. Use desktop VS Code to run those commands.

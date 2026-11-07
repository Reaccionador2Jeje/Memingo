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

## Commands

- `Memingo: Run Current File`
- `Memingo: Initialize Project`
- `Memingo: Open REPL`
- `Memingo: Serve Project`

## Settings

```json
{
  "memingo.executable": "memingo",
  "memingo.pythonExecutable": "python3"
}
```

## Development

```bash
code vscode-extension
```

Press `F5` to open an Extension Development Host.

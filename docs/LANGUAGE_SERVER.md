# Memingo Language Server

Memingo includes a dependency-free Language Server Protocol (LSP) server. It communicates over JSON-RPC 2.0 using the standard Content-Length framed stdio transport.

## Start

After installing Memingo:

```bash
memingo lsp --stdio
```

The process is intended to be launched by an editor. It reads protocol messages from stdin and writes protocol messages to stdout; diagnostic logs must go to stderr.

## Current capabilities

- Initialize, shutdown and exit lifecycle.
- Open, change, save and close document synchronization.
- Parser-backed diagnostics using the official Memingo lexer and parser.
- Completion items for Memingo keywords, standard-library functions and locally declared names.
- Hover documentation for keywords, built-ins and declared symbols.
- Go to definition for declarations in the active document.
- Document symbols for `vibe` and `ritual` declarations.

## Protocol limits

Incoming JSON-RPC messages are limited to 8 MiB. The server uses only the Python standard library and does not download packages or execute the edited program.

## Editor integration

The desktop Memingo IDE starts this server automatically for `.mgo` and `.mgoa` files when the Memingo runtime is installed and available in PATH. Other language servers remain optional external tools.

The Android WebView edition cannot spawn the Python runtime directly. It provides local Memingo keyword and standard-library suggestions; native Android LSP transport and runtime execution remain future work.

## Current limitations

The first release analyzes one open document at a time. Workspace-wide symbol indexing, cross-file navigation, semantic type inference, references, rename, formatting, and code actions are not yet complete.

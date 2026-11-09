# Memingo Roadmap

## Language
- [x] Lexer with keywords, literals, operators and comments
- [x] Parser for variables, functions, blocks, conditions and loops
- [x] Tree-walking interpreter
- [x] Lists, built-ins and function recursion
- [x] Python package and REPL
- [x] Dictionaries and property/index access
- [x] Standard library for JSON, environment and collections
- [x] Text, number, collection and higher-order standard library
- [x] Project-scoped text file helpers
- [ ] Better error locations and source snippets
- [ ] Modules and imports
- [ ] Standard library for games and apps
- [ ] Native compiler or bytecode VM

## CLI
- [x] `memingo init` project scaffolding
- [x] `memingo run` project and file execution
- [x] `memingo dev` file-change watch mode
- [x] `memingo build` ZIP project archives
- [x] `memingo test` test discovery and reporting
- [x] `memingo repl` explicit REPL command
- [x] Linux/macOS and Windows direct installers
- [x] Environment configuration and `.env` support
- [x] `memingo fmt` source formatter
- [x] `memingo eval` inline code execution
- [x] `memingo check` syntax validation
- [x] `memingo info`, `deps` and `clean` project tools
- [x] `memingo manifest` standalone manifest creation
- [x] Shell completion
- [x] Art-directed CLI dashboards and project status
- [x] Universal subcommand headers for interactive CLI workflows
- [x] Native Linux package repositories
- [x] Automatic project manifest scaffolding
## Package manager
- [x] `memingo.toml` package specification
- [x] `memingo add`, `remove`, `install` and `update` local workflows
- [x] Lockfile generation and digest verification
- [x] Package registry protocol and remote resolution
- [x] Direct archive URLs and non-approved registries
- [x] SHA-256 archive checksums and published `.sha256` files
- [x] Automatic project scaffolding and `memingo.toml` creation
- [x] Curated registry catalog with reproducible ZIP, checksum and index generation
- [ ] Package signing and verification
- [x] Secure local cache

## Web server
- [x] Static HTTP serving
- [x] `memingo serve` static-file launcher
- [x] `memingo api` route-based application launcher for Python and `.mgo` apps
- [x] HTTP client GET/POST and JSON helpers
- [x] Memingo HTTP server API (Python application API v0.3)
- [x] Native `.mgo` API routes, request objects and JSON body parsing
- [x] Routes, methods and middleware (GET/POST/PUT/DELETE, path parameters)
- [x] Native `.mgo` middleware and response modification helpers
- [x] Native JSON, text and HTML responses with custom status codes and headers
- [x] Redirect responses and structured HTTP error responses
- [x] HTTP response header and status validation
- [x] Request and response objects (headers, query, text and JSON helpers)
- [ ] Templates
- [x] URL-encoded and multipart form parsing
- [x] Native file uploads with generated safe filenames and project-scoped storage
- [x] Request and per-file upload size limits
- [ ] Hot reload

## Tooling
- [x] Syntax highlighter
- [x] VS Code extension
- [x] Native Memingo Language Server Protocol (stdio, diagnostics, completions, hover, definition, document symbols)
- [ ] Complete LSP references, rename and code actions
- [ ] Language server protocol extensions and workspace-wide analysis
- [x] Formatter
- [ ] Debugger
- [x] Bilingual website and online documentation
- [ ] Online playground

## Quality
- [x] Continuous integration across Linux, macOS, Windows and Python 3.10-3.13
- [ ] Cross-platform release builds
- [ ] Language specification
- [ ] Contributor guide
- [x] Package documentation
- [x] Curated package catalog and self-tests

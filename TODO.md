# Memingo Roadmap

## Compiler
- [x] Compiler package foundation
- [x] Source files, Unicode-aware offsets, spans and source maps
- [x] Structured diagnostics with terminal rendering
- [x] Source offsets on lexer tokens and statement/expression AST roots
- [x] Initial lexical scopes and symbol lookup
- [x] Primitive and collection type representations
- [x] Basic expression type inference and numeric widening
- [x] Initial static checks for names, assignments, conditions, and calls
- [x] Conservative ritual return-type inference for guaranteed-return paths
- [x] Optional primitive parameter annotations and call-site/body type checking
- [ ] Call-site parameter inference and interprocedural return analysis
- [x] Initial typed HIR and lowering from the existing AST
- [x] Public parse → type-check → HIR compilation API
- [x] Type model invariants and reusable checker state
- [x] Initial type checker, ownership analysis and lexical borrow checks
- [ ] Bytecode format and virtual machine
- [ ] Native backend prototype and benchmarks

## Hybrid Shield
- [x] Runtime execution-step budget and loop guard
- [x] Ritual call-depth limit
- [x] Collection, string and integer size limits
- [x] Reject non-finite floating-point values at runtime boundaries
- [x] Initial static ownership analysis for collection transfers
- [x] Call-scoped exclusive-borrow alias checks for collection mutators
- [x] Explicit shared and mutable reference syntax
- [x] Initial lexical lifetime and scope-based borrow analysis (collection references)
- [ ] Mutation alias analysis and closure capture rules
- [ ] Borrow checker integrated into typed HIR
- [ ] Explicit audited unsafe capabilities and scoped escape hatches
- [x] Approximate runtime memory accounting for reachable interpreter values
- [x] Snapshot-based allocation tracking for reachable interpreter values
- [ ] Allocator-level hooks and hard process memory ceilings
- [ ] Hardware and OS fault reporting through host-specific adapters

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
- [ ] Render parser and lexer errors with source snippets
- [x] Add CLI `memingo analyze` command backed by compiler pipeline
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

# Memingo 1.0 Architecture

## Mission

Memingo should let developers describe complete applications, services, games and websites with a small amount of readable source code. The language should hide repetitive plumbing, not hide important behavior or security decisions.

The goal is not to promise that every project needs only a few lines. A small project should be concise; a complex project should remain understandable, testable and extensible.

## Current baseline (0.2)

- Python-hosted lexer, parser and tree-walking interpreter.
- Variables, functions, conditions, loops, lists, objects and built-ins.
- Project CLI, package manager, static file server and HTTP client helpers.
- No first-class module/import system, application framework, dynamic HTTP API framework, or integrated game runtime yet.

Memingo 1.0 is an evolution of this baseline. Existing 0.2 syntax and commands should remain compatible wherever practical.

## Architecture principles

1. **Small source, real capabilities:** concise declarations should expand into ordinary, inspectable project structure.
2. **One language, multiple targets:** apps, servers, web and games share the parser, type/value model, modules and package manager.
3. **Runtime first:** deliver reliable APIs and project conventions before attempting native compilation.
4. **Portable by default:** keep the core usable on Linux, Windows, macOS and Android/Termux. Platform-specific build tools may be optional.
5. **Explicit security:** filesystem access stays project-scoped by default; network listeners, secrets, permissions and external commands require clear configuration.
6. **Composable modules:** framework features are packages/modules, not a giant hard-coded interpreter.
7. **Test every layer:** syntax, runtime, framework APIs, generated projects and cross-platform CLI behavior need automated tests.

## Target architecture

```text
.mgo source
   |
Lexer -> Parser -> AST -> Semantic checks
                         |
                    Module resolver
                         |
                 Runtime / execution engine
                         |
          +--------------+--------------+
          |              |              |
       Core stdlib    Frameworks     Build system
                      |              |
             +--------+-------+      +--> Web bundles
             |        |       |      +--> Server deploy
           Apps    Server   Games    +--> Desktop/mobile
             |
       Package manager (mgoa)
```

### Core language

- Preserve existing syntax and add source locations to tokens and AST nodes.
- Add modules with deterministic resolution, cycle detection and clear import errors.
- Add a semantic/check phase before execution.
- Define stable public APIs for values, built-ins and module exports.
- Keep the interpreter as the reference runtime while a bytecode VM or compiler is evaluated later.

### Project model

A project is described by `memingo.toml`, with a project kind, entry point, dependencies and optional target settings. Existing manifests must continue to load. New fields are optional and versioned.

Illustrative future manifest:

```toml
[project]
name = "hello-service"
kind = "server"
entry = "src/main.mgo"

[targets]
runtime = "portable"
```

### Framework layers

- **Memingo Web:** pages, components, routing and static asset generation.
- **Memingo Server:** HTTP routes, request/response objects, middleware, JSON and WebSockets.
- **Memingo Apps:** reusable UI components, navigation, state and platform adapters. Start with web/PWA output; native mobile packaging can follow when toolchains are available.
- **Memingo Games:** scenes, entities, input, timing, audio and 2D rendering first. 3D is a later milestone and may use an external rendering backend.

Framework APIs should be implemented as independently testable modules and packages. Do not claim native Android/iOS or 3D support until a working target backend exists.

## Delivery roadmap

### Phase 1 — Core foundation
- [ ] Add architecture and compatibility specification.
- [ ] Add source locations and useful parser/runtime diagnostics.
- [ ] Add module/import syntax and resolver.
- [ ] Add framework/module API boundaries and tests.

### Phase 2 — Server
- [ ] Implement Memingo HTTP server API.
- [ ] Add routes, methods, request/response objects and middleware.
- [ ] Add JSON responses, static assets and safe file uploads.
- [ ] Add development reload and deployment documentation.

### Phase 3 — Web and apps
- [ ] Add web project template and component/page model.
- [ ] Add routing, state and browser event bindings.
- [ ] Generate a standards-based web/PWA output.
- [ ] Document what is web-based versus native.

### Phase 4 — Games
- [ ] Define a backend-independent game API.
- [ ] Implement a small 2D runtime with scenes, sprites, input and audio.
- [ ] Add a playable sample and automated smoke tests.
- [ ] Evaluate 3D and mobile export as separate backend projects.

### Phase 5 — Build and distribution
- [ ] Reproducible builds and dependency lock verification.
- [ ] Target-specific build adapters and diagnostics.
- [ ] Release artifacts for supported platforms.
- [ ] Consider bytecode/native compilation only after runtime APIs stabilize.

## Compatibility and release policy

- Keep 0.2 projects runnable while 1.0 foundations are developed.
- Introduce new syntax behind tests and document it in LANGUAGE.md.
- Do not silently change package resolution or project permissions.
- A target is supported only when CI and a documented smoke test prove it.
- Mark roadmap items complete only after implementation, tests and documentation exist.

## First implementation priority

Start with source locations, diagnostics and modules/imports. These are prerequisites for maintainable frameworks and should land before large app/game APIs.

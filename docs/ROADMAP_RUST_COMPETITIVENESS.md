# Memingo: Rust-Competitiveness Engineering Roadmap

**Project direction:** Hybrid + Productivity  
**Principle:** meme-inspired syntax, serious language engineering.

Memingo does not need to imitate Rust's syntax or promise feature parity. Rust is a mature, ahead-of-time compiled systems language with a strong static type and ownership model. Memingo 0.2 is currently a Python-hosted tree-walking interpreter. The honest goal is to close specific engineering gaps in stages, measure every improvement, and preserve Memingo's approachable identity.

## Current baseline (verified against the repository)

- Lexer, recursive-descent parser, AST and tree-walking interpreter.
- Dynamic values, functions, lists, objects and a standard library.
- Project-scoped file helpers and an HTTP server API.
- MGOA package manager with lockfiles, SHA-256 archive checks and ZIP path protections.
- CLI, formatter, tests, LSP and web IDE.
- Runtime requires Python 3.10+.

These are useful foundations, but they do not make the current runtime comparable to Rust for native performance, compile-time guarantees, memory control or low-level systems programming.

## Engineering rules

1. **No fake performance claims.** Publish reproducible benchmarks with compiler/runtime versions, machine details, warmups and multiple samples.
2. **Safety before speed.** New native or FFI capabilities must be opt-in, bounded and documented. No arbitrary memory access in safe Memingo code.
3. **Compatibility matters.** Existing .mgo programs should keep working unless a clearly versioned breaking change is approved.
4. **Meme syntax stays.** New syntax must fit the vibe / ritual / drop language identity; internal architecture can be conventional.
5. **Every stage ships tests.** No feature is considered complete because a demo happens to run.

## Staged plan

### Stage 1 — Compiler front end and diagnostics

- Define a versioned language specification for tokens, grammar, evaluation order, scoping and runtime errors.
- Add source spans (file, start/end line and column) to tokens and AST nodes.
- Standardize lexer, parser, semantic and runtime diagnostics.
- Add a semantic analysis pass for duplicate declarations, unresolved names, invalid drop placement and function arity.
- Keep dynamic execution as the default; make static checks available through memingo check.

**Exit criteria:** deterministic diagnostics with source snippets; regression tests for every diagnostic; existing language suite remains green.

### Stage 2 — Optional static types

- Introduce optional type annotations without requiring them in existing programs.
- Start with whole, caption, based, cringe, ghost, lists and object shapes.
- Add type inference for literals, expressions, variables and function returns.
- Reject known-invalid operations before execution while preserving dynamic mode.
- Specify how ghost, numeric conversion and collection element types behave.

**Exit criteria:** documented type rules, positive and negative tests, and no silent coercions that change existing program behavior.

### Stage 3 — Bytecode virtual machine

- Keep the AST interpreter as a reference implementation.
- Define a versioned bytecode instruction set and verifier.
- Compile AST nodes to bytecode, then execute on a stack-based VM.
- Add source maps so VM errors still point to .mgo source.
- Compare VM and interpreter outputs on the same conformance suite.

**Exit criteria:** identical observable behavior for the supported language subset; bytecode verifier rejects malformed programs; repeatable benchmarks show where the VM helps and where it does not.

### Stage 4 — Memory and concurrency model

- Specify object lifetime and collection behavior for the VM.
- Add bounded execution options (instruction budget, recursion depth and memory budget).
- Design structured concurrency and cancellation before adding parallel execution.
- Keep unsafe/native memory operations outside the safe language subset.

**Exit criteria:** stress tests, cancellation tests, resource-limit tests and documented guarantees. Do not claim Rust-style ownership until a real static ownership/borrowing model exists and is enforced.

### Stage 5 — Native compilation (long-term)

- Evaluate a portable native backend only after the language semantics and VM are stable.
- Prototype a small, explicit subset first; keep unsupported features as clear compile-time errors.
- Compare LLVM, C transpilation and other backends using maintenance cost, portability and generated-code quality.
- Define a stable ABI before promising native library interoperability.

**Exit criteria:** reproducible cross-platform builds, conformance tests against the interpreter/VM, binary compatibility policy and measured benchmarks.

### Stage 6 — Supply-chain and ecosystem hardening

- Add package signing and signature verification to MGOA.
- Publish provenance for releases and generated registry artifacts.
- Add dependency audit/report commands and reproducible package builds.
- Expand sandboxing and permission boundaries for project code and package scripts.

**Exit criteria:** signed release artifacts, tamper tests, documented trust model and a clear recovery path for revoked keys.

## Immediate next implementation

Start with Stage 1: source spans and a semantic checker. This is the highest-leverage foundation for better diagnostics, a trustworthy LSP, optional static types and later bytecode/native compilation. Do not start a native backend before the language behavior is specified and tested.

---

# Memingo: hoja de ruta para competir técnicamente con Rust

**Dirección:** Hybrid + Productivity.  
**Principio:** sintaxis inspirada en memes; ingeniería seria por dentro.

Memingo no necesita copiar la sintaxis de Rust ni prometer paridad de funciones. Rust es un lenguaje de sistemas maduro, compilado anticipadamente y con un modelo fuerte de tipos estáticos y propiedad. Memingo 0.2 es actualmente un intérprete de árbol ejecutado sobre Python. El objetivo realista es cerrar brechas concretas por etapas, medir cada mejora y conservar una experiencia accesible.

## Punto de partida

El repositorio ya incluye lexer, parser, AST, intérprete, valores dinámicos, funciones, colecciones, biblioteca estándar, herramientas de proyecto, servidor HTTP, MGOA, CLI, formatter, pruebas, LSP e IDE web. Esto es una base útil, pero todavía no equivale a Rust en rendimiento nativo, garantías en compilación, control de memoria ni programación de bajo nivel.

## Reglas de ingeniería

1. No inventar cifras de rendimiento: publicar benchmarks reproducibles.
2. Seguridad antes que velocidad: las capacidades nativas deben ser explícitas y acotadas.
3. Compatibilidad: los programas .mgo existentes deben seguir funcionando salvo cambios versionados.
4. Conservar la identidad meme en la sintaxis; la arquitectura interna puede ser convencional.
5. Toda etapa necesita pruebas automatizadas y criterios de salida.

## Etapas

1. **Frontend y diagnósticos:** especificación del lenguaje, rangos de código fuente, errores uniformes y análisis semántico.
2. **Tipos estáticos opcionales:** anotaciones e inferencia sin romper el modo dinámico.
3. **Máquina virtual de bytecode:** mantener el intérprete como referencia y verificar bytecode antes de ejecutarlo.
4. **Memoria y concurrencia:** límites de recursos, cancelación y un modelo de memoria documentado.
5. **Compilación nativa:** evaluar un backend solo cuando la semántica y la VM estén estables.
6. **Cadena de suministro:** firma de paquetes, verificación, procedencia y builds reproducibles.

**Siguiente implementación:** comenzar por la Etapa 1 con rangos de código fuente y un analizador semántico. No iniciar un backend nativo antes de especificar y probar el comportamiento del lenguaje.

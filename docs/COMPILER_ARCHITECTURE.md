# Memingo Compiler Architecture

**Status:** foundation in progress  
**Language identity:** meme-inspired syntax, production-minded implementation  
**Design priority:** developer productivity

Memingo will evolve incrementally. Its interpreter, package ecosystem, CLI, LSP, and .mgo syntax remain the working baseline while compiler capabilities are added. This avoids a risky rewrite and protects existing projects.

## Goals

- Preserve Memingo's internet-meme identity and existing keywords.
- Keep the language approachable without making runtime safety optional.
- Introduce static analysis and type checking before native code generation.
- Share source locations and diagnostics across compiler, CLI, tests, and LSP.
- Support portable execution and native compilation over time.
- Make each compiler milestone independently testable.

## Planned pipeline

    .mgo source
       |
       v
    Lexer -> Parser -> Existing AST
                        |
                        v
                    Typed HIR
                        |
                        v
               Ownership / Effects
                        |
                        v
                    Lowered MIR
                        |
                    Optimizations
                      /     \
                     v       v
                 Bytecode  Native IR
                     |        |
                     v        v
                    VM    Native backend

The first implementation will reuse the existing lexer and parser where practical. New compiler structures must not silently change interpreter semantics.

## Compiler package boundaries

- memingo.compiler.source: immutable source documents, spans, locations, and source maps.
- memingo.compiler.diagnostics: structured errors, warnings, labels, and terminal rendering.
- memingo.compiler.types (planned): primitive, collection, function, and inference types.
- memingo.compiler.hir (planned): typed high-level intermediate representation.
- memingo.compiler.mir (planned): lowered control-flow representation.
- memingo.compiler.analysis (planned): name resolution, type checking, ownership, and effect analysis.
- memingo.compiler.backends (planned): bytecode and native code generation.

## Source coordinate contract

Compiler spans use half-open ranges [start, end) and zero-based Python Unicode-code-point offsets. User-facing line and column numbers are one-based. A future UTF-8 native backend must translate coordinates at its boundary rather than mixing byte offsets with editor columns.

## Safety direction

Safe Memingo code must not require raw pointer operations. Ownership and borrowing checks will be introduced as compiler analyses, with explicit and auditable escape hatches reserved for low-level interoperability. Automatic memory management may be offered for selected managed types, but it must not weaken guarantees for values participating in low-level ownership rules.

## Compatibility policy

- Existing meme keywords such as vibe, ritual, spill, drop, when, nah, grind, and borrow remain part of the language identity.
- Existing interpreter behavior remains supported during compiler development.
- New static typing features will be introduced with clear inference rules.
- Breaking language changes require a documented migration path.

## Milestones

1. **Foundation:** source maps and structured diagnostics.
2. **Semantic model:** initial scopes, primitive/collection types, inference, and type diagnostics (in progress).
3. **Typed HIR:** lower existing AST nodes into a typed representation.
4. **Analysis:** type checking and safe ownership rules.
5. **Execution:** bytecode format and virtual machine.
6. **Native:** measured backend prototype and optimization pipeline.

No performance or safety superiority over Rust is claimed until reproducible benchmarks, conformance tests, and independent review support those claims.

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

The first implementation reuses the existing lexer and parser. The public Python API is `memingo.compiler.compile_source(source, source_id)`, and the CLI exposes `memingo analyze [files-or-directories]` to run parsing, static checks, and typed HIR lowering without executing the program. New compiler structures must not silently change interpreter semantics.

## Compiler package boundaries

- memingo.compiler.source: immutable source documents, spans, locations, and source maps.
- memingo.compiler.diagnostics: structured errors, warnings, labels, and terminal rendering.
- memingo.compiler.types: primitive, collection, function, and gradual inference types.
- memingo.compiler.hir: typed high-level intermediate representation and AST lowering.
- memingo.compiler.checker: local name resolution, expression typing, and static diagnostics.
- memingo.compiler.ownership / borrow: collection transfer, alias, and lexical reference checks.
- memingo.compiler.mir (planned): lowered control-flow representation.
- memingo.compiler.backends (planned): verified bytecode and native code generation.

## Current type inference

The current checker infers primitive and collection expression types, validates assignments and conditions, and checks known ritual call arity. Ritual parameters remain dynamic (`any`) until parameter annotations or call-site inference are designed.

Ritual return types are inferred conservatively:

- A ritual with no `drop` statement returns `ghost`.
- A ritual whose every control-flow path returns can infer a common return type.
- An `if` contributes a guaranteed return only when both branches return.
- A possible fallthrough path keeps the return type as `any`; the checker does not promise a type the runtime cannot guarantee.
- Incompatible return types widen to `any`.
- Dynamic built-ins and imported package calls remain `any` unless their signatures are declared.

This is an inference foundation, not yet complete function-signature inference or a replacement for runtime checks.

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
2. **Semantic model:** initial scopes, primitive/collection types, expression inference, and structured diagnostics implemented; ritual return inference is now conservative and path-aware.
3. **Typed HIR:** initial typed HIR and AST lowering implemented; continue filling semantic metadata and invariants.
4. **Analysis:** initial type, ownership, and lexical borrow checks implemented; parameter inference and complete lifetime analysis remain open.
5. **Execution:** verified bytecode format and virtual machine planned.
6. **Native:** measured backend prototype and optimization pipeline planned.

No performance or safety superiority over Rust is claimed until reproducible benchmarks, conformance tests, and independent review support those claims.

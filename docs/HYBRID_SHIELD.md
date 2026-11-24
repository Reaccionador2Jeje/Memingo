# Memingo Hybrid Shield

Hybrid Shield is enabled by default in interpreter executions and is being expanded
through the compiler pipeline.

## Runtime safeguards

- Execution-step budget, including loop iterations.
- Maximum nested Memingo ritual call depth.
- Maximum list and object item count.
- Maximum string length and integer bit width.
- Rejection of non-finite floating-point values at interpreter boundaries.

## Static ownership foundation

The compiler's `memingo analyze` command now includes a conservative ownership pass
for list and object values:

- A direct collection binding such as `vibe second = first` transfers ownership.
- Reading `first` after that transfer reports diagnostic `M2001`.
- Reinitializing the moved binding restores its usable state.
- Scalar values are not treated as owned heap collections.
- Branch analysis only marks a value definitely moved when both branches move it.
- A loop body is not assumed to execute, so moves inside it are not definite afterward.

Example:

```mgo
vibe first = [1, 2, 3]
vibe second = first
spill first # rejected by: memingo analyze
```

This is an initial static ownership model, not yet a complete Rust-style borrow
checker. Shared and mutable borrow lifetimes, mutation alias analysis, closure
capture rules, and ownership enforcement in every execution path remain future work.
The interpreter still uses Python-managed objects; static analysis does not change
Python's runtime memory model.

## Important boundaries

Hybrid Shield cannot guarantee prevention of physical hardware faults, operating
system failures, defects in native extensions, or arbitrary hostile code. It limits
language-level resource use and catches selected errors at the Memingo boundary.
Host-specific adapters can report and recover from some faults, but cannot make
hardware infallible.

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m memingo analyze examples
```

## Call-scoped borrow checking

The compiler now recognizes exclusive mutable access performed by the standard
collection mutators `push`, `append`, `set_value`, and `delete_key`.
Diagnostic `M2101` is emitted when another argument in the same call refers
to the same root collection as the mutating argument. This catches direct and
property/index-based aliases such as passing a collection as both the target
and the value being inserted.

This is deliberately a call-scoped alias check, not a complete reference
system. Memingo does not yet have explicit shared/mutable reference syntax or
lifetime inference. Sequential calls are separate borrow scopes; aliases hidden
inside dynamic values or external Python/native extensions cannot always be
proven statically.

## Runtime memory accounting

Each interpreter execution now has a configurable `max_memory_bytes` budget
(default: 64 MiB). After each executed statement, the shield estimates the
reachable size of values stored in the active environment chain. The estimator
walks Python dictionaries and common container types, tracks object identities
to avoid double-counting shared references and cycles, and raises a Shield
violation when the configured budget is exceeded. Byte strings are also subject
to the existing string-size boundary.

This is an approximate accounting guard for interpreter-managed values. It is
not process-RSS accounting, does not include all allocator overhead, native
extension allocations, thread stacks, or external process memory, and cannot
guarantee a hard operating-system memory ceiling. The Python runtime remains
responsible for physical allocation and reclamation.

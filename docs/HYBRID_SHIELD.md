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

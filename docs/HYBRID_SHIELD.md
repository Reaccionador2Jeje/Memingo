# Memingo Hybrid Shield

Hybrid Shield is enabled by default in every interpreter instance. Its first runtime
foundation protects against accidental resource exhaustion and oversized values.

## Current safeguards

- Execution-step budget, including loop iterations.
- Maximum nested Memingo ritual call depth.
- Maximum list and object item count.
- Maximum string length.
- Maximum integer bit width.
- Rejection of non-finite floating-point values.

The defaults are intentionally generous for ordinary scripts. Embedders can supply
a `ShieldLimits` instance to `Interpreter(shield_limits=...)` to tune them.

## Important boundaries

Hybrid Shield does not claim to prevent every memory bug or hardware failure.
Memingo currently runs on Python, so the host runtime still owns physical memory
management. These limits reduce runaway work and oversized allocations at the
language boundary; they are not a sandbox against hostile Python extensions,
operating-system faults, defective hardware, or arbitrary native code.

The next compiler stages are static ownership/borrowing analysis, typed memory
regions, and an explicit audited unsafe-capability model. Low-level access must
remain opt-in and narrowly scoped; it is not implemented by this runtime layer.

## Tests

```bash
python3 -m unittest tests.test_shield -v
python3 -m unittest discover -s tests -v
```

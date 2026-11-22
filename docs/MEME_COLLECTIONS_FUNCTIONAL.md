# Meme Collections & Functional Packages

These packages extend Memingo's existing collection and callback built-ins with a meme-first public API. They are implemented in `.mgo` and can be installed with MGOA.

| Package | Purpose | Main rituals |
| --- | --- | --- |
| `hoarding` | Collection cleanup and inspection | `compact`, `unique_lore`, `duplicates`, `frequency_of`, `partition_lobby`, `pluck_many` |
| `infiniteyap` | Iterable transformations | `enumerate_pairs`, `zip_pairs`, `chain_lists`, `windows`, `take_every`, `flatten_one` |
| `functionjuice` | Functional pipelines and callbacks | `identity`, `apply_twice`, `pipe2`, `compose2`, `tap`, `map_chain`, `filter_map`, `apply_if` |

## Example

```mgo
borrow "hoarding"
borrow "infiniteyap"
borrow "functionjuice"

spill duplicates(["lol", "bruh", "lol", "based"])
spill windows([1, 2, 3, 4, 5], 3)

ritual double(n) {
    drop n * 2
}

ritual add_one(n) {
    drop n + 1
}

spill pipe2(20, double, add_one)
spill map_chain([1, 2, 3], double, add_one)
```

## Semantics

- `compact` removes `ghost`, `cringe`, numeric zero and empty strings.
- `duplicates` returns each repeated value once, in the order it first becomes a duplicate.
- `frequency_of` counts strict-equality matches.
- `partition_lobby` calls the supplied predicate once per item and returns an object with `matched` and `rejected` lists.
- `zip_pairs` stops at the shorter input, like Python's `zip`.
- `windows` returns overlapping windows; invalid non-positive sizes return an empty list.
- `take_every` selects indices 0, step, 2*step, and so on; invalid non-positive steps return an empty list.
- `pipe2(value, first, second)` evaluates `second(first(value))`.
- `compose2(value, outer, inner)` evaluates `outer(inner(value))`.
- `tap` invokes an observer and returns the original value.
- `filter_map` filters first, then transforms the selected values.

Each package includes `self_test()`. The Python test suite parses each source package and runs those self-tests through the Memingo interpreter.

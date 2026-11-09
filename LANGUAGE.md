# Memingo Language Reference

## Values

Memingo supports numbers, strings, booleans, `ghost`, lists, and objects.

```mgo
vibe count = 12
vibe text = "hello"
vibe active = based
vibe missing = ghost
vibe values = [1, 2, 3]
vibe profile = {name: "Ana", role: "builder"}
```

## Statements

- `vibe` declares a variable
- `ritual` declares a function
- `spill` prints a value
- `drop` returns a function value
- `when / nah` creates conditions
- `grind` repeats while a condition is true
- `borrow` loads an installed package

## Objects and access

```mgo
vibe profile = {name: "Ana", role: "builder"}
set_value(profile, "status", "based")
spill profile.name
spill profile["status"]
```

Lists and objects may span multiple lines. Trailing commas are allowed.

```mgo
vibe world = {
    name: "MemeCraft",
    day: based
}
vibe materials = [
    {name: "grass", solid: based},
    {name: "stone", solid: based},
]
```

## Functions

```mgo
ritual factorial(n) {
    when n <= 1 {
        drop 1
    }
    drop n * factorial(n - 1)
}

spill factorial(5)
```

`drop` returns immediately from the enclosing ritual. A `drop` at the top level stops the program and returns its value.

## Operators

Arithmetic: `+ - * / %`
Comparison: `< > <= >=`
Equality: `== !=`
Logic: `&& || !`

`+` also concatenates strings.

## JSON and environment

```mgo
vibe config = json_parse(env("CONFIG_JSON", "{}"))
spill json_stringify(config)
```

## HTTP

```mgo
vibe result = http_get("https://example.com/api/status")
spill result
```

```mgo
vibe created = http_post("https://example.com/api/items", {name: "meme"})
spill created
```

## Standard library

### Values and collections

- `headcount(value)` counts lists, objects and strings
- `whatkind(value)` reports the Memingo type: `whole`, `caption`, `party`, `based-or-cringe`, or `ghost`
- `keys(object)` lists object keys
- `values(object)` lists object values
- `push(list, value)` appends a value and returns the value
- `append(list, value)` appends a value and returns the new length
- `set_value(container, key, value)` assigns a list or object member
- `delete_key(object, key)` removes an object member
- `sort(list, descending?)` returns a sorted copy
- `reverse(list)` returns a reversed copy
- `unique(list)` removes duplicate values while keeping order
- `sum(list)` adds a list of numbers
- `min(values)` and `max(values)` accept a list or separate numbers
- `slice(value, start, end?)` slices a list or string

### Text

- `upper(text)`, `lower(text)` and `trim(text)`
- `split(text, separator?)` returns a list of parts
- `join(list, separator?)` joins values into text
- `replace(text, old, new)`
- `contains(text, value)` also works on lists and object keys
- `starts_with(text, prefix)` and `ends_with(text, suffix)`
- `repeat(text, count)` repeats text `count` times
- `lines(text)` splits text into a list of lines
- `meme_case(text)` alternates uppercase and lowercase letters for maximum meme energy
- `shuffle(list)` returns a shuffled copy of a list
- `uuid()` returns a random UUID string

### Numbers

- `abs(value)`, `floor(value)`, `ceil(value)` and `round(value)`
- `clamp(value, low, high)` keeps a number inside a range
- `parse_int(text)` and `parse_float(text)` convert text to numbers
- `random()` returns a decimal between 0 and 1
- `random_int(low, high)` returns an integer in the inclusive range
- `range(end)`, `range(start, end)` and `range(start, end, step)`

### Functions

- `map(list, function)` applies a function to every item
- `filter(list, function)` keeps items where the function returns a truthy value
- `reduce(list, function, initial?)` combines items into one value

```mgo
ritual double(n) { drop n * 2 }
ritual even(n) { drop n % 2 == 0 }
ritual combine(a, b) { drop a + b }

spill map([1, 2, 3], double)
spill filter([1, 2, 3, 4], even)
spill reduce([1, 2, 3, 4], combine, 0)
```

### Data, time and network

- `json_parse(text)` parses JSON
- `json_stringify(value)` serializes JSON
- `env(name, default)` reads an environment variable
- `now()` returns the current Unix timestamp
- `sleep(seconds)` pauses execution
- `http_get(url)` reads text or JSON
- `http_post(url, object)` sends JSON and reads text or JSON

### Files

File helpers are restricted to the project directory and reject absolute paths or `..` escapes.

- `read_file(path)` reads a UTF-8 text file
- `write_file(path, text)` writes a UTF-8 text file, creating parent directories
- `file_exists(path)` returns `based` or `cringe`
- `list_files(path)` returns a sorted list of directory entries

```mgo
write_file("notes/hello.txt", "hola")
spill read_file("notes/hello.txt")
spill file_exists("notes/hello.txt")
spill list_files("notes")
```

Errors raised inside a built-in are reported as Memingo runtime errors with the function name.

## Packages

```mgo
borrow "hello-memes"
greet("Team")
```

`borrow` loads the installed package entry point from `.memingo/packages/<name>`. Package names may contain letters, digits, dots, dashes, and underscores.


## Runtime diagnostics

Runtime errors include the source line and column of the statement that caused the failure when that location is available. Errors inside a ritual preserve the innermost failing statement location.

```mgo
vibe answer = 42
spill missing_value
```

The CLI reports the undefined variable together with its source location, making larger projects easier to debug.


## Modules and imports

Use `import` to load a project module. Module files are resolved relative to the project directory. A module can be a single `.mgo` file or a folder containing `main.mgo`.

```mgo
import "math"
spill math.sqrt(81)

import "helpers/text" as text
spill text.title_case("hello memingo")
```

Imported project modules execute once per interpreter and expose their top-level variables and rituals through a module namespace. Imports cannot use absolute paths or escape the project directory. Circular imports are rejected with a runtime error.

The built-in `math` module currently exposes `sqrt`, `pow`, `sin`, `cos`, `tan`, `pi`, `e`, `floor` and `ceil`.

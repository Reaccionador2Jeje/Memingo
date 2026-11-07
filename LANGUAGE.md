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
- `borrow` loads an installed approved package

## Objects and access

```mgo
vibe profile = {name: "Ana", role: "builder"}
set_value(profile, "status", "based")
spill profile.name
spill profile["status"]
```

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

- `len(value)` is not built-in; use `headcount(value)`
- `headcount(value)` counts lists and objects
- `whatkind(value)` reports the Memingo type name
- `json_parse(text)` parses JSON
- `json_stringify(value)` serializes JSON
- `env(name, default)` reads an environment variable
- `range(end)` creates a numeric list
- `keys(object)` lists object keys
- `push(list, value)` appends a value and returns the value
- `append(list, value)` appends a value and returns the new length
- `set_value(container, key, value)` assigns a list or object member
- `delete_key(object, key)` removes an object member
- `random()` returns a decimal between 0 and 1
- `random_int(low, high)` returns an integer in the inclusive range
- `http_get(url)` reads text or JSON
- `http_post(url, object)` sends JSON and reads text or JSON

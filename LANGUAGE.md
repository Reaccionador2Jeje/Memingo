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

## Native HTTP servers

Memingo programs can define HTTP APIs directly in `.mgo`:

```mgo
vibe app = api()

ritual greet(request) {
    drop {message: "Hello " + request.params.name}
}

api_get(app, "/hello/<name>", greet)
api_listen(app)
```

- `api()` creates an application.
- `api_get(app, path, ritual)`, `api_post(...)`, `api_put(...)`, `api_patch(...)`, and `api_delete(...)` register routes.
- `api_route(app, methods, path, ritual)` registers custom methods.
- `request_json(request)` parses a request's JSON body.
- `request_form(request)` parses URL-encoded and multipart form fields.
- `request_files(request)` returns uploaded file records, including binary data and metadata.
- `save_upload(file, directory?)` stores an uploaded file safely inside the project using a generated filename.
- `response_json(data, status?, headers?)`, `response_text(text, status?, headers?)`, and `response_html(html, status?, headers?)` create explicit HTTP responses.
- `response_redirect(location, status?)` creates a redirect; `response_error(status, message)` creates a JSON error response.
- `api_use(app, ritual)` registers middleware with `(request, next)` parameters.
- `response_header(response, name, value)`, `response_status(response, status)`, and `response_body(response, body)` modify a response returned by `next()`.
- `api_listen(app, host?, port?)` starts listening. The default host is `127.0.0.1` and port is `8000`.

The route ritual receives a request object with `method`, `path`, `query`, `params`, `headers`, `body`, `form`, and `files`. Request bodies are limited to 10 MB and individual uploaded files to 5 MB. Upload storage stays inside the project directory. See the upload example at `examples/native_uploads.mgo`. Return an object or list for JSON, a string for text, or `ghost` for an empty 204 response. Middleware runs in registration order; call `next()` to continue, or return an object to stop the chain early. `next()` returns a response that can be changed with the response helpers. Run a server with `memingo api server.mgo`. See [docs/SERVER.md](docs/SERVER.md).

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

## Built-in AI training

Memingo includes a dependency-free CPU engine for small dense neural networks. It is called directly from `.mgo` scripts; Python is not required by the AI API.

```mgo
vibe model = ai.create({
    name: "MyModel",
    layers: [2, 4, 1],
    activation: "sigmoid"
})

vibe data = ai.dataset(
    [[0, 0], [0, 1], [1, 0], [1, 1]],
    [[0], [1], [1], [0]]
)

vibe report = ai.train(model, data, {
    epochs: 1000,
    learning_rate: 0.3,
    batch_size: 2,
    shuffle: based
})

spill report.loss
spill ai.predict(model, [0, 1])
spill ai.evaluate(model, data)

ai.save(model, "models/my-model.mgoai")
vibe restored = ai.load("models/my-model.mgoai")
spill ai.predict(restored, [0, 1])
```

Available operations:

- `ai.create(config)` creates a dense neural network. Configure `layers` and an activation (`relu`, `sigmoid`, or `tanh`).
- `ai.dataset(inputs, outputs)` validates paired numeric training examples.
- `ai.train(model, dataset, options)` trains with backpropagation and returns epoch count, final mean squared error, and sample count.
- `ai.predict(model, inputs)` returns the model output for one input row.
- `ai.evaluate(model, dataset)` returns mean squared error and sample count.
- `ai.save(model, path)` saves a versioned `.mgoai` model inside the project directory.
- `ai.load(path)` loads a saved model from inside the project directory.

The built-in engine is CPU-based and intended for learning and small models. Training limits epochs to 100,000 and network size to 8,192 total neurons. It does not currently provide GPU acceleration, transformer/LLM training, image pipelines, or automatic dataset downloads. Python and external ML frameworks remain optional integrations.


## Meme-first standard packages

Memingo's standard package collection uses meme-inspired names while keeping real, documented behavior. Existing package names remain available for backward compatibility.

| Package | Purpose | Example operations |
| --- | --- | --- |
| `brainrot` | Mathematics | `sqrt_irl`, `powerlevel`, `factorial_arc`, `fibonacci_lore`, `is_prime_sus` |
| `yapstats` | Statistics | `average_yap`, `median_lore`, `variance_arc`, `stddev_finalboss`, `percentile_lore` |
| `luckymeme` | Random utilities for games and simulations | `pick_bro`, `sample_lobby`, `coinflip_irl`, `roll_dice`, `roll_many` |
| `whenisbro` | Time and durations | `timestamp_irl`, `days_between`, `weekday_lore`, `format_duration` |

Install these packages through the Memingo package manager, then load them with `borrow`:

```mgo
borrow "brainrot"
borrow "yapstats"
borrow "luckymeme"
borrow "whenisbro"

spill sqrt_irl(81)
```

Each package exposes a `self_test()` ritual for a quick behavior check. Meme-inspired names are the public API; implementations remain deterministic where appropriate, validated, and suitable for normal software projects.

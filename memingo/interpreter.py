import json
import math
import os
import random
import re
import time
import urllib.request
import uuid
from pathlib import Path

from .http_api import MemingoAPIServer
from .parser import (
    Assign, Binary, Borrow, Call, Function, Get, If, ImportModule, Let, ListExpression,
    Literal, MapExpression, Program, Return, Say, Unary, Variable, While, parse,
)


class RuntimeErrorMemingo(Exception):
    """Runtime error with optional source location."""

    def __init__(self, message, line=None, column=None):
        super().__init__(message)
        self.line = line
        self.column = column

    def __str__(self):
        message = super().__str__()
        if self.line is None:
            return message
        if self.column is None:
            return f"{message} at line {self.line}"
        return f"{message} at line {self.line}, column {self.column}"


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


_MISSING = object()


class Environment:
    def __init__(self, parent=None):
        self.values = {}
        self.parent = parent

    def define(self, name, value):
        self.values[name] = value

    def get(self, name):
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise RuntimeErrorMemingo(f"Undefined variable '{name}'")

    def assign(self, name, value):
        if name in self.values:
            self.values[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise RuntimeErrorMemingo(f"Undefined variable '{name}'")


class MemingoFunction:
    def __init__(self, declaration, closure):
        self.declaration = declaration
        self.closure = closure

    def call(self, interpreter, arguments):
        if len(arguments) != len(self.declaration.params):
            raise RuntimeErrorMemingo(
                f"Function '{self.declaration.name}' expects {len(self.declaration.params)} arguments, got {len(arguments)}"
            )
        environment = Environment(self.closure)
        for name, value in zip(self.declaration.params, arguments):
            environment.define(name, value)
        try:
            interpreter.execute_block(self.declaration.body, environment)
        except ReturnSignal as signal:
            return signal.value
        return None


class Interpreter:
    def __init__(self, project_directory="."):
        self.project_directory = Path(project_directory).resolve()
        self.output = []
        self.debug_trace = None
        self.module_cache = {}
        self.loading_modules = set()
        env_path = self.project_directory / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))
        self.global_environment = Environment()
        self.global_environment.define("http_server", lambda: MemingoAPIServer(self).api())
        self.global_environment.define("math", {
            "sqrt": math.sqrt, "pow": pow, "sin": math.sin, "cos": math.cos,
            "tan": math.tan, "pi": math.pi, "e": math.e,
            "floor": math.floor, "ceil": math.ceil,
        })
        self.global_environment.define("headcount", lambda value: len(value))
        self.global_environment.define("whatkind", self._whatkind)
        self.global_environment.define("json_parse", lambda text: json.loads(text))
        self.global_environment.define("json_stringify", lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":")))
        self.global_environment.define("env", lambda name, default=None: os.environ.get(name, default))
        self.global_environment.define("random", random.random)
        self.global_environment.define("random_int", lambda low, high: random.randint(low, high))
        self.global_environment.define("shuffle", self._shuffle)
        self.global_environment.define("uuid", lambda: str(uuid.uuid4()))
        self.global_environment.define("range", self._range)
        self.global_environment.define("keys", lambda value: list(value.keys()) if isinstance(value, dict) else [])
        self.global_environment.define("values", self._values)
        self.global_environment.define("push", lambda items, value: items.append(value) or value if isinstance(items, list) else None)
        self.global_environment.define("append", lambda items, value: items.append(value) or len(items) if isinstance(items, list) else None)
        self.global_environment.define("set_value", lambda container, key, value: container.__setitem__(key, value) or value if isinstance(container, (dict, list)) else None)
        self.global_environment.define("delete_key", lambda container, key: container.pop(key, None) if isinstance(container, dict) else None)
        self.global_environment.define("upper", self._upper)
        self.global_environment.define("lower", self._lower)
        self.global_environment.define("trim", self._trim)
        self.global_environment.define("split", self._split)
        self.global_environment.define("join", self._join)
        self.global_environment.define("replace", self._replace)
        self.global_environment.define("contains", self._contains)
        self.global_environment.define("starts_with", self._starts_with)
        self.global_environment.define("ends_with", self._ends_with)
        self.global_environment.define("meme_case", self._meme_case)
        self.global_environment.define("slice", self._slice)
        self.global_environment.define("repeat", self._repeat)
        self.global_environment.define("lines", self._lines)
        self.global_environment.define("sort", self._sort)
        self.global_environment.define("reverse", self._reverse)
        self.global_environment.define("unique", self._unique)
        self.global_environment.define("sum", self._sum)
        self.global_environment.define("min", self._min)
        self.global_environment.define("max", self._max)
        self.global_environment.define("abs", self._abs)
        self.global_environment.define("floor", self._floor)
        self.global_environment.define("ceil", self._ceil)
        self.global_environment.define("round", self._round)
        self.global_environment.define("clamp", self._clamp)
        self.global_environment.define("parse_int", self._parse_int)
        self.global_environment.define("parse_float", self._parse_float)
        self.global_environment.define("map", self._map)
        self.global_environment.define("filter", self._filter)
        self.global_environment.define("reduce", self._reduce)
        self.global_environment.define("now", time.time)
        self.global_environment.define("sleep", self._sleep)
        self.global_environment.define("http_get", self._http_get)
        self.global_environment.define("http_post", self._http_post)
        self.global_environment.define("read_file", self._read_file)
        self.global_environment.define("write_file", self._write_file)
        self.global_environment.define("file_exists", self._file_exists)
        self.global_environment.define("list_files", self._list_files)

    def run(self, program):
        try:
            return self.execute_block(program.statements, self.global_environment)
        except ReturnSignal as signal:
            return signal.value

    def execute_block(self, statements, environment):
        previous = getattr(self, "environment", None)
        self.environment = environment
        try:
            result = None
            for statement in statements:
                try:
                    result = self.execute(statement)
                except RuntimeErrorMemingo as error:
                    # Keep the innermost source location while errors bubble up.
                    if error.line is None:
                        error.line = getattr(statement, "line", None)
                        error.column = getattr(statement, "column", None)
                    raise
            return result
        finally:
            self.environment = previous

    def execute(self, node):
        if self.debug_trace is not None:
            if len(self.debug_trace) >= 10000:
                raise RuntimeErrorMemingo("Debug trace limit reached (10,000 steps). Check for an endless loop.")
            self.debug_trace.append({
                "line": getattr(node, "line", None),
                "type": type(node).__name__,
                "variables": self._debug_variables(),
            })
        if isinstance(node, Let):
            value = self.evaluate(node.value)
            self.environment.define(node.name, value)
            return value
        if isinstance(node, Assign):
            value = self.evaluate(node.value)
            self.environment.assign(node.name, value)
            return value
        if isinstance(node, Say):
            value = self.evaluate(node.value)
            text = self._display(value)
            self.output.append(text)
            return value
        if isinstance(node, Return):
            raise ReturnSignal(self.evaluate(node.value))
        if isinstance(node, ImportModule):
            module_path = self.evaluate(node.path)
            if not isinstance(module_path, str) or not module_path:
                raise RuntimeErrorMemingo("import requires a non-empty quoted path")
            if module_path == "math":
                self.environment.define(node.alias, self.global_environment.get("math"))
                return None
            requested = Path(module_path)
            if requested.is_absolute() or ".." in requested.parts:
                raise RuntimeErrorMemingo("Module imports must stay inside the project directory")
            candidates = []
            if requested.suffix:
                candidates.append((self.project_directory / requested).resolve())
            else:
                candidates.append((self.project_directory / requested.with_suffix(".mgo")).resolve())
                candidates.append((self.project_directory / requested / "main.mgo").resolve())
            module_file = next((candidate for candidate in candidates
                                if candidate.is_file()
                                and self.project_directory in candidate.parents), None)
            if module_file is None:
                raise RuntimeErrorMemingo(f"Module '{module_path}' was not found in the project")
            if module_file in self.loading_modules:
                raise RuntimeErrorMemingo(f"Circular module import detected: '{module_path}'")
            if module_file not in self.module_cache:
                self.loading_modules.add(module_file)
                module_environment = Environment(self.global_environment)
                try:
                    try:
                        module_source = module_file.read_text(encoding="utf-8")
                    except (OSError, UnicodeError) as error:
                        raise RuntimeErrorMemingo(f"Could not read module '{module_path}': {error}") from error
                    module_program = parse(module_source)
                    self.execute_block(module_program.statements, module_environment)
                    self.module_cache[module_file] = {
                        name: value for name, value in module_environment.values.items()
                    }
                finally:
                    self.loading_modules.discard(module_file)
            self.environment.define(node.alias, self.module_cache[module_file])
            return None
        if isinstance(node, Borrow):
            package_name = self.evaluate(node.package)
            if not isinstance(package_name, str):
                raise RuntimeErrorMemingo("borrow requires a package name")
            if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", package_name):
                raise RuntimeErrorMemingo(f"Invalid package name '{package_name}'")
            package_dir = self.project_directory / ".memingo" / "packages" / package_name
            lock_path = self.project_directory / "memingo.lock.json"
            lock = {}
            if lock_path.exists():
                try:
                    lock = json.loads(lock_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError, UnicodeError) as error:
                    raise RuntimeErrorMemingo(f"Could not read package lockfile: {error}") from error
            if not isinstance(lock, dict):
                raise RuntimeErrorMemingo("Package lockfile is invalid")
            dependencies = lock.get("dependencies", {})
            if not isinstance(dependencies, dict):
                raise RuntimeErrorMemingo("Package lockfile is invalid")
            record = dependencies.get(package_name)
            entry = record.get("entry", "main.mgo") if isinstance(record, dict) else "main.mgo"
            if not isinstance(entry, str) or not entry:
                raise RuntimeErrorMemingo(f"Borrowed package '{package_name}' has an invalid entry point")
            package_root = package_dir.resolve()
            entry_path = (package_dir / entry).resolve()
            if entry_path != package_root and package_root not in entry_path.parents:
                raise RuntimeErrorMemingo(f"Borrowed package '{package_name}' has an unsafe entry point")
            if not entry_path.exists():
                raise RuntimeErrorMemingo(f"Borrowed package '{package_name}' is not installed")
            module_environment = Environment(self.environment)
            previous = self.environment
            self.environment = module_environment
            try:
                try:
                    module_source = entry_path.read_text(encoding="utf-8")
                except UnicodeError as error:
                    raise RuntimeErrorMemingo(
                        f"Borrowed package '{package_name}' is not valid UTF-8"
                    ) from error
                module_program = parse(module_source)
                self.execute_block(module_program.statements, module_environment)
            finally:
                self.environment = previous
            for name, value in module_environment.values.items():
                self.environment.define(name, value)
            return None
        if isinstance(node, Function):
            function = MemingoFunction(node, self.environment)
            self.environment.define(node.name, function)
            return function
        if isinstance(node, If):
            if self.evaluate(node.condition):
                return self.execute_block(node.then_branch, Environment(self.environment))
            return self.execute_block(node.else_branch, Environment(self.environment)) if node.else_branch else None
        if isinstance(node, While):
            result = None
            iterations = 0
            while self.evaluate(node.condition):
                iterations += 1
                if self.debug_trace is not None and iterations > 10000:
                    raise RuntimeErrorMemingo("Debug loop limit reached (10,000 iterations). Check the loop condition.")
                result = self.execute_block(node.body, Environment(self.environment))
            return result
        return self.evaluate(node)

    def _debug_variables(self):
        visible = {}
        environment = getattr(self, "environment", self.global_environment)
        chain = []
        while environment is not None:
            chain.append(environment)
            environment = environment.parent
        for scope in reversed(chain):
            for name, value in scope.values.items():
                try:
                    rendered = self._display(value)
                except Exception:
                    rendered = f"<{type(value).__name__}>"
                if len(rendered) > 160:
                    rendered = rendered[:157] + "..."
                visible[name] = rendered
        return visible

    def evaluate(self, node):
        if isinstance(node, Literal):
            return node.value
        if isinstance(node, Variable):
            return self.environment.get(node.name)
        if isinstance(node, ListExpression):
            return [self.evaluate(item) for item in node.items]
        if isinstance(node, MapExpression):
            return {key: self.evaluate(value) for key, value in node.entries}
        if isinstance(node, Get):
            target = self.evaluate(node.target)
            key = self.evaluate(node.key)
            try:
                return target[key]
            except (KeyError, IndexError, TypeError):
                raise RuntimeErrorMemingo(f"Cannot access {key!r} on value")
        if isinstance(node, Unary):
            value = self.evaluate(node.operand)
            if node.operator == "!":
                return not bool(value)
            if node.operator == "-":
                if not isinstance(value, (int, float)):
                    raise RuntimeErrorMemingo("Unary '-' requires a number")
                return -value
        if isinstance(node, Binary):
            left = self.evaluate(node.left)
            if node.operator == "&&":
                return self.evaluate(node.right) if bool(left) else False
            if node.operator == "||":
                return left if bool(left) else self.evaluate(node.right)
            right = self.evaluate(node.right)
            return self._binary(node.operator, left, right)
        if isinstance(node, Call):
            callee = self.evaluate(node.callee)
            arguments = [self.evaluate(argument) for argument in node.arguments]
            if isinstance(callee, MemingoFunction):
                return callee.call(self, arguments)
            if callable(callee):
                try:
                    return callee(*arguments)
                except RuntimeErrorMemingo:
                    raise
                except Exception as exception:
                    name = node.callee.name if isinstance(node.callee, Variable) else getattr(callee, "__name__", "built-in")
                    raise RuntimeErrorMemingo(f"{name}() failed: {exception}") from exception
            raise RuntimeErrorMemingo("Attempted to call a non-function value")
        raise RuntimeErrorMemingo(f"Unknown expression: {type(node).__name__}")

    def _binary(self, operator, left, right):
        if operator == "+":
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left + right
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            raise RuntimeErrorMemingo("Operator '+' requires numbers or strings")
        if operator == "-":
            return self._number_operation(operator, left, right, lambda a, b: a - b)
        if operator == "*":
            return self._number_operation(operator, left, right, lambda a, b: a * b)
        if operator == "/":
            if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                raise RuntimeErrorMemingo("Operator '/' requires numbers")
            if right == 0:
                raise RuntimeErrorMemingo("Division by zero")
            return left / right
        if operator == "%":
            return self._number_operation(operator, left, right, lambda a, b: a % b)
        if operator == "==":
            return left == right
        if operator == "!=":
            return left != right
        if operator in ("<", ">", "<=", ">="):
            try:
                return {"<": left < right, ">": left > right, "<=": left <= right, ">=": left >= right}[operator]
            except TypeError:
                raise RuntimeErrorMemingo(f"Operator '{operator}' requires comparable values")
        raise RuntimeErrorMemingo(f"Unknown operator '{operator}'")

    def _http_get(self, url):
        request = urllib.request.Request(str(url), headers={"User-Agent": "Memingo/0.2"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8")) if response.headers.get_content_type() == "application/json" else response.read().decode("utf-8")

    def _http_post(self, url, payload=None):
        body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(str(url), data=body, headers={"Content-Type": "application/json", "User-Agent": "Memingo/0.2"}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read().decode("utf-8")
            return json.loads(data) if response.headers.get_content_type() == "application/json" else data

    def _project_path(self, function, path):
        if not isinstance(path, str) or not path.strip():
            raise RuntimeErrorMemingo(f"{function}() requires a non-empty relative path")
        candidate = Path(path)
        if candidate.is_absolute():
            raise RuntimeErrorMemingo(f"{function}() requires a path inside the project")
        resolved = (self.project_directory / candidate).resolve()
        if resolved != self.project_directory and self.project_directory not in resolved.parents:
            raise RuntimeErrorMemingo(f"{function}() cannot leave the project directory")
        return resolved

    def _read_file(self, path):
        target = self._project_path("read_file", path)
        if not target.is_file():
            raise RuntimeErrorMemingo(f"read_file() could not find '{path}'")
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeError as exception:
            raise RuntimeErrorMemingo(f"read_file() requires a UTF-8 file: {exception}") from exception

    def _write_file(self, path, contents):
        target = self._project_path("write_file", path)
        if not isinstance(contents, str):
            raise RuntimeErrorMemingo("write_file() requires string contents")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents, encoding="utf-8")
        except OSError as exception:
            raise RuntimeErrorMemingo(f"write_file() failed: {exception}") from exception
        return len(contents)

    def _file_exists(self, path):
        return self._project_path("file_exists", path).exists()

    def _list_files(self, path="."):
        target = self._project_path("list_files", path)
        if not target.is_dir():
            raise RuntimeErrorMemingo(f"list_files() could not find directory '{path}'")
        return sorted(entry.name for entry in target.iterdir())

    def _string_argument(self, function, value, label="value"):
        if not isinstance(value, str):
            raise RuntimeErrorMemingo(f"{function}() requires a string {label}")
        return value

    def _number_argument(self, function, value):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise RuntimeErrorMemingo(f"{function}() requires a number")
        return value

    def _list_argument(self, function, value):
        if not isinstance(value, list):
            raise RuntimeErrorMemingo(f"{function}() requires a list")
        return value

    def _range(self, *arguments):
        if not 1 <= len(arguments) <= 3:
            raise RuntimeErrorMemingo("range() expects 1 to 3 whole numbers")
        if any(not isinstance(value, int) or isinstance(value, bool) for value in arguments):
            raise RuntimeErrorMemingo("range() expects whole numbers")
        try:
            return list(range(*arguments))
        except ValueError as exception:
            raise RuntimeErrorMemingo(f"range() failed: {exception}") from exception

    def _values(self, container):
        if not isinstance(container, dict):
            return []
        return list(container.values())

    def _upper(self, text):
        return self._string_argument("upper", text).upper()

    def _lower(self, text):
        return self._string_argument("lower", text).lower()

    def _trim(self, text):
        return self._string_argument("trim", text).strip()

    def _split(self, text, separator=None):
        text = self._string_argument("split", text)
        if separator is None:
            return text.split()
        separator = self._string_argument("split", separator, "separator")
        if separator == "":
            raise RuntimeErrorMemingo("split() separator cannot be empty")
        return text.split(separator)

    def _join(self, items, separator=""):
        items = self._list_argument("join", items)
        separator = self._string_argument("join", separator, "separator")
        return separator.join(self._display(item) for item in items)

    def _replace(self, text, old, new):
        text = self._string_argument("replace", text)
        old = self._string_argument("replace", old, "old text")
        new = self._string_argument("replace", new, "new text")
        return text.replace(old, new)

    def _contains(self, container, value):
        if not isinstance(container, (str, list, dict)):
            raise RuntimeErrorMemingo("contains() requires a string, list, or object")
        try:
            return value in container
        except TypeError as exception:
            raise RuntimeErrorMemingo(f"contains() failed: {exception}") from exception

    def _starts_with(self, text, prefix):
        text = self._string_argument("starts_with", text)
        prefix = self._string_argument("starts_with", prefix, "prefix")
        return text.startswith(prefix)

    def _ends_with(self, text, suffix):
        text = self._string_argument("ends_with", text)
        suffix = self._string_argument("ends_with", suffix, "suffix")
        return text.endswith(suffix)

    def _meme_case(self, text):
        text = self._string_argument("meme_case", text)
        letters = iter(text)
        result = []
        capital = True
        for character in letters:
            if character.isalpha():
                result.append(character.upper() if capital else character.lower())
            else:
                result.append(character)
            capital = not capital
        return "".join(result)

    def _shuffle(self, items):
        shuffled = list(self._list_argument("shuffle", items))
        random.shuffle(shuffled)
        return shuffled

    def _slice(self, value, start, end=None):
        if not isinstance(value, (str, list)):
            raise RuntimeErrorMemingo("slice() requires a string or list")
        if not isinstance(start, int) or isinstance(start, bool):
            raise RuntimeErrorMemingo("slice() start must be a whole number")
        if end is not None and (not isinstance(end, int) or isinstance(end, bool)):
            raise RuntimeErrorMemingo("slice() end must be a whole number")
        return value[start:end]

    def _repeat(self, text, count):
        text = self._string_argument("repeat", text)
        if not isinstance(count, int) or isinstance(count, bool):
            raise RuntimeErrorMemingo("repeat() count must be a whole number")
        if count < 0:
            raise RuntimeErrorMemingo("repeat() count must be zero or greater")
        return text * count

    def _lines(self, text):
        return self._string_argument("lines", text).splitlines()

    def _sort(self, items, descending=False):
        items = self._list_argument("sort", items)
        if not isinstance(descending, bool):
            raise RuntimeErrorMemingo("sort() descending must be based or cringe")
        try:
            return sorted(items, reverse=descending)
        except TypeError as exception:
            raise RuntimeErrorMemingo(f"sort() failed: {exception}") from exception

    def _reverse(self, items):
        if isinstance(items, str):
            return items[::-1]
        return list(reversed(self._list_argument("reverse", items)))

    def _unique(self, items):
        items = self._list_argument("unique", items)
        result = []
        for item in items:
            if item not in result:
                result.append(item)
        return result

    def _sum(self, items):
        items = self._list_argument("sum", items)
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in items):
            raise RuntimeErrorMemingo("sum() requires a list of numbers")
        return sum(items)

    def _numeric_arguments(self, function, values):
        if len(values) == 1 and isinstance(values[0], list):
            candidates = values[0]
        else:
            candidates = list(values)
        if not candidates:
            raise RuntimeErrorMemingo(f"{function}() requires at least one number")
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in candidates):
            raise RuntimeErrorMemingo(f"{function}() requires numbers")
        return candidates

    def _min(self, *values):
        return min(self._numeric_arguments("min", values))

    def _max(self, *values):
        return max(self._numeric_arguments("max", values))

    def _abs(self, value):
        return abs(self._number_argument("abs", value))

    def _floor(self, value):
        return math.floor(self._number_argument("floor", value))

    def _ceil(self, value):
        return math.ceil(self._number_argument("ceil", value))

    def _round(self, value):
        return round(self._number_argument("round", value))

    def _clamp(self, value, low, high):
        value = self._number_argument("clamp", value)
        low = self._number_argument("clamp", low)
        high = self._number_argument("clamp", high)
        if low > high:
            raise RuntimeErrorMemingo("clamp() requires low <= high")
        return max(low, min(value, high))

    def _parse_int(self, text):
        text = self._string_argument("parse_int", text)
        try:
            return int(text.strip())
        except ValueError as exception:
            raise RuntimeErrorMemingo(f"parse_int() failed: {exception}") from exception

    def _parse_float(self, text):
        text = self._string_argument("parse_float", text)
        try:
            return float(text.strip())
        except ValueError as exception:
            raise RuntimeErrorMemingo(f"parse_float() failed: {exception}") from exception

    def _invoke(self, function, arguments, label):
        if isinstance(function, MemingoFunction):
            return function.call(self, arguments)
        if callable(function):
            try:
                return function(*arguments)
            except RuntimeErrorMemingo:
                raise
            except Exception as exception:
                raise RuntimeErrorMemingo(f"{label}() failed: {exception}") from exception
        raise RuntimeErrorMemingo(f"{label}() requires a function")

    def _map(self, items, function):
        items = self._list_argument("map", items)
        return [self._invoke(function, [item], "map") for item in items]

    def _filter(self, items, function):
        items = self._list_argument("filter", items)
        return [item for item in items if bool(self._invoke(function, [item], "filter"))]

    def _reduce(self, items, function, initial=_MISSING):
        items = self._list_argument("reduce", items)
        if not callable(function) and not isinstance(function, MemingoFunction):
            raise RuntimeErrorMemingo("reduce() requires a function")
        if initial is _MISSING:
            if not items:
                raise RuntimeErrorMemingo("reduce() requires an initial value for an empty list")
            accumulator = items[0]
            remaining = items[1:]
        else:
            accumulator = initial
            remaining = items
        for item in remaining:
            accumulator = self._invoke(function, [accumulator, item], "reduce")
        return accumulator

    def _sleep(self, seconds):
        seconds = self._number_argument("sleep", seconds)
        if seconds < 0:
            raise RuntimeErrorMemingo("sleep() requires a non-negative number")
        time.sleep(seconds)
        return None

    def _whatkind(self, value):
        if value is None:
            return "ghost"
        if isinstance(value, bool):
            return "based-or-cringe"
        if isinstance(value, (int, float)):
            return "whole"
        if isinstance(value, str):
            return "caption"
        if isinstance(value, (list, dict)):
            return "party"
        return type(value).__name__

    def _number_operation(self, operator, left, right, operation):
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            raise RuntimeErrorMemingo(f"Operator '{operator}' requires numbers")
        return operation(left, right)

    def _display(self, value):
        if value is None:
            return "ghost"
        if value is True:
            return "based"
        if value is False:
            return "cringe"
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)


def execute(source, capture_output=True, project_directory="."):
    interpreter = Interpreter(project_directory=project_directory)
    interpreter.run(parse(source))
    return interpreter.output

import json
import math
import os
import random
import re
import time
import urllib.request
import uuid
from pathlib import Path

from .parser import (
    Assign, Binary, Borrow, Call, Function, Get, If, Let, ListExpression,
    Literal, MapExpression, Program, Return, Say, Unary, Variable, While, parse,
)


class RuntimeErrorMemingo(Exception):
    pass


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
        env_path = self.project_directory / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))
        self.global_environment = Environment()
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
        self.global_environment.define("sort", self._sort)
        self.global_environment.define("reverse", self._reverse)
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
                result = self.execute(statement)
            return result
        finally:
            self.environment = previous

    def execute(self, node):
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
            while self.evaluate(node.condition):
                result = self.execute_block(node.body, Environment(self.environment))
            return result
        return self.evaluate(node)

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
                capital = not capital
            else:
                result.append(character)
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

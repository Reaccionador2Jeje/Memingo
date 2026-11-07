import json
import os
import random
import urllib.request
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
        self.global_environment.define("whatkind", lambda value: "whole" if isinstance(value, (int, float)) else "caption" if isinstance(value, str) else "party" if isinstance(value, list) else "party" if isinstance(value, dict) else "based-or-cringe" if isinstance(value, bool) else "ghost" if value is None else type(value).__name__)
        self.global_environment.define("json_parse", lambda text: json.loads(text))
        self.global_environment.define("json_stringify", lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":")))
        self.global_environment.define("env", lambda name, default=None: os.environ.get(name, default))
        self.global_environment.define("random", random.random)
        self.global_environment.define("random_int", lambda low, high: random.randint(low, high))
        self.global_environment.define("range", lambda end: list(range(end)) if isinstance(end, int) else [])
        self.global_environment.define("keys", lambda value: list(value.keys()) if isinstance(value, dict) else [])
        self.global_environment.define("push", lambda items, value: items.append(value) or value if isinstance(items, list) else None)
        self.global_environment.define("append", lambda items, value: items.append(value) or len(items) if isinstance(items, list) else None)
        self.global_environment.define("set_value", lambda container, key, value: container.__setitem__(key, value) or value if isinstance(container, (dict, list)) else None)
        self.global_environment.define("delete_key", lambda container, key: container.pop(key, None) if isinstance(container, dict) else None)
        self.global_environment.define("http_get", self._http_get)
        self.global_environment.define("http_post", self._http_post)

    def run(self, program):
        return self.execute_block(program.statements, self.global_environment)

    def execute_block(self, statements, environment):
        previous = getattr(self, "environment", None)
        self.environment = environment
        try:
            result = None
            for statement in statements:
                result = self.execute(statement)
                if isinstance(statement, Return):
                    return result
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
        if isinstance(node, Borrow):
            package_name = self.evaluate(node.package)
            if not isinstance(package_name, str):
                raise RuntimeErrorMemingo("borrow requires a package name")
            package_dir = self.project_directory / ".memingo" / "packages" / package_name
            lock_path = self.project_directory / "memingo.lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {}
            record = lock.get("dependencies", {}).get(package_name)
            entry = record.get("entry", "main.mgo") if isinstance(record, dict) else "main.mgo"
            entry_path = package_dir / entry
            if not entry_path.exists():
                raise RuntimeErrorMemingo(f"Borrowed package '{package_name}' is not installed")
            module_environment = Environment(self.environment)
            previous = self.environment
            self.environment = module_environment
            try:
                module_program = parse(entry_path.read_text(encoding="utf-8"))
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
                return callee(*arguments)
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
        request = urllib.request.Request(str(url), headers={"User-Agent": "Memingo/0.1"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8")) if response.headers.get_content_type() == "application/json" else response.read().decode("utf-8")

    def _http_post(self, url, payload=None):
        body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(str(url), data=body, headers={"Content-Type": "application/json", "User-Agent": "Memingo/0.1"}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read().decode("utf-8")
            return json.loads(data) if response.headers.get_content_type() == "application/json" else data

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

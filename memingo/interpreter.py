import json

from .parser import (
    Assign, Binary, Call, Function, If, Let, ListExpression, Literal,
    Program, Return, Say, Unary, Variable, While, parse,
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
    def __init__(self):
        self.output = []
        self.global_environment = Environment()
        self.global_environment.define("headcount", lambda value: len(value))
        self.global_environment.define("whatkind", lambda value: "whole" if isinstance(value, (int, float)) else "caption" if isinstance(value, str) else "party" if isinstance(value, list) else "based-or-cringe" if isinstance(value, bool) else "ghost" if value is None else type(value).__name__) 

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
        if isinstance(node, Return):
            value = self.evaluate(node.value) if node.value is not None else None
            raise ReturnSignal(value)
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
        if isinstance(value, list):
            return json.dumps(value, ensure_ascii=False)
        return str(value)


def execute(source, capture_output=True):
    interpreter = Interpreter()
    interpreter.run(parse(source))
    return interpreter.output

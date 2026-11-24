"""First semantic pass: local name resolution and static type checking.

This checker is intentionally conservative. Unknown dynamic calls have type
ANY, allowing existing standard-library functions to keep working while
Memingo gradually adds declarations for built-ins and imported packages.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .diagnostics import DiagnosticBag, Label
from .types import (
    ANY, BASED, CAPTION, DECIMAL, GHOST, WHOLE, Type, TypeKind,
    common_type, function_of, is_assignable, list_of, map_of,
)


@dataclass
class Scope:
    parent: "Scope | None" = None
    symbols: dict[str, Type] = field(default_factory=dict)

    def define(self, name: str, value_type: Type) -> bool:
        if name in self.symbols:
            return False
        self.symbols[name] = value_type
        return True

    def lookup(self, name: str) -> Type | None:
        if name in self.symbols:
            return self.symbols[name]
        return self.parent.lookup(name) if self.parent else None

    def assign(self, name: str, value_type: Type) -> Type | None:
        if name in self.symbols:
            declared = self.symbols[name]
            if is_assignable(declared, value_type):
                return declared
            return declared
        if self.parent:
            return self.parent.assign(name, value_type)
        return None


@dataclass(frozen=True)
class TypeCheckResult:
    diagnostics: tuple
    expression_types: dict[int, Type]

    @property
    def has_errors(self) -> bool:
        return any(item.severity.value == "error" for item in self.diagnostics)


class TypeChecker:
    def __init__(self, diagnostics: DiagnosticBag | None = None):
        self.diagnostics = diagnostics if diagnostics is not None else DiagnosticBag()
        self.expression_types: dict[int, Type] = {}
        self.scope = Scope()
        self._functions: dict[str, Type] = {}

    def check(self, program) -> TypeCheckResult:
        # A checker instance can safely be reused for independent programs.
        self.expression_types.clear()
        self._functions.clear()
        self.scope = Scope()
        self.diagnostics.clear()

        # Predeclare rituals so calls can resolve regardless of declaration order.
        for statement in program.statements:
            if statement.__class__.__name__ == "Function":
                signature = function_of(tuple(ANY for _ in statement.params), ANY)
                if not self.scope.define(statement.name, signature):
                    self._error("M1001", f"'{statement.name}' is already declared in this scope", statement)
                else:
                    self._functions[statement.name] = signature

        for statement in program.statements:
            self._statement(statement)
        return TypeCheckResult(self.diagnostics.items, dict(self.expression_types))

    def _label(self, node) -> tuple[Label, ...]:
        span = getattr(node, "span", None)
        return (Label(span, primary=True),) if span is not None else ()

    def _error(self, code: str, message: str, node) -> None:
        self.diagnostics.error(code, message, *self._label(node))

    def _statement(self, node) -> None:
        name = node.__class__.__name__
        if name == "Let":
            value_type = self._expression(node.value)
            if not self.scope.define(node.name, value_type):
                self._error("M1001", f"'{node.name}' is already declared in this scope", node)
        elif name == "Assign":
            value_type = self._expression(node.value)
            declared = self.scope.lookup(node.name)
            if declared is None:
                self._error("M1002", f"unknown variable '{node.name}'", node)
            elif not is_assignable(declared, value_type):
                self._error("M1003", f"cannot assign {value_type} to '{node.name}' of type {declared}", node)
        elif name == "Say":
            self._expression(node.value)
        elif name == "Borrow":
            self._expression(node.package)
        elif name == "ReferenceBorrow":
            source_type = self.scope.lookup(node.source)
            if source_type is None:
                self._error("M1002", f"unknown variable '{node.source}'", node)
                source_type = ANY
            elif source_type.kind not in (TypeKind.LIST, TypeKind.MAP, TypeKind.ANY):
                self._error("M1020", "references currently require a list or object value", node)
            previous = self.scope
            local = Scope(previous)
            if not local.define(node.alias, source_type):
                self._error("M1001", f"'{node.alias}' is already declared in this scope", node)
            self.scope = local
            self._check_block(node.body, nested=False)
            self.scope = previous
        elif name == "Return":
            self._expression(node.value)
        elif name == "If":
            condition = self._expression(node.condition)
            self._require_boolean(condition, node.condition, "when")
            self._check_block(node.then_branch)
            self._check_block(node.else_branch)
        elif name == "While":
            condition = self._expression(node.condition)
            self._require_boolean(condition, node.condition, "grind")
            self._check_block(node.body)
        elif name == "Function":
            previous = self.scope
            local = Scope(previous)
            for parameter in node.params:
                if not local.define(parameter.name, ANY):
                    self._error("M1014", f"duplicate parameter '{parameter.name}'", node)
            self.scope = local
            self._check_block(node.body, nested=False)
            self.scope = previous
        else:
            self._expression(node)

    def _check_block(self, statements, nested=True) -> None:
        previous = self.scope
        if nested:
            self.scope = Scope(previous)
        for statement in statements:
            self._statement(statement)
        if nested:
            self.scope = previous

    def _require_boolean(self, value_type: Type, node, construct: str) -> None:
        if value_type != ANY and value_type != BASED:
            self._error("M1004", f"'{construct}' condition must be based-or-cringe, got {value_type}", node)

    def _remember(self, node, value_type: Type) -> Type:
        self.expression_types[id(node)] = value_type
        return value_type

    def _expression(self, node) -> Type:
        name = node.__class__.__name__
        if name == "Literal":
            value = node.value
            if value is None:
                result = GHOST
            elif isinstance(value, bool):
                result = BASED
            elif isinstance(value, int):
                result = WHOLE
            elif isinstance(value, float):
                result = DECIMAL
            elif isinstance(value, str):
                result = CAPTION
            else:
                result = ANY
        elif name == "Variable":
            result = self.scope.lookup(node.name)
            if result is None:
                self._error("M1002", f"unknown variable '{node.name}'", node)
                result = ANY
        elif name == "ListExpression":
            result = list_of(ANY)
            if node.items:
                item_type = self._expression(node.items[0])
                for item in node.items[1:]:
                    item_type = common_type(item_type, self._expression(item))
                result = list_of(item_type)
        elif name == "MapExpression":
            value_type = ANY
            if node.entries:
                value_type = self._expression(node.entries[0][1])
                for _, value in node.entries[1:]:
                    value_type = common_type(value_type, self._expression(value))
            result = map_of(value_type)
        elif name == "Unary":
            operand = self._expression(node.operand)
            if node.operator == "!":
                if operand not in (BASED, ANY):
                    self._error("M1005", f"operator '!' requires based-or-cringe, got {operand}", node)
                result = BASED
            else:
                if operand not in (WHOLE, DECIMAL, ANY):
                    self._error("M1006", f"unary '-' requires a number, got {operand}", node)
                result = operand
        elif name == "Binary":
            left = self._expression(node.left)
            right = self._expression(node.right)
            result = self._binary_type(node.operator, left, right, node)
        elif name == "Get":
            target = self._expression(node.target)
            key = self._expression(node.key)
            if target.kind is TypeKind.LIST:
                if key not in (WHOLE, ANY):
                    self._error("M1007", f"list index must be whole, got {key}", node.key)
                result = target.arguments[0]
            elif target.kind is TypeKind.MAP:
                result = target.arguments[0]
            elif target is ANY:
                result = ANY
            else:
                self._error("M1008", f"cannot index value of type {target}", node)
                result = ANY
        elif name == "Call":
            callee = self._expression(node.callee)
            argument_types = tuple(self._expression(argument) for argument in node.arguments)
            if callee.kind is TypeKind.FUNCTION:
                parameters = callee.arguments[:-1]
                if len(parameters) != len(argument_types):
                    self._error("M1009", f"ritual expects {len(parameters)} arguments, got {len(argument_types)}", node)
                for index, (expected, actual) in enumerate(zip(parameters, argument_types), 1):
                    if not is_assignable(expected, actual):
                        self._error("M1010", f"argument {index} expects {expected}, got {actual}", node.arguments[index - 1])
                result = callee.arguments[-1]
            else:
                # Dynamic built-ins and imported values remain supported.
                result = ANY
        else:
            result = ANY
        return self._remember(node, result)

    def _binary_type(self, operator: str, left: Type, right: Type, node) -> Type:
        numeric = (WHOLE, DECIMAL, ANY)
        if operator in ("+", "-", "*", "/", "%"):
            if operator == "+" and left == CAPTION and right == CAPTION:
                return CAPTION
            if left not in numeric or right not in numeric:
                self._error("M1011", f"operator '{operator}' requires compatible numbers, got {left} and {right}", node)
                return ANY
            if operator == "/" or DECIMAL in (left, right):
                return DECIMAL
            return WHOLE
        if operator in ("<", ">", "<=", ">="):
            if left not in numeric or right not in numeric:
                self._error("M1012", f"operator '{operator}' requires numbers, got {left} and {right}", node)
            return BASED
        if operator in ("==", "!="):
            if common_type(left, right) is ANY and left is not ANY and right is not ANY:
                self._error("M1013", f"cannot compare {left} with {right}", node)
            return BASED
        if operator in ("&&", "||"):
            self._require_boolean(left, node.left, operator)
            self._require_boolean(right, node.right, operator)
            return BASED
        return ANY


def check(program, diagnostics: DiagnosticBag | None = None) -> TypeCheckResult:
    return TypeChecker(diagnostics).check(program)

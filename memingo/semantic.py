"""Conservative static checks for Memingo ASTs.

The analyzer only reports errors that can be proven from the current
single-file syntax. It deliberately does not guess at names provided by
borrowed packages or dynamic values.
"""

from dataclasses import dataclass

from .parser import (
    Binary, Call, Function, Get, If, ListExpression, Literal, MapExpression,
    Program, Return, Say, Unary, Variable, While, Let, Assign, Borrow,
)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int = 1

    def __str__(self):
        return f"{self.code} at line {self.line}: {self.message}"


def analyze(program):
    """Return deterministic, conservative semantic diagnostics for a Program."""
    diagnostics = []
    _check_scope(program.statements, {}, diagnostics)
    return diagnostics


def _check_scope(statements, parent_functions, diagnostics):
    functions = dict(parent_functions)
    for statement in statements:
        if isinstance(statement, Function):
            functions[statement.name] = len(statement.params)

    for statement in statements:
        line = getattr(statement, "line", 1)
        if isinstance(statement, Function):
            seen = set()
            for parameter in statement.params:
                if parameter in seen:
                    diagnostics.append(Diagnostic(
                        "MGO201",
                        f"Duplicate parameter '{parameter}' in ritual '{statement.name}'",
                        line,
                    ))
                seen.add(parameter)
            _check_scope(statement.body, functions, diagnostics)
        elif isinstance(statement, If):
            _check_expression(statement.condition, functions, line, diagnostics)
            _check_scope(statement.then_branch, functions, diagnostics)
            _check_scope(statement.else_branch, functions, diagnostics)
        elif isinstance(statement, While):
            _check_expression(statement.condition, functions, line, diagnostics)
            _check_scope(statement.body, functions, diagnostics)
        elif isinstance(statement, (Let, Assign, Say, Return, Borrow)):
            value = (
                statement.value if isinstance(statement, (Let, Assign, Say, Return))
                else statement.package if isinstance(statement, Borrow)
                else None
            )
            if value is not None:
                _check_expression(value, functions, line, diagnostics)
        else:
            _check_expression(statement, functions, line, diagnostics)


def _check_expression(node, functions, line, diagnostics):
    if isinstance(node, Call):
        if isinstance(node.callee, Variable):
            name = node.callee.name
            if name in functions:
                expected = functions[name]
                actual = len(node.arguments)
                if actual != expected:
                    diagnostics.append(Diagnostic(
                        "MGO202",
                        f"Ritual '{name}' expects {expected} argument(s), got {actual}",
                        line,
                    ))
        _check_expression(node.callee, functions, line, diagnostics)
        for argument in node.arguments:
            _check_expression(argument, functions, line, diagnostics)
    elif isinstance(node, Binary):
        _check_expression(node.left, functions, line, diagnostics)
        _check_expression(node.right, functions, line, diagnostics)
    elif isinstance(node, Unary):
        _check_expression(node.operand, functions, line, diagnostics)
    elif isinstance(node, Get):
        _check_expression(node.target, functions, line, diagnostics)
        _check_expression(node.key, functions, line, diagnostics)
    elif isinstance(node, ListExpression):
        for item in node.items:
            _check_expression(item, functions, line, diagnostics)
    elif isinstance(node, MapExpression):
        for _, value in node.entries:
            _check_expression(value, functions, line, diagnostics)

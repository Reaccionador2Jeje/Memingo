"""Conservative static ownership analysis for collection values.

This first pass models a collection binding as a unique owner. Initializing a
second binding directly from that owner transfers ownership and marks the
source as moved. It deliberately does not infer borrow lifetimes or inspect
mutations performed by dynamic built-ins yet.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .diagnostics import DiagnosticBag, Label
from .types import Type, TypeKind


@dataclass
class _Flow:
    types: dict[str, Type] = field(default_factory=dict)
    moved: set[str] = field(default_factory=set)

    def clone(self):
        return _Flow(dict(self.types), set(self.moved))


@dataclass(frozen=True)
class OwnershipResult:
    diagnostics: tuple

    @property
    def has_errors(self):
        return any(item.severity.value == "error" for item in self.diagnostics)


class OwnershipChecker:
    def __init__(self, expression_types=None, diagnostics=None):
        self.expression_types = expression_types or {}
        self.diagnostics = diagnostics if diagnostics is not None else DiagnosticBag()
        self._reported = set()

    def check(self, program):
        self._reported.clear()
        flow = _Flow()
        self._block(program.statements, flow)
        return OwnershipResult(self.diagnostics.items)

    def _error(self, node, name):
        key = (id(node), name)
        if key in self._reported:
            return
        self._reported.add(key)
        span = getattr(node, "span", None)
        labels = (Label(span, primary=True),) if span is not None else ()
        self.diagnostics.error(
            "M2001",
            f"use of moved value '{name}'; its ownership was transferred to another binding",
            *labels,
        )

    def _type_of(self, expression):
        return self.expression_types.get(id(expression))

    def _is_owned(self, value_type):
        return value_type is not None and value_type.kind in (TypeKind.LIST, TypeKind.MAP)

    def _read(self, node, flow):
        kind = node.__class__.__name__
        if kind == "Variable":
            if node.name in flow.moved:
                self._error(node, node.name)
            return
        if kind == "ListExpression":
            for item in node.items:
                self._read(item, flow)
        elif kind == "MapExpression":
            for _, value in node.entries:
                self._read(value, flow)
        elif kind == "Get":
            self._read(node.target, flow)
            self._read(node.key, flow)
        elif kind == "Binary":
            self._read(node.left, flow)
            self._read(node.right, flow)
        elif kind == "Unary":
            self._read(node.operand, flow)
        elif kind == "Call":
            self._read(node.callee, flow)
            for argument in node.arguments:
                self._read(argument, flow)

    def _bind(self, target, value, flow):
        self._read(value, flow)
        target_type = self._type_of(value)
        if value.__class__.__name__ == "Variable":
            source = value.name
            source_type = flow.types.get(source, self._type_of(value))
            if self._is_owned(source_type):
                flow.moved.add(source)
                flow.types[target] = source_type
                flow.moved.discard(target)
                return
        flow.types[target] = target_type
        flow.moved.discard(target)

    def _block(self, statements, flow):
        for node in statements:
            kind = node.__class__.__name__
            if kind == "Let":
                self._bind(node.name, node.value, flow)
            elif kind == "Assign":
                self._read(node.value, flow)
                value_type = self._type_of(node.value)
                if node.value.__class__.__name__ == "Variable":
                    source = node.value.name
                    source_type = flow.types.get(source, self._type_of(node.value))
                    if self._is_owned(source_type):
                        flow.moved.add(source)
                        value_type = source_type
                flow.types[node.name] = value_type or flow.types.get(node.name)
                flow.moved.discard(node.name)
            elif kind in ("Say", "Return"):
                self._read(node.value, flow)
            elif kind == "Borrow":
                self._read(node.package, flow)
            elif kind == "If":
                self._read(node.condition, flow)
                then_flow, else_flow = flow.clone(), flow.clone()
                self._block(node.then_branch, then_flow)
                self._block(node.else_branch, else_flow)
                # A value is definitely moved after the branch only if moved on
                # both paths; this avoids rejecting valid one-sided control flow.
                flow.moved |= then_flow.moved & else_flow.moved
            elif kind == "While":
                self._read(node.condition, flow)
                body_flow = flow.clone()
                self._block(node.body, body_flow)
                # A loop may execute zero times, so moves in its body are not
                # definite after the loop.
            elif kind == "Function":
                local = _Flow()
                for parameter in node.params:
                    local.types[parameter] = None
                self._block(node.body, local)
            else:
                self._read(node, flow)


def check_ownership(program, expression_types=None, diagnostics=None):
    return OwnershipChecker(expression_types, diagnostics).check(program)

"""Typed high-level intermediate representation and AST lowering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .source import Span
from .types import ANY, Type


@dataclass(frozen=True, slots=True)
class HIRNode:
    """A normalized compiler node independent from parser implementation details."""

    kind: str
    span: Span | None
    type: Type
    value: Any = None
    children: tuple["HIRNode", ...] = ()


@dataclass(frozen=True, slots=True)
class HIRProgram:
    statements: tuple[HIRNode, ...]


def lower(program, expression_types: Mapping[int, Type] | None = None) -> HIRProgram:
    """Lower the current AST into a compact typed tree.

    The lowering is deliberately lossless for the language constructs currently
    represented by the parser. New AST node kinds fail loudly rather than being
    silently discarded.
    """
    types = expression_types or {}

    def visit(node) -> HIRNode:
        name = node.__class__.__name__
        span = getattr(node, "span", None)
        value = None
        children: list[HIRNode] = []

        if name in ("Literal",):
            value = node.value
        elif name in ("Variable",):
            value = node.name
        elif name in ("Let", "Assign"):
            value = node.name
            children.append(visit(node.value))
        elif name in ("Say", "Return"):
            children.append(visit(node.value))
        elif name == "Borrow":
            children.append(visit(node.package))
        elif name == "If":
            children.append(visit(node.condition))
            children.extend(visit(item) for item in node.then_branch)
            children.extend(visit(item) for item in node.else_branch)
            value = {"then_count": len(node.then_branch), "else_count": len(node.else_branch)}
        elif name == "While":
            children.append(visit(node.condition))
            children.extend(visit(item) for item in node.body)
            value = {"body_count": len(node.body)}
        elif name == "Function":
            children.extend(visit(item) for item in node.body)
            value = {"name": node.name, "parameters": tuple(node.params)}
        elif name == "ListExpression":
            children.extend(visit(item) for item in node.items)
        elif name == "MapExpression":
            for key, item in node.entries:
                children.append(HIRNode("MapKey", None, ANY, key))
                children.append(visit(item))
        elif name == "Get":
            children.extend((visit(node.target), visit(node.key)))
        elif name == "Binary":
            value = node.operator
            children.extend((visit(node.left), visit(node.right)))
        elif name == "Unary":
            value = node.operator
            children.append(visit(node.operand))
        elif name == "Call":
            children.append(visit(node.callee))
            children.extend(visit(item) for item in node.arguments)
            value = {"argument_count": len(node.arguments)}
        elif name == "Program":
            children.extend(visit(item) for item in node.statements)
        else:
            raise TypeError(f"unsupported AST node during HIR lowering: {name}")

        inferred = types.get(id(node), ANY)
        return HIRNode(name, span, inferred, value, tuple(children))

    return HIRProgram(tuple(visit(statement) for statement in program.statements))

"""Call-scoped exclusive-borrow checks for mutating collection built-ins.

Memingo does not yet expose explicit reference syntax. This pass therefore
models the exclusive mutable borrow performed by known mutating built-ins and
rejects a second argument that aliases the same collection during that call.
"""
from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import DiagnosticBag, Label


_MUTATING_ARGUMENTS = {
    "push": (0,),
    "append": (0,),
    "set_value": (0,),
    "delete_key": (0,),
}


@dataclass(frozen=True)
class BorrowResult:
    diagnostics: tuple

    @property
    def has_errors(self):
        return any(item.severity.value == "error" for item in self.diagnostics)


class BorrowChecker:
    def __init__(self, diagnostics=None):
        self.diagnostics = diagnostics if diagnostics is not None else DiagnosticBag()
        self._reported = set()

    def check(self, program):
        self._reported.clear()
        for statement in program.statements:
            self._visit(statement)
        return BorrowResult(self.diagnostics.items)

    def _root(self, expression):
        kind = expression.__class__.__name__
        if kind == "Variable":
            return expression.name
        if kind == "Get":
            return self._root(expression.target)
        return None

    def _roots(self, expression):
        found = set()
        kind = expression.__class__.__name__
        if kind == "Variable":
            found.add(expression.name)
        elif kind == "Get":
            found |= self._roots(expression.target)
            found |= self._roots(expression.key)
        elif kind == "Call":
            found |= self._roots(expression.callee)
            for argument in expression.arguments:
                found |= self._roots(argument)
        elif kind == "ListExpression":
            for item in expression.items:
                found |= self._roots(item)
        elif kind == "MapExpression":
            for _, item in expression.entries:
                found |= self._roots(item)
        elif kind == "Binary":
            found |= self._roots(expression.left)
            found |= self._roots(expression.right)
        elif kind == "Unary":
            found |= self._roots(expression.operand)
        return found

    def _error(self, call, name, argument):
        key = (id(call), name)
        if key in self._reported:
            return
        self._reported.add(key)
        span = getattr(argument, "span", None) or getattr(call, "span", None)
        labels = (Label(span, primary=True),) if span is not None else ()
        self.diagnostics.error(
            "M2101",
            f"conflicting mutable borrow of '{name}' in one call; "
            "the collection is both mutably borrowed and accessed by another argument",
            *labels,
        )

    def _walk(self, node):
        if node is None:
            return
        yield node
        if not hasattr(node, "__dict__"):
            return
        for value in vars(node).values():
            if isinstance(value, (list, tuple)):
                for item in value:
                    yield from self._walk(item)
            elif hasattr(value, "__dict__"):
                yield from self._walk(value)

    def _lifetime_error(self, code, node, message):
        key = (code, id(node))
        if key in self._reported:
            return
        self._reported.add(key)
        span = getattr(node, "span", None)
        labels = (Label(span, primary=True),) if span is not None else ()
        self.diagnostics.error(code, message, *labels)

    def _check_reference_scope(self, node):
        source, alias = node.source, node.alias
        if source == alias:
            self._lifetime_error("M2201", node, "reference name must differ from its source")
            return
        if node.mutable:
            for item in node.body:
                for part in self._walk(item):
                    if ((part.__class__.__name__ == "Variable" and part.name == source)
                            or (part.__class__.__name__ == "Assign" and part.name == source)):
                        self._lifetime_error(
                            "M2203", part,
                            f"source '{source}' cannot be accessed while its mutable reference '{alias}' is active",
                        )
                        break
        else:
            for item in node.body:
                for part in self._walk(item):
                    if part.__class__.__name__ == "Assign" and part.name == source:
                        self._lifetime_error(
                            "M2202", part,
                            f"cannot reassign '{source}' inside an immutable reference scope",
                        )
                    if part.__class__.__name__ == "Call":
                        callee = part.callee
                        name = callee.name if callee.__class__.__name__ == "Variable" else None
                        for position in _MUTATING_ARGUMENTS.get(name, ()):
                            if (position < len(part.arguments)
                                    and ({alias, source} & self._roots(part.arguments[position]))):
                                self._lifetime_error(
                                    "M2202", part,
                                    f"cannot mutate the borrowed collection inside an immutable reference scope",
                                )
        for item in node.body:
            for part in self._walk(item):
                if (part.__class__.__name__ == "ReferenceBorrow"
                        and part.source in (source, alias)):
                    if node.mutable or part.mutable:
                        self._lifetime_error(
                            "M2205", part,
                            f"overlapping references to '{source}' include a mutable borrow",
                        )
        # References are lexical and cannot escape through return or assignment.
        for item in node.body:
            for part in self._walk(item):
                kind = part.__class__.__name__
                if kind == "Return" and alias in self._roots(part.value):
                    self._lifetime_error("M2204", part, f"reference '{alias}' cannot escape its borrow scope")
                elif kind == "Assign" and alias in self._roots(part.value):
                    self._lifetime_error("M2204", part, f"reference '{alias}' cannot be assigned outside its borrow scope")

    def _visit(self, node):
        if node is None:
            return
        kind = node.__class__.__name__
        if kind == "ReferenceBorrow":
            self._check_reference_scope(node)
            for item in node.body:
                self._visit(item)
        elif kind == "Call":
            callee = node.callee
            function_name = callee.name if callee.__class__.__name__ == "Variable" else None
            mutable_positions = _MUTATING_ARGUMENTS.get(function_name, ())
            for position in mutable_positions:
                if position >= len(node.arguments):
                    continue
                mutable_argument = node.arguments[position]
                mutable_roots = self._roots(mutable_argument)
                for index, other_argument in enumerate(node.arguments):
                    if index == position:
                        continue
                    overlap = mutable_roots & self._roots(other_argument)
                    for name in overlap:
                        self._error(node, name, other_argument)
            self._visit(node.callee)
            for argument in node.arguments:
                self._visit(argument)
        elif kind == "Let" or kind == "Assign":
            self._visit(node.value)
        elif kind in ("Say", "Return"):
            self._visit(node.value)
        elif kind == "Borrow":
            self._visit(node.package)
        elif kind == "If":
            self._visit(node.condition)
            for item in node.then_branch + node.else_branch:
                self._visit(item)
        elif kind == "While":
            self._visit(node.condition)
            for item in node.body:
                self._visit(item)
        elif kind == "Function":
            for item in node.body:
                self._visit(item)
        elif kind == "ListExpression":
            for item in node.items:
                self._visit(item)
        elif kind == "MapExpression":
            for _, item in node.entries:
                self._visit(item)
        elif kind == "Get":
            self._visit(node.target)
            self._visit(node.key)
        elif kind == "Binary":
            self._visit(node.left)
            self._visit(node.right)
        elif kind == "Unary":
            self._visit(node.operand)


def check_borrows(program, diagnostics=None):
    return BorrowChecker(diagnostics).check(program)

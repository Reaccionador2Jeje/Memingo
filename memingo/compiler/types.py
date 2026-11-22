"""Type model for Memingo's gradual-to-static compiler pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TypeKind(str, Enum):
    ANY = "any"
    GHOST = "ghost"
    BASED = "based-or-cringe"
    WHOLE = "whole"
    DECIMAL = "decimal"
    CAPTION = "caption"
    LIST = "list"
    MAP = "map"
    FUNCTION = "ritual"


@dataclass(frozen=True, slots=True)
class Type:
    kind: TypeKind
    arguments: tuple["Type", ...] = ()

    def __post_init__(self) -> None:
        expected = {
            TypeKind.LIST: 1,
            TypeKind.MAP: 1,
        }.get(self.kind)
        if expected is not None and len(self.arguments) != expected:
            raise ValueError(f"{self.kind.value} type requires {expected} type argument")
        if self.kind is TypeKind.FUNCTION and not self.arguments:
            raise ValueError("ritual type requires a return type")
        if self.kind not in (TypeKind.LIST, TypeKind.MAP, TypeKind.FUNCTION) and self.arguments:
            raise ValueError(f"{self.kind.value} type does not accept type arguments")

    def __str__(self) -> str:
        if self.kind is TypeKind.LIST:
            return f"party[{self.arguments[0]}]"
        if self.kind is TypeKind.MAP:
            return f"object[{self.arguments[0]}]"
        if self.kind is TypeKind.FUNCTION:
            *parameters, result = self.arguments
            return f"ritual({', '.join(map(str, parameters))}) -> {result}"
        return self.kind.value


ANY = Type(TypeKind.ANY)
GHOST = Type(TypeKind.GHOST)
BASED = Type(TypeKind.BASED)
WHOLE = Type(TypeKind.WHOLE)
DECIMAL = Type(TypeKind.DECIMAL)
CAPTION = Type(TypeKind.CAPTION)


def list_of(item: Type = ANY) -> Type:
    return Type(TypeKind.LIST, (item,))


def map_of(value: Type = ANY) -> Type:
    return Type(TypeKind.MAP, (value,))


def function_of(parameters: tuple[Type, ...], result: Type = ANY) -> Type:
    return Type(TypeKind.FUNCTION, (*parameters, result))


def common_type(left: Type, right: Type) -> Type:
    """Return a safe common type, widening whole numbers to decimals."""
    if left == right:
        return left
    if left == ANY or right == ANY:
        return ANY
    if {left.kind, right.kind} == {TypeKind.WHOLE, TypeKind.DECIMAL}:
        return DECIMAL
    if left.kind is TypeKind.LIST and right.kind is TypeKind.LIST:
        return list_of(common_type(left.arguments[0], right.arguments[0]))
    if left.kind is TypeKind.MAP and right.kind is TypeKind.MAP:
        return map_of(common_type(left.arguments[0], right.arguments[0]))
    return ANY


def is_assignable(target: Type, value: Type) -> bool:
    """Whether a value can be assigned to a variable of target type."""
    if target == ANY or value == ANY or target == value:
        return True
    if target.kind is TypeKind.DECIMAL and value.kind is TypeKind.WHOLE:
        return True
    if target.kind is TypeKind.LIST and value.kind is TypeKind.LIST:
        return is_assignable(target.arguments[0], value.arguments[0])
    if target.kind is TypeKind.MAP and value.kind is TypeKind.MAP:
        return is_assignable(target.arguments[0], value.arguments[0])
    return False

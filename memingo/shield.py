"""Hybrid Shield: bounded runtime safeguards for Memingo programs.

The shield reduces accidental resource exhaustion and catches oversized values.
It is not a hardware fault barrier or a substitute for static ownership analysis.
"""
from dataclasses import dataclass
import math
import sys


class ShieldViolation(Exception):
    """Raised when a program exceeds a configured safety boundary."""


@dataclass(frozen=True)
class ShieldLimits:
    max_steps: int = 1_000_000
    max_call_depth: int = 256
    max_collection_items: int = 100_000
    max_string_chars: int = 4_000_000
    max_integer_bits: int = 1_000_000
    max_memory_bytes: int = 64 * 1024 * 1024

    def __post_init__(self):
        for name, value in self.__dict__.items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


class MemingoShield:
    """Per-execution guard for steps, call depth, and runtime values."""

    def __init__(self, limits=None):
        self.limits = limits or ShieldLimits()
        self.steps = 0
        self.call_depth = 0
        self.memory_bytes = 0

    def tick(self, amount=1):
        if amount < 0:
            raise ValueError("shield tick amount cannot be negative")
        self.steps += amount
        if self.steps > self.limits.max_steps:
            raise ShieldViolation(
                f"execution step budget exceeded ({self.limits.max_steps:,}); "
                "check for an endless loop or reduce the workload"
            )

    def enter_call(self):
        if self.call_depth >= self.limits.max_call_depth:
            raise ShieldViolation(
                f"maximum ritual call depth exceeded "
                f"({self.limits.max_call_depth})"
            )
        self.call_depth += 1

    def leave_call(self):
        if self.call_depth > 0:
            self.call_depth -= 1

    def check_collection_size(self, size):
        if size > self.limits.max_collection_items:
            raise ShieldViolation(
                f"collection limit exceeded ({self.limits.max_collection_items:,} items)"
            )

    def estimate_size(self, value, seen=None):
        """Estimate reachable Python container memory without double-counting aliases.

        This is an accounting estimate, not a measurement of process RSS or a
        guarantee about allocator/native-extension memory.
        """
        if seen is None:
            seen = set()
        identity = id(value)
        if identity in seen:
            return 0
        seen.add(identity)
        size = sys.getsizeof(value)
        if isinstance(value, dict):
            size += sum(self.estimate_size(key, seen) + self.estimate_size(item, seen)
                        for key, item in value.items())
        elif isinstance(value, (list, tuple, set, frozenset)):
            size += sum(self.estimate_size(item, seen) for item in value)
        return size

    def check_memory(self, value):
        self.memory_bytes = self.estimate_size(value)
        if self.memory_bytes > self.limits.max_memory_bytes:
            raise ShieldViolation(
                f"memory budget exceeded ({self.limits.max_memory_bytes:,} bytes; "
                f"estimated {self.memory_bytes:,} bytes)"
            )
        return self.memory_bytes

    def validate(self, value, seen=None):
        """Validate values crossing interpreter boundaries without traversing cycles."""
        if isinstance(value, (bytes, bytearray)):
            if len(value) > self.limits.max_string_chars:
                raise ShieldViolation(
                    f"binary value limit exceeded ({self.limits.max_string_chars:,} bytes)"
                )
            return value
        if isinstance(value, str):
            if len(value) > self.limits.max_string_chars:
                raise ShieldViolation(
                    f"string limit exceeded ({self.limits.max_string_chars:,} characters)"
                )
            return value
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, int):
            if value.bit_length() > self.limits.max_integer_bits:
                raise ShieldViolation(
                    f"integer size limit exceeded ({self.limits.max_integer_bits:,} bits)"
                )
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ShieldViolation("non-finite numeric value is not allowed")
            return value
        if isinstance(value, (list, tuple, dict)):
            self.check_collection_size(len(value))
            if seen is None:
                seen = set()
            identity = id(value)
            if identity in seen:
                return value
            seen.add(identity)
            children = value.values() if isinstance(value, dict) else value
            for child in children:
                self.validate(child, seen)
            seen.remove(identity)
        return value

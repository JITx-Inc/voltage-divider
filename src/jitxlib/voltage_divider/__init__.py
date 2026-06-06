"""
voltage_divider
===============

Python API for voltage divider constraint solving and circuit construction.

Exposes:
- VoltageDividerConstraints
- InverseDividerConstraints
- solve
- voltage_divider
- voltage_divider_from_constraints
- forward_divider
- inverse_divider
"""

from .constraints import VoltageDividerConstraints
from .inverse import InverseDividerConstraints
from .solver import solve
from .circuit import (
    voltage_divider,
    voltage_divider_from_constraints,
    forward_divider,
    inverse_divider,
)

__all__ = [
    "VoltageDividerConstraints",
    "InverseDividerConstraints",
    "solve",
    "voltage_divider",
    "voltage_divider_from_constraints",
    "forward_divider",
    "inverse_divider",
]

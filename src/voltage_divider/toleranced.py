from dataclasses import dataclass
from typing import Optional, Union, Callable
import math

# TODO: Implement or import Percentage type as needed
# For now, treat as float in [0, 1] for percentage (e.g., 0.01 for 1%)
Percentage = float

@dataclass(eq=True, frozen=True)
class Toleranced:
    """
    Interval Arithmetic Type for values with tolerances.

    :param typ: Typical value (average/nominal)
    :param tol_plus: Relative positive increment (max bound, or None for unbounded)
    :param tol_minus: Relative negative increment (min bound, or None for unbounded)
    """
    typ: float
    tol_plus: Optional[float] = 0.0
    tol_minus: Optional[float] = 0.0

    def __str__(self):
        if self.tol_minus and self.tol_plus:
            return f"Toleranced({self.min_value()} <= {self.typ} <= {self.max_value()})"
        elif self.tol_minus:
            return f"Toleranced({self.min_value()} <= typ:{self.typ})"
        elif self.tol_plus:
            return f"Toleranced(typ:{self.typ} <= {self.max_value()})"
        else:
            return f"Toleranced({self.typ})"

    def max_value(self) -> float:
        if self.tol_plus is not None:
            return self.typ + self.tol_plus
        raise ValueError("tol_plus must be specified to compute max_value")

    def min_value(self) -> float:
        if self.tol_minus is not None:
            return self.typ - self.tol_minus
        raise ValueError("tol_minus must be specified to compute min_value")

    def center_value(self) -> float:
        return self.min_value() + 0.5 * (self.max_value() - self.min_value())

    def tol_plus_percent(self) -> float:
        if self.typ == 0.0:
            raise ValueError("typ() != 0.0 to compute tol+%(Toleranced)")
        return 100.0 * self.tol_plus / self.typ

    def tol_minus_percent(self) -> float:
        if self.typ == 0.0:
            raise ValueError("typ() != 0.0 to compute tol-%(Toleranced)")
        return 100.0 * self.tol_minus / self.typ

    def in_range(self, value: Union[float, 'Toleranced', Percentage]) -> bool:
        if isinstance(value, Toleranced):
            return value.min_value() >= self.min_value() and value.max_value() <= self.max_value()
        elif isinstance(value, float):
            return self.min_value() <= value <= self.max_value()
        elif isinstance(value, (int, float)):
            return self.min_value() <= value <= self.max_value()
        # TODO: Handle Percentage type
        return False

    def tolerance_range(self) -> float:
        return self.max_value() - self.min_value()

    def _full_tolerance(self):
        return (
            isinstance(self.typ, float)
            and isinstance(self.tol_plus, float)
            and isinstance(self.tol_minus, float)
        )

    # Arithmetic operators
    def __add__(self, other: Union['Toleranced', float]) -> 'Toleranced':
        if isinstance(other, Toleranced):
            if self._full_tolerance() and other._full_tolerance():
                return Toleranced(
                    self.typ + other.typ,
                    self.tol_plus + other.tol_plus,
                    self.tol_minus + other.tol_minus
                )
            else:
                raise ValueError("Toleranced() arithmetic operations require fully specified arguments")
        elif isinstance(other, (int, float)):
            return Toleranced(self.typ + other, self.tol_plus, self.tol_minus)
        return NotImplemented

    def __radd__(self, other: float) -> 'Toleranced':
        # float + Toleranced
        return self.__add__(other)

    def __sub__(self, other: Union['Toleranced', float]) -> 'Toleranced':
        if isinstance(other, Toleranced):
            if self._full_tolerance() and other._full_tolerance():
                return Toleranced(
                    self.typ - other.typ,
                    self.tol_plus + other.tol_minus,
                    self.tol_minus + other.tol_plus
                )
            else:
                raise ValueError("Toleranced() arithmetic operations require fully specified arguments")
        elif isinstance(other, (int, float)):
            return Toleranced(self.typ - other, self.tol_plus, self.tol_minus)
        return NotImplemented

    def __rsub__(self, other: float) -> 'Toleranced':
        # float - Toleranced
        if self._full_tolerance():
            return Toleranced(other, 0.0, 0.0) - self
        else:
            raise ValueError("Toleranced() arithmetic operations require fully specified arguments")

    def __mul__(self, other: Union['Toleranced', float, Percentage]) -> 'Toleranced':
        if isinstance(other, Toleranced):
            if self._full_tolerance() and other._full_tolerance():
                typ = self.typ * other.typ
                variants = [
                    self.min_value() * other.min_value(),
                    self.min_value() * other.max_value(),
                    self.max_value() * other.min_value(),
                    self.max_value() * other.max_value(),
                ]
                tol_plus = max(variants) - typ
                tol_minus = typ - min(variants)
                return Toleranced(typ, tol_plus, tol_minus)
            else:
                raise ValueError("Toleranced() arithmetic operations require fully specified arguments")
        elif isinstance(other, (int, float)):
            return Toleranced(self.typ * other, abs(self.tol_plus * other), abs(self.tol_minus * other))
        return NotImplemented

    def __rmul__(self, other: float) -> 'Toleranced':
        # float * Toleranced
        return self.__mul__(other)

    def __truediv__(self, other: Union['Toleranced', float]) -> 'Toleranced':
        if isinstance(other, Toleranced):
            if self._full_tolerance() and other._full_tolerance():
                if other.in_range(0.0):
                    raise ZeroDivisionError("Cannot divide by zero for Toleranced values.")
                typ = self.typ / other.typ
                inv = Toleranced(1.0 / other.typ,
                                 1.0 / other.min_value() - 1.0 / other.typ,
                                 1.0 / other.typ - 1.0 / other.max_value())
                return self * inv
            else:
                raise ValueError("Toleranced() arithmetic operations require fully specified arguments")
        elif isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("Cannot divide by zero.")
            return Toleranced(self.typ / other, self.tol_plus / abs(other), self.tol_minus / abs(other))
        return NotImplemented

    def __rtruediv__(self, other: float) -> 'Toleranced':
        # float / Toleranced
        if self._full_tolerance():
            return Toleranced(other, 0.0, 0.0) / self
        else:
            raise ValueError("Toleranced() arithmetic operations require fully specified arguments")

    def apply(self, f: Callable[[float], float]) -> 'Toleranced':
        tv = f(self.typ)
        minv = f(self.min_value())
        maxv = f(self.max_value())
        return min_typ_max(minv, tv, maxv)

# Helper constructors

def min_typ_max(min_val: Optional[float], typ_val: Optional[float], max_val: Optional[float]) -> Toleranced:
    """
    Create a Toleranced value from min, typ, and max values.
    At least two must be specified.
    """
    if typ_val is not None and min_val is not None and max_val is not None:
        if typ_val < min_val or max_val < typ_val:
            raise ValueError("min-typ-max() should be [min] <= [typ] <= [max]")
        return tol(typ_val, max_val - typ_val, typ_val - min_val)
    elif min_val is not None and max_val is not None:
        if max_val < min_val:
            raise ValueError("min-typ-max() should have max >= min.")
        t = min_val + 0.5 * (max_val - min_val)
        return tol(t, max_val - t, t - min_val)
    elif typ_val is not None and min_val is not None:
        if typ_val < min_val:
            raise ValueError("min-typ-max() should have min <= typ")
        return tol(typ_val, None, typ_val - min_val)
    elif typ_val is not None and max_val is not None:
        if typ_val > max_val:
            raise ValueError("min-typ-max() should have typ <= max")
        return tol(typ_val, max_val - typ_val, None)
    else:
        raise ValueError("min-typ-max() should have at least two of min, typ, max values")

def min_max(min_val: float, max_val: float) -> Toleranced:
    """Toleranced defined by absolute min and max values."""
    return min_typ_max(min_val, None, max_val)

def min_typ(min_val: float, typ_val: float) -> Toleranced:
    """Toleranced defined by an absolute minimum and typical value."""
    return min_typ_max(min_val, typ_val, None)

def typ_max(typ_val: float, max_val: float) -> Toleranced:
    """Toleranced defined by an absolute maximum and typical value."""
    return min_typ_max(None, typ_val, max_val)

def tol_percent(typ: float, tol_plus: float, tol_minus: float) -> Toleranced:
    """Create a Toleranced based on asymmetric percentages of the typical value."""
    if not (0.0 <= tol_plus <= 100.0):
        raise ValueError("tol+ must be in range 0.0 <= tol+ <= 100.0")
    if not (0.0 <= tol_minus <= 100.0):
        raise ValueError("tol- must be in range 0.0 <= tol- <= 100.0")
    abstyp = abs(typ)
    plus = abstyp * tol_plus / 100.0
    minus = abstyp * tol_minus / 100.0
    return Toleranced(typ, plus, minus)

def tol_percent_symmetric(typ: float, tol: float) -> Toleranced:
    """Create Toleranced based on symmetric percentage relative value."""
    if not (0.0 <= tol <= 100.0):
        raise ValueError("tol must be in range 0.0 <= tol <= 100.0")
    delta = abs(typ * tol / 100.0)
    return Toleranced(typ, delta, delta)

def tol(typ: float, tol_plus: Optional[float] = 0.0, tol_minus: Optional[float] = 0.0) -> Toleranced:
    """Create a tolerance from differences higher and lower."""
    return Toleranced(typ, tol_plus, tol_minus)

def typ_toleranced(typ: float) -> Toleranced:
    """Alias for Toleranced with Zero'd tol+ and tol-."""
    return tol(typ, 0.0, 0.0)

def Exactly(x: float) -> Toleranced:
    """Exactly a value (zero tolerance)."""
    return Toleranced(x, 0.0, 0.0) 

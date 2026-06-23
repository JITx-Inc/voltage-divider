import warnings
from typing import Optional

from jitx.circuit import Circuit
from jitx.net import Net, Port
from jitx.toleranced import Toleranced
from jitxlib.parts import Resistor

from .solver import VoltageDividerSolution, solve
from .constraints import VoltageDividerConstraints
from .inverse import InverseDividerConstraints


class VoltageDividerCircuit(Circuit):
    """
    Circuit for a voltage divider solution.
    Ports: hi, out, lo
    Instances: r_hi, r_lo
    """

    hi: Port
    out: Port
    lo: Port
    r_hi: Resistor
    r_lo: Resistor
    nets: list[Net]
    output_voltage: Toleranced

    def __init__(self, sol: VoltageDividerSolution):
        # Ports
        self.hi = Port()
        self.out = Port()
        self.lo = Port()
        # Resistor instances, instantiated from the solver's pinned queries via
        # the public parts factory (safe under active instantiation).
        self.r_hi = Resistor(sol.R_h.query)
        self.r_lo = Resistor(sol.R_l.query)
        # Nets (connections). A resistor is symmetric, so p1/p2 orientation is
        # electrically irrelevant.
        self.nets = [
            self.r_hi.p1 + self.hi,
            self.r_hi.p2 + self.r_lo.p1 + self.out,
            self.r_lo.p2 + self.lo,
        ]
        # FIXME: Properties are a concept of JITX ESIR interface and don't have a port in the python interface.
        self.output_voltage = sol.vo


def _warn_name_ignored(name: Optional[str]) -> None:
    if name is not None:
        warnings.warn(
            "The `name` argument is deprecated and ignored; the circuit is "
            "always named 'VoltageDividerCircuit'.",
            DeprecationWarning,
            stacklevel=3,
        )


def voltage_divider(
    sol: VoltageDividerSolution, name: Optional[str] = None
) -> VoltageDividerCircuit:
    """
    Construct a voltage divider circuit from a solution.

    .. deprecated::
        The `name` argument is deprecated and ignored.
    """
    _warn_name_ignored(name)
    return VoltageDividerCircuit(sol)


def voltage_divider_from_constraints(
    cxt: VoltageDividerConstraints, name: Optional[str] = None
) -> VoltageDividerCircuit:
    """
    Construct a voltage divider circuit from constraints (forward or inverse).
    """
    sol = solve(cxt)
    return voltage_divider(sol, name=name)


def forward_divider(
    v_in: Toleranced, v_out: Toleranced, current: float, name: Optional[str] = None
) -> VoltageDividerCircuit:
    """
    Construct a forward voltage divider circuit from basic parameters.
    """
    cxt = VoltageDividerConstraints(v_in=v_in, v_out=v_out, current=current)
    return voltage_divider_from_constraints(cxt, name=name)


def inverse_divider(
    v_in: Toleranced, v_out: Toleranced, current: float, name: Optional[str] = None
) -> VoltageDividerCircuit:
    """
    Construct an inverse voltage divider circuit from basic parameters.
    """
    cxt = InverseDividerConstraints(v_in=v_in, v_out=v_out, current=current)
    return voltage_divider_from_constraints(cxt, name=name)

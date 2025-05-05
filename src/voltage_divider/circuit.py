from jitx.circuit import Circuit
from jitx.net import Port
from jitx_parts.convert import convert_component
from src.voltage_divider.solver import VoltageDividerSolution, solve
from src.voltage_divider.constraints import VoltageDividerConstraints
from src.voltage_divider.inverse import InverseDividerConstraints
from src.voltage_divider.toleranced import Toleranced

class VoltageDividerCircuit(Circuit):
    """
    Circuit for a voltage divider solution.
    Ports: hi, out, lo
    Instances: r_hi, r_lo
    """
    def __init__(self, sol: VoltageDividerSolution):
        # Ports
        self.hi = Port()
        self.out = Port()
        self.lo = Port()
        # Resistor instances
        self.r_hi = convert_component(sol.R_h, component_name="r_hi")()
        self.r_lo = convert_component(sol.R_l, component_name="r_lo")()
        # Nets (connections)
        self.nets = [
            self.r_hi.p[0] + self.hi,
            self.r_hi.p[1] + self.r_lo.p[0] + self.out,
            self.r_lo.p[1] + self.lo
        ]
        # FIXME: Properties are a concept of JITX ESIR interface and don't have a port in the python interface.
        self.output_voltage = sol.vo

def voltage_divider(sol: VoltageDividerSolution, name: str = None) -> Circuit:
    """
    Construct a voltage divider circuit from a solution.
    The returned class will have the type name set to `name` if provided.
    """
    base_class = VoltageDividerCircuit
    if name is not None:
        # Dynamically create a subclass with the given name
        return type(name, (VoltageDividerCircuit,), {})(sol)
    else:
        return base_class(sol)

def voltage_divider_from_constraints(cxt: VoltageDividerConstraints, name: str = None) -> Circuit:
    """
    Construct a voltage divider circuit from constraints (forward or inverse).
    """
    sol = solve(cxt)
    return voltage_divider(sol, name=name)

def forward_divider(v_in: Toleranced, v_out: Toleranced, current: float, name: str = None) -> Circuit:
    """
    Construct a forward voltage divider circuit from basic parameters.
    """
    cxt = VoltageDividerConstraints(v_in=v_in, v_out=v_out, current=current)
    return voltage_divider_from_constraints(cxt, name=name)

def inverse_divider(v_in: Toleranced, v_out: Toleranced, current: float, name: str = None) -> Circuit:
    """
    Construct an inverse voltage divider circuit from basic parameters.
    """
    cxt = InverseDividerConstraints(v_in=v_in, v_out=v_out, current=current)
    return voltage_divider_from_constraints(cxt, name=name) 

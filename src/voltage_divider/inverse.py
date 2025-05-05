from dataclasses import dataclass, field
from typing import List, Optional
from src.voltage_divider.toleranced import Toleranced, tol
from src.voltage_divider.constraints import VoltageDividerConstraints, get_default_resistor_query, ensure_sources_limits, STD_PRECS, DEF_MIN_SRCS, DEF_QUERY_LIMIT, DEF_SEARCH_RANGE
from jitx_parts.query_api import ResistorQuery

@dataclass
class InverseDividerConstraints(VoltageDividerConstraints):
    """
    Inverse Voltage Divider Constraints

    Parameters for a voltage divider solver that attempts to solve the inverse relationship of VoltageDividerConstraints.
    Useful for feedback voltage dividers in LDOs or switching converters.
    """
    v_in: Toleranced
    v_out: Toleranced
    current: float
    prec_series: List[float] = field(default_factory=lambda: list(STD_PRECS))
    search_range: float = DEF_SEARCH_RANGE
    min_sources: int = DEF_MIN_SRCS
    query_limit: int = DEF_QUERY_LIMIT
    temp_range: Optional[Toleranced] = None
    base_query: ResistorQuery = field(default_factory=get_default_resistor_query)

    def __post_init__(self):
        self.prec_series = sorted(self.prec_series, reverse=True)
        ensure_sources_limits(self.min_sources, self.query_limit)
        if self.temp_range is None:
            self.temp_range = None  # TODO: Set to min_max(-20.0, 50.0) or user-provided

    def compute_objective(self, rh: Toleranced, rl: Toleranced, hi_dr: Optional[Toleranced] = None, lo_dr: Optional[Toleranced] = None) -> Toleranced:
        """
        Compute the output objective voltage range as a Toleranced based on resistor features.
        Default: Vobj = V-in * (1 + (R-H / R-L))
        """
        if hi_dr is None:
            hi_dr = tol(1.0)
        if lo_dr is None:
            lo_dr = tol(1.0)
        r_hi = rh * hi_dr
        r_lo = rl * lo_dr
        vout = self.v_in * (1.0 + (r_hi / r_lo))
        return vout

    def compute_initial_guess(self) -> (float, float):
        """
        Compute an initial guess for the inverse voltage divider solution.
        Returns (r_hi, r_lo)
        """
        r_hi = (self.v_out.typ - self.v_in.typ) / self.current
        r_lo = self.v_in.typ / self.current
        return r_hi, r_lo 

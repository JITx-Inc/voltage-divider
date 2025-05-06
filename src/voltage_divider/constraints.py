from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union
from .toleranced import Toleranced, tol_exact, tol_percent_symmetric
from .settings import OPERATING_TEMPERATURE
from jitx_parts.query_api import ResistorQuery

# Default values from utils.stanza
STD_PRECS = [20.0, 10.0, 5.0, 2.0, 1.0, 0.5, 0.25, 0.1]  # Percentages, unitless
DEF_MIN_SRCS = 3
DEF_QUERY_LIMIT = 50
DEF_SEARCH_RANGE = 10.0  # Percent, unitless

# Helper for default resistor query
def get_default_resistor_query() -> ResistorQuery:
    """Return a default ResistorQuery instance."""
    return ResistorQuery(mounting="smd", min_stock=10, case=["0603"])

# Helper for ensure-sources-limits
def ensure_sources_limits(min_sources: int, query_limit: int):
    if min_sources > query_limit:
        raise ValueError(f"Min Sources must be less than Query Limit: min-sources={min_sources} query-limit={query_limit}")

@dataclass
class VoltageDividerConstraints:
    """
    Voltage Divider Constraints

    Encapsulates the necessary parameters for the solver as well as other logistics parameters for the generated result.
    This type solves the "forward" voltage divider problem. The input voltage is the `hi` side of the voltage divider and the objective voltage is the middle node (`out`).
    """
    v_in: Toleranced
    v_out: Toleranced
    current: float
    prec_series: List[float] = field(default_factory=lambda: list(STD_PRECS))
    search_range: float = DEF_SEARCH_RANGE
    min_sources: int = DEF_MIN_SRCS
    query_limit: int = DEF_QUERY_LIMIT
    temp_range: Toleranced = OPERATING_TEMPERATURE
    base_query: ResistorQuery = field(default_factory=get_default_resistor_query)

    def __post_init__(self):
        # Sort precision series descending
        self.prec_series = sorted(self.prec_series, reverse=True)
        ensure_sources_limits(self.min_sources, self.query_limit)

    def compute_objective(self, rh: Toleranced, rl: Toleranced, hi_dr: Toleranced = tol_exact(1.0), lo_dr: Toleranced = tol_exact(1.0)) -> Toleranced:
        """
        Compute the output objective voltage range as a Toleranced based on resistor features.
        Default: Vobj = V-in * (R-L / (R-H + R-L))
        """
        r_hi = rh * hi_dr
        r_lo = rl * lo_dr
        vout = self.v_in * r_lo / (r_lo + r_hi)
        return vout

    def is_compliant(self, v_obj: Union[Toleranced, float]) -> bool:
        """
        Check if the computed objective voltage is within the user-defined constraints.
        """
        return self.v_out.in_range(v_obj)

    def compute_loss(self, rh: float, rl: float, precision: float) -> Optional[float]:
        """
        Compute a loss function for a potential solution.
        Returns a positive value if compliant, or None if not a solution.
        """
        rh_tol = tol_percent_symmetric(rh, precision)
        rl_tol = tol_percent_symmetric(rl, precision)
        vo = self.compute_objective(rh_tol, rl_tol)
        if self.is_compliant(vo):
            # This metric is suspect
            #  - It does not consider the span of the output
            #     For example - you could have two configurations:
            #       1.  2.5 +/- 0.1
            #       2.  2.499 +/- 0.01
            #    If the target was 2.5 - then the first would have lower
            #    loss but would not be preferred.
            return abs(self.v_out.typ - vo.typ)
        else:
            return None

    def compute_initial_guess(self) -> Tuple[float, float]:
        """
        Compute an initial guess for the voltage divider solution.
        Returns (r_hi, r_lo)
        """
        r_hi = (self.v_in.typ - self.v_out.typ) / self.current
        r_lo = self.v_out.typ / self.current
        return r_hi, r_lo 

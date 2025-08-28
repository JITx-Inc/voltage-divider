from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

from jitx.toleranced import Toleranced
from jitxlib.parts import ResistorQuery

from .settings import OPERATING_TEMPERATURE

# Default values from utils.stanza
STD_PRECS = [20.0, 10.0, 5.0, 2.0, 1.0, 0.5, 0.25, 0.1]  # Percentages, unitless
DEF_MIN_SRCS = 3
DEF_QUERY_LIMIT = 50
DEF_SEARCH_RANGE = 10.0  # Percent, unitless


# Helper for default resistor query
# FIXME: This should be implemented in query_api.py with setters.
def get_default_resistor_query() -> ResistorQuery:
    """Return a default ResistorQuery instance."""
    return ResistorQuery()


# Helper for ensure-sources-limits
def ensure_sources_limits(min_sources: int, query_limit: int):
    if min_sources > query_limit:
        raise ValueError(
            f"Min Sources must be less than Query Limit: min-sources={min_sources} query-limit={query_limit}"
        )


@dataclass
class VoltageDividerConstraints:
    """
    Voltage Divider Constraints

    This type encapsulates the necessary parameters for the
    solver as well as other logistics parameters for the generated result.

    This type solves the "forward" voltage divider problem. Meaning that the
    input voltage is the `hi` side of the voltage divider and the objective
    voltage we are solving for is the middle node of the voltage divider (`out`).

    This type of solve might be used when building an attenuator where we want
    to keep the output within some toleranced range.

    Args:
        v_in: Input Voltage Range
              This parameter encodes the typical DC voltage
              range for the input.
        v_out: Desired Voltage Output Range
               Construct a voltage divider such that the specified
               input voltage results in a output voltage in this range.
        current: Max current in amps allowed through the divider
        prec_series: Set of precision series to search
                     By default, we search the following series: [0.20, 0.10, 0.05, 0.02, 0.01, 0.005, 0.0025, 0.001]
                     The user can customize this series by pass an overriding series.
        search_range: Set the search range for components to select
                      This algorithm does a pre-screening of resistor values based on
                      the `v-in`, `v-out`, and `current` parameters. Then this
                      parameter limits how far from these pre-screen values we're willing
                      to search to find an acceptable solution.
        min_sources: Set the minimum number of sources
                     When pulling resistors from the database, this algorithm will
                     limit the selection of resistors to only those components
                     for which there are at least `min-sources` number of manufacturers
                     for comparable parts.
                     By default this value is 3.
        query_limit: Query Limiter for Results.
                     For many resistors, there may be 1000's of parts that
                     match a particular query. This parameter limits the
                     number of returned results to some max so as not to
                     overload the parts database. The default value is 50.
                     This value must be greater than the `min-sources`
                     parameter.
        temp_range: Temperature Range for TCR evaluation.
                    Default is 0.0 to 25.0 C.
        base_query: Base ResistorQuery
                    This object allows the user to further fine tune the
                    selected resistors as part of the solver. The global
                    design level defaults will still apply but this can
                    be used to override or add to the query parameters.
                    The `resistance`, `tolerance`, or `precision` keys
                    will be overridden by the solvers so any value
                    in the base query will be ignored for those keys.
    """

    v_in: Toleranced
    v_out: Toleranced
    current: float
    prec_series: List[float] = field(default_factory=lambda: list(STD_PRECS))
    search_range: float = DEF_SEARCH_RANGE
    min_sources: int = DEF_MIN_SRCS
    query_limit: int = DEF_QUERY_LIMIT
    temp_range: Toleranced = OPERATING_TEMPERATURE
    # TODO: Remove base_query and retrieve it from teh DesignContext.
    base_query: ResistorQuery = field(default_factory=get_default_resistor_query)

    def __post_init__(self):
        # Sort precision series descending
        self.prec_series = sorted(self.prec_series, reverse=True)
        ensure_sources_limits(self.min_sources, self.query_limit)

    def compute_objective(
        self,
        rh: Toleranced,
        rl: Toleranced,
        hi_dr: Toleranced = Toleranced.exact(1.0),
        lo_dr: Toleranced = Toleranced.exact(1.0),
    ) -> Toleranced:
        """
        This function computes the objective as the forward voltage of the
        voltage divider. Meaning the middle node of the divider is the output.

        ```
        Vobj = V-in * (R-L / (R-H + R-L))
        ```

        Args:
            rh: The top resistor in the divider.
            rl: The bottom resistor in the divider.
            hi_dr: Delta-Resistance as a Toleranced with a nominal value of 1.0. This value when multiplied
                   against the nominal `hi` resistance value gives the range of resistances expected for the operating
                   temperature range.
            lo_dr: Delta-Resistance as a Toleranced with a nominal value of 1.0. This value when multiplied
                   against the nominal `lo` resistance value gives the range of resistances expected for the operating
                   temperature range.
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
        rh_tol = Toleranced.percent(rh, precision)
        rl_tol = Toleranced.percent(rl, precision)
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

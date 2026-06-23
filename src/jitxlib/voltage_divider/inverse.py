from typing import Tuple

from jitx.toleranced import Toleranced

from .constraints import VoltageDividerConstraints, DEF_DELTA_RESISTANCE


class InverseDividerConstraints(VoltageDividerConstraints):
    """
    Inverse Voltage Divider Constraints

    This type defines the parameters for a voltage divider solver
    that attempts solve the inverse relationship that `VoltageDividerConstraints`.

    This is typically useful for the feedback voltage divider used in
    LDO's or switching converters. For example, an LDO might list specifications
    for the reference voltage as a tolerance over a particular temperature range.
    Then it is our job, as an engineer, to determine what voltage divider would
    cause the output of the LDO to drive a voltage in that range.

    This solver allows the user to spec a `v-out` for the LDO's output voltage
    as the objective and then the feedback reference as a the input voltage. The
    solver will then find the resistor combination with the right precision that
    keeps the LDO's output voltage in the objective range.

    Args:
        v_in: Input Voltage Range
              The inverse divider's "input" is the middle node of the divider.
              This parameter is used to drive the objective voltage.
        v_out: Desired Voltage Output Range
               This is the objective voltage for the solver and for the inverse
               solver, this is the `hi` port voltage of the divider.
        current: Max current in amps allowed through the divider (ie from `hi -> lo`)
                 This value is expected to be positive.
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

    def compute_objective(
        self,
        rh: Toleranced,
        rl: Toleranced,
        hi_dr: Toleranced = DEF_DELTA_RESISTANCE,
        lo_dr: Toleranced = DEF_DELTA_RESISTANCE,
    ) -> Toleranced:
        """
        Default `compute-objective` for inverse divider.

        This function currently computes the objective as the inverse voltage of the
        voltage divider. Meaning the middle node of the divider is the "input" and the
        objective we are solving over is the voltage into the `hi` port of the divider.

        Args:
            rh: The top resistor in the divider.
            rl: The bottom resistor in the divider.
            hi_dr: Delta-Resistance as a Toleranced with a nominal value of 1.0. This value when multiplied
                   against the nominal `hi` resistance value gives the range of resistances expected for the operating
                   temperature range.
            lo_dr: Delta-Resistance as a Toleranced with a nominal value of 1.0. This value when multiplied
                   against the nominal `lo` resistance value gives the range of resistances expected for the operating
                   temperature range.
        ```
        Vobj = V-in ( 1 + (R-H / R-L)
        ```
        """
        r_hi = rh * hi_dr
        r_lo = rl * lo_dr
        vout = self.v_in * (1.0 + (r_hi / r_lo))
        return vout

    def compute_initial_guess(self) -> Tuple[float, float]:
        """
        Compute an initial guess for the inverse voltage divider solution.
        Returns (r_hi, r_lo)
        """
        r_hi = (self.v_out.typ - self.v_in.typ) / self.current
        r_lo = self.v_in.typ / self.current
        return r_hi, r_lo

from dataclasses import dataclass
from logging import getLogger
from typing import Any, List, Optional, Tuple, cast

from jitx.toleranced import Toleranced
from jitxlib.parts import search_resistors, ExistKeys, DistinctKey, ResistorQuery
from jitxlib.parts.query_api import to_component

from .constraints import VoltageDividerConstraints
from .errors import (
    NoPrecisionSatisfiesConstraintsError,
    VinRangeTooLargeError,
    IncompatibleVinVoutError,
    NoSolutionFoundError,
)


logger = getLogger(__name__)


@dataclass(frozen=True)
class _ResistorData:
    """Resistor parameters the solver needs from a parts-database entry."""

    resistance: float
    mpn: str
    tolerance: Optional[Tuple[float, float]]  # (min, max)
    tcr: Optional[Tuple[float, float]]  # (pos, neg)


@dataclass
class ResistorSelection:
    """A resistor chosen by the solver.

    Carries a resolved ``ResistorQuery`` pinned to the exact part (by MPN, with
    resistance and precision) so the circuit can instantiate it through the
    public ``jitxlib.parts.Resistor`` factory.
    """

    resistance: float
    mpn: str
    query: ResistorQuery


@dataclass
class VoltageDividerSolution:
    """
    Voltage Divider Solution Type
    """

    R_h: ResistorSelection
    R_l: ResistorSelection
    vo: Toleranced


@dataclass
class Ratio:
    high: float
    low: float
    loss: float


def solve(constraints: VoltageDividerConstraints) -> VoltageDividerSolution:
    """
    Solve the Voltage Divider Constraint Problem.
    """
    search_prec = constraints.search_range
    goals = constraints.compute_initial_guess()
    for g in goals:
        if g < 0.0:
            raise IncompatibleVinVoutError(constraints.v_in, constraints.v_out)
    goal_r_hi, goal_r_lo = goals
    # Screen the input voltage requirement with perfect resistors
    vin_screen = constraints.compute_objective(
        Toleranced.exact(goal_r_hi), Toleranced.exact(goal_r_lo)
    )
    if not constraints.is_compliant(vin_screen):
        raise VinRangeTooLargeError(goals, vin_screen)
    # Pre-screen precision series
    pre_screen = []
    for std_prec in constraints.prec_series:
        vo = constraints.compute_objective(
            Toleranced.percent(goal_r_hi, std_prec),
            Toleranced.percent(goal_r_lo, std_prec),
        )
        pre_screen.append((constraints.is_compliant(vo), std_prec, vo))
    first_valid_series = next((i for i, elem in enumerate(pre_screen) if elem[0]), None)
    if first_valid_series is not None:
        series = constraints.prec_series[first_valid_series:]
    else:
        raise NoPrecisionSatisfiesConstraintsError(goals, pre_screen)
    # Try to solve for each valid precision
    for std_prec in series:
        logger.debug("Trying precision %s%%", std_prec)
        sol = solve_over_series(constraints, std_prec, search_prec)
        if sol is not None:
            return sol
    raise NoSolutionFoundError(
        "Failed to Source Resistors to Satisfy Voltage Divider Constraints"
    )


def solve_over_series(
    constraints: VoltageDividerConstraints, precision: float, search_prec: float
) -> Optional[VoltageDividerSolution]:
    goal_r_hi, goal_r_lo = constraints.compute_initial_guess()
    hi_res = query_resistance_by_values(constraints, goal_r_hi, precision, search_prec)
    lo_res = query_resistance_by_values(constraints, goal_r_lo, precision, search_prec)
    for ratio in sort_pairs_by_best_fit(constraints, precision, hi_res, lo_res):
        sol = filter_query_results(constraints, ratio, precision)
        if sol is not None:
            return sol
    return None


def filter_query_results(
    constraints: VoltageDividerConstraints, ratio: Ratio, precision: float
) -> Optional[VoltageDividerSolution]:
    logger.debug("Querying resistors for R-h=%s ohm R-l=%s ohm", ratio.high, ratio.low)
    r_his = query_resistors(constraints, ratio.high, precision)
    r_los = query_resistors(constraints, ratio.low, precision)
    min_srcs = constraints.min_sources
    if len(r_his) < min_srcs or len(r_los) < min_srcs:
        logger.debug(
            "Ignoring candidate: there must be at least %s resistors of each type",
            min_srcs,
        )
        return None
    r_hi_cmp = r_his[0]
    r_lo_cmp = r_los[0]
    vo_set = study_solution(constraints, r_hi_cmp, r_lo_cmp, constraints.temp_range)
    vo_valids = [constraints.is_compliant(vo) for vo in vo_set]
    is_valid = all(vo_valids)
    if not is_valid:
        logger.debug("Ignoring candidate: not a solution when taking TCRs into account")

        def fmt(ok, vo):
            return "OK" if ok else f"FAIL ({vo} V)"

        logger.debug("min-temp: %s", fmt(vo_valids[0], vo_set[0]))
        logger.debug("max-temp: %s", fmt(vo_valids[1], vo_set[1]))
        return None
    # TODO: Compute the worst case v-out here and use that instead of just the first
    worst_case_vo = vo_set[0]
    mpn1 = r_hi_cmp.mpn
    mpn2 = r_lo_cmp.mpn
    vout_str = f"({vo_set[0]}, {vo_set[1]})V" if len(vo_set) > 1 else f"({vo_set[0]})V"
    try:
        current = vo_set[0].typ / ratio.low
    except Exception:
        current = "unknown"
    logger.info(
        "Solved: mpn1=%s, mpn2=%s, v-out=%s, current=%sA",
        mpn1,
        mpn2,
        vout_str,
        current,
    )
    return VoltageDividerSolution(
        _select(r_hi_cmp, constraints.base_query, precision),
        _select(r_lo_cmp, constraints.base_query, precision),
        worst_case_vo,
    )


def sort_pairs_by_best_fit(
    constraints: VoltageDividerConstraints,
    precision: float,
    hi_res: List[float],
    lo_res: List[float],
) -> List[Ratio]:
    ratios = []
    for rh in hi_res:
        for rl in lo_res:
            loss = constraints.compute_loss(rh, rl, precision)
            if loss is not None:
                ratios.append(Ratio(rh, rl, loss))
    ratios.sort(key=lambda r: r.loss)
    return ratios


def query_resistance_by_values(
    constraints: VoltageDividerConstraints,
    goal_r: float,
    r_prec: float,
    min_prec: float,
) -> List[float]:
    """
    Query for resistance values within the specified precision range using search_resistors.
    Returns a list of resistance values (float).
    """

    def to_float(r: object) -> float:
        if not isinstance(r, int | float):
            raise ValueError(
                f"Expected returned resistance value from database to be an int|float, got {type(r)}: {r}"
            )
        return float(r)

    # Use search_resistors with distinct resistance
    exist_keys = ExistKeys(["tcr_pos", "tcr_neg"])
    distinct_key = DistinctKey("resistance")
    base_query = constraints.base_query
    resistances = search_resistors(
        base_query,
        resistance=Toleranced.percent(goal_r, min_prec),
        precision=r_prec / 100.0,
        exist=exist_keys,
        distinct=distinct_key,
    )
    # Case from int to float (mimic stanza codebase, the database is sensitive to the difference, maybe due to caching).
    return [to_float(r) for r in resistances]


def query_resistors(
    constraints: VoltageDividerConstraints, target: float, prec: float
) -> List[_ResistorData]:
    """
    Query for resistors matching a particular target resistance and precision.
    Returns the parameters the solver needs (resistance, mpn, tolerance, tcr).
    """

    exist_keys = ExistKeys(["tcr_pos", "tcr_neg"])
    base_query = constraints.base_query
    results = search_resistors(
        base_query,
        resistance=target,
        precision=prec / 100.0,
        exist=exist_keys,
        limit=constraints.min_sources,
    )
    out: List[_ResistorData] = []
    for r in results:
        # `to_component` (public, from query_api) parses a parts-db row into a
        # dataclass; read its fields through a cast so we depend only on the
        # public function and not on the private result type.
        c = cast(Any, to_component(r))
        tol = c.tolerance
        tcr = c.tcr
        out.append(
            _ResistorData(
                resistance=float(c.resistance),
                mpn=str(c.mpn),
                tolerance=(tol.min, tol.max) if tol is not None else None,
                tcr=(tcr.pos, tcr.neg) if tcr is not None else None,
            )
        )
    return out


def _select(
    chosen: _ResistorData, base_query: ResistorQuery, precision: float
) -> ResistorSelection:
    """
    Build a resolved query pinned to the exact validated part so the circuit
    instantiates the precise resistor whose TCR/tolerance the solver checked.
    """
    query = base_query.update(
        mpn=chosen.mpn, resistance=chosen.resistance, precision=precision / 100.0
    )
    return ResistorSelection(chosen.resistance, chosen.mpn, query)


def study_solution(
    constraints: VoltageDividerConstraints,
    r_hi: _ResistorData,
    r_lo: _ResistorData,
    temp_range: Toleranced,
) -> List[Toleranced]:
    """
    Compute the voltage divider expected output over a temperature range.
    Returns a list of Toleranced values for [min_temp, max_temp].
    """

    if r_lo.resistance == 0.0 and r_hi.resistance == 0.0:
        raise ValueError(
            f"Can't check output voltage current for a solution with two zero ohm resistors {r_lo.mpn} and {r_hi.mpn}."
        )

    # Compute TCR deviations for min and max temperature
    lo_drs = [
        compute_tcr_deviation(r_lo, temp_range.min_value),
        compute_tcr_deviation(r_lo, temp_range.max_value),
    ]
    hi_drs = [
        compute_tcr_deviation(r_hi, temp_range.min_value),
        compute_tcr_deviation(r_hi, temp_range.max_value),
    ]
    r_lo_val = get_resistance(r_lo)
    r_hi_val = get_resistance(r_hi)
    results = []
    for lo_dr, hi_dr in zip(lo_drs, hi_drs, strict=True):
        if lo_dr is not None and hi_dr is not None:
            vout = constraints.compute_objective(r_hi_val, r_lo_val, hi_dr, lo_dr)
            results.append(vout)
        else:
            raise ValueError("No TCR Data")
    return results


def get_resistance(r: _ResistorData) -> Toleranced:
    """
    Get the resistance value as a Toleranced.
    Combines the nominal resistance with the (min, max) tolerance band.
    Raises an error if tolerance is None.
    """
    if r.tolerance is None:
        raise ValueError(
            "Resistor tolerance must be specified (min, max). None is not allowed."
        )
    return tol_minmax(r.resistance, r.tolerance)


def tol_minmax(typ: float, tolerance: Tuple[float, float]) -> Toleranced:
    """
    Create a Toleranced value from a (min, max) tolerance band.
    Mirrors the Stanza implementation:
    tol(v, tolerance:MinMaxRange):
      coeff = min-max(1.0 + min(tolerance), 1.0 + max(tolerance))
      v * coeff
    """
    tol_min, tol_max = tolerance
    coeff = Toleranced.min_max(1.0 + tol_min, 1.0 + tol_max)
    return typ * coeff


def compute_tcr_deviation(
    resistor: _ResistorData, temperature: float
) -> Optional[Toleranced]:
    """
    Compute the expected deviation window of a given resistor at a given temperature.

    This function mirrors the Stanza implementation in component-types.stanza:
    - Extracts tcr and reference temperature from the resistor.
    - Converts pos/neg to a Toleranced interval using Toleranced.min_max.
    - Calls compute_tcr_deviation_interval.
    - Returns None if tcr is not present.

    NOTE: This includes a workaround for known database issues with TCR values,
    as described in the Stanza code and PROD-328.
    """
    tcr = resistor.tcr
    ref_temp = 25.0  # Default reference temperature
    if tcr is None:
        return None
    # This mirrors the Stanza hack for database issues:
    # See: https://linear.app/jitx/issue/PROD-328/tcr-values-in-database-seem-wrong
    p, n = tcr
    tcr_interval = Toleranced.min_max(min(p, n), max(p, n))
    return compute_tcr_deviation_interval(tcr_interval, temperature, ref_temp)


def compute_tcr_deviation_interval(
    tcr: Toleranced, temperature: float, ref_temp: float = 25.0
) -> Toleranced:
    """
    Compute the expected deviation window of a given temperature coefficient.

    This function mirrors the Stanza implementation:
    - Returns 1.0 + (diff * tcr), where diff = temperature - ref_temp.
    - The result is a Toleranced window for the deviation (typically ~0.9 to 1.1).
    """
    diff = temperature - ref_temp
    return 1.0 + (diff * tcr)

from dataclasses import dataclass
from typing import List, Optional

from jitx.toleranced import Toleranced
from jitxlib.parts import search_resistors, ExistKeys, DistinctKey
from jitxlib.parts._types.main import to_component, PartJSON
from jitxlib.parts._types.component import MinMax
from jitxlib.parts._types.resistor import Resistor

from .constraints import VoltageDividerConstraints
from .errors import (
    NoPrecisionSatisfiesConstraintsError,
    VinRangeTooLargeError,
    IncompatibleVinVoutError,
    NoSolutionFoundError,
)


@dataclass
class VoltageDividerSolution:
    """
    Voltage Divider Solution Type
    """

    R_h: Resistor
    R_l: Resistor
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
        print(f"-> Precision {std_prec}%")
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
    print(f"    - Querying resistors for R-h={ratio.high}Ω R-l={ratio.low}Ω")
    r_his = query_resistors(constraints, ratio.high, precision)
    r_los = query_resistors(constraints, ratio.low, precision)
    min_srcs = constraints.min_sources
    if len(r_his) < min_srcs or len(r_los) < min_srcs:
        print(
            f"      Ignoring: there must be at least {min_srcs} resistors of each type"
        )
        return None
    r_hi_cmp = r_his[0]
    r_lo_cmp = r_los[0]
    vo_set = study_solution(constraints, r_hi_cmp, r_lo_cmp, constraints.temp_range)
    vo_valids = [constraints.is_compliant(vo) for vo in vo_set]
    is_valid = all(vo_valids)
    if not is_valid:
        print("      Ignoring: not a solution when taking into account TCRs.")

        def fmt(ok, vo):
            return "OK" if ok else f"FAIL ({vo} V)"

        print(f"        min-temp: {fmt(vo_valids[0], vo_set[0])}")
        print(f"        max-temp: {fmt(vo_valids[1], vo_set[1])}")
        return None
    # TODO: Compute the worst case v-out here and use that instead of just the first
    worst_case_vo = vo_set[0]
    # Print solution found
    mpn1 = r_hi_cmp.mpn
    mpn2 = r_lo_cmp.mpn
    vout_str = f"({vo_set[0]}, {vo_set[1]})V" if len(vo_set) > 1 else f"({vo_set[0]})V"
    try:
        current = vo_set[0].typ / ratio.low
    except Exception:
        current = "unknown"
    print(
        f"      Solved: mpn1={mpn1}, mpn2={mpn2}, v-out={vout_str}, current={current}A"
    )
    return VoltageDividerSolution(r_hi_cmp, r_lo_cmp, worst_case_vo)


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

    def to_float(r: PartJSON) -> float:
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
) -> List[Resistor]:
    """
    Query for resistors matching a particular target resistance and precision.
    Returns a list of Resistor objects.
    """

    def to_resistor(r: PartJSON) -> Resistor:
        c = to_component(r)
        if not isinstance(c, Resistor):
            raise ValueError(f"Expected Resistor, got {type(c)}: {c}")
        return c

    exist_keys = ExistKeys(["tcr_pos", "tcr_neg"])
    base_query = constraints.base_query
    results = search_resistors(
        base_query,
        resistance=target,
        precision=prec / 100.0,
        exist=exist_keys,
        limit=constraints.min_sources,
    )
    # Convert results to Resistor objects
    return [to_resistor(r) for r in results]


def study_solution(
    constraints: VoltageDividerConstraints,
    r_hi: Resistor,
    r_lo: Resistor,
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


def get_resistance(r: Resistor) -> Toleranced:
    """
    Get the resistance value as a Toleranced.
    Uses the internal information of the Resistor component object to construct the resistance value with tolerances.
    Raises an error if tolerance is None. Always expects MinMax for tolerance.
    """
    if r.tolerance is None:
        raise ValueError(
            "Resistor tolerance must be specified (MinMax). None is not allowed."
        )
    return tol_minmax(r.resistance, r.tolerance)


def tol_minmax(typ: float, tolerance: MinMax) -> Toleranced:
    """
    Create a Toleranced value from the MinMax range.
    Mirrors the Stanza implementation:
    tol(v, tolerance:MinMaxRange):
      coeff = min-max(1.0 + min(tolerance), 1.0 + max(tolerance))
      v * coeff
    """
    coeff = Toleranced.min_max(1.0 + tolerance.min, 1.0 + tolerance.max)
    return typ * coeff


def compute_tcr_deviation(
    resistor: Resistor, temperature: float
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
    p, n = tcr.pos, tcr.neg
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

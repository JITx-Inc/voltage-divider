from dataclasses import dataclass
from typing import Any, List, Optional
from src.voltage_divider.toleranced import Toleranced, tol
from src.voltage_divider.constraints import VoltageDividerConstraints
from jitx_parts.query_api import search_resistors, ExistKeys, DistinctKey
from jitx_parts.types.main import to_component
from jitx_parts.types.component import Part, MinMax
from jitx_parts.types.resistor import Resistor

# TODO: Implement or import these error classes
class NoPrecisionSatisfiesConstraintsError(Exception): pass
class VinRangeTooLargeError(Exception): pass
class IncompatibleVinVoutError(Exception): pass
class NoSolutionFoundError(Exception): pass

@dataclass
class VoltageDividerSolution:
    """
    Voltage Divider Solution Type
    """
    R_h: Any  # Resistor object
    R_l: Any  # Resistor object
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
    vin_screen = constraints.compute_objective(tol(goal_r_hi, 0.0), tol(goal_r_lo, 0.0))
    if not constraints.is_compliant(vin_screen):
        raise VinRangeTooLargeError(goals, vin_screen)
    # Pre-screen precision series
    pre_screen = []
    for std_prec in constraints.prec_series:
        vo = constraints.compute_objective(tol(goal_r_hi, std_prec), tol(goal_r_lo, std_prec))
        pre_screen.append((constraints.is_compliant(vo), std_prec, vo))
    first_valid_series = next((i for i, elem in enumerate(pre_screen) if elem[0]), None)
    if first_valid_series is not None:
        series = constraints.prec_series[first_valid_series:]
    else:
        raise NoPrecisionSatisfiesConstraintsError(goals, pre_screen)
    # Try to solve for each valid precision
    for std_prec in series:
        sol = solve_over_series(constraints, std_prec, search_prec)
        if sol is not None:
            return sol
    raise NoSolutionFoundError("Failed to Source Resistors to Satisfy Voltage Divider Constraints")

def solve_over_series(constraints: VoltageDividerConstraints, precision: float, search_prec: float) -> Optional[VoltageDividerSolution]:
    goal_r_hi, goal_r_lo = constraints.compute_initial_guess()
    hi_res = query_resistance_by_values(constraints, goal_r_hi, precision, search_prec)
    lo_res = query_resistance_by_values(constraints, goal_r_lo, precision, search_prec)
    for ratio in sort_pairs_by_best_fit(constraints, precision, hi_res, lo_res):
        sol = filter_query_results(constraints, ratio, precision)
        if sol is not None:
            return sol
    return None

def filter_query_results(constraints: VoltageDividerConstraints, ratio: Ratio, precision: float) -> Optional[VoltageDividerSolution]:
    r_his = query_resistors(constraints, ratio.high, precision)
    r_los = query_resistors(constraints, ratio.low, precision)
    min_srcs = constraints.min_sources
    if len(r_his) < min_srcs or len(r_los) < min_srcs:
        return None
    r_hi_cmp = r_his[0]
    r_lo_cmp = r_los[0]
    vo_set = study_solution(constraints, r_hi_cmp, r_lo_cmp, constraints.temp_range)
    vo_valids = [constraints.is_compliant(vo) for vo in vo_set]
    is_valid = all(vo_valids)
    if not is_valid:
        return None
    # TODO: Compute the worst case v-out here and use that instead of just the first
    worst_case_vo = vo_set[0]
    return VoltageDividerSolution(r_hi_cmp, r_lo_cmp, worst_case_vo)

def sort_pairs_by_best_fit(constraints: VoltageDividerConstraints, precision: float, hi_res: List[float], lo_res: List[float]) -> List[Ratio]:
    ratios = []
    for rh in hi_res:
        for rl in lo_res:
            loss = constraints.compute_loss(rh, rl, precision)
            if loss is not None:
                ratios.append(Ratio(rh, rl, loss))
    ratios.sort(key=lambda r: r.loss)
    return ratios

def query_resistance_by_values(constraints: VoltageDividerConstraints, goal_r: float, r_prec: float, min_prec: float) -> List[float]:
    """
    Query for resistance values within the specified precision range using search_resistors.
    Returns a list of resistance values (float).
    """
    # Use search_resistors with distinct resistance
    exist_keys = ExistKeys(["tcr_pos", "tcr_neg"])
    distinct_key = DistinctKey("resistance")
    base_query = constraints.base_query
    results = search_resistors(
        base_query,
        resistance=tol(goal_r, min_prec),
        precision=r_prec,
        exist=exist_keys,
        distinct=distinct_key,
        limit=constraints.query_limit
    )
    # Extract resistance values from the results
    return [getattr(r, "resistance", goal_r) for r in results]

def query_resistors(constraints: VoltageDividerConstraints, target: float, prec: float) -> List[Part]:
    """
    Query for resistors matching a particular target resistance and precision.
    Returns a list of Part objects.
    """
    exist_keys = ExistKeys(["tcr_pos", "tcr_neg"])
    base_query = constraints.base_query
    results = search_resistors(
        base_query,
        resistance=target,
        precision=prec,
        exist=exist_keys,
        limit=constraints.query_limit
    )
    # Convert results to Part objects using to_component
    return [to_component(r) for r in results]

def study_solution(constraints: VoltageDividerConstraints, r_hi: Resistor, r_lo: Resistor, temp_range: Optional[Toleranced]) -> List[Toleranced]:
    """
    Compute the voltage divider expected output over a temperature range.
    Returns a list of Toleranced values for [min_temp, max_temp].
    """
    if temp_range is None:
        # Default to no temperature range
        temp_range = Toleranced(25.0, 0.0, 0.0)
    # Compute TCR deviations for min and max temperature
    lo_drs = [compute_tcr_deviation(r_lo, temp_range.min_value()), compute_tcr_deviation(r_lo, temp_range.max_value())]
    hi_drs = [compute_tcr_deviation(r_hi, temp_range.min_value()), compute_tcr_deviation(r_hi, temp_range.max_value())]
    r_lo_val = get_resistance(r_lo)
    r_hi_val = get_resistance(r_hi)
    results = []
    for lo_dr, hi_dr in zip(lo_drs, hi_drs):
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
    """
    # If tolerance is a MinMax, use min/max, else treat as symmetric
    if r.tolerance is not None:
        t = r.tolerance
        # If t is MinMax, treat as asymmetric
        if isinstance(t, MinMax):
            return tol(r.resistance, abs(t.max * r.resistance), abs(t.min * r.resistance))
        else:
            # Fallback: treat as symmetric
            return tol(r.resistance, abs(t * r.resistance), abs(t * r.resistance))
    else:
        return tol(r.resistance, 0.0, 0.0)

def compute_tcr_deviation(resistor: Resistor, temperature: float, ref_temp: float = 25.0) -> Optional[Toleranced]:
    """
    Compute the expected deviation window of a given resistor at a given temperature.
    Returns a Toleranced window for the deviation (typically ~0.9 to 1.1).
    """
    tcr = resistor.tcr
    if tcr is None:
        return None
    # MinMaxRange in stanza is ResistorTCR in Python
    tcr_tol = Toleranced(0.0, abs(tcr.pos), abs(tcr.neg))
    diff = temperature - ref_temp
    # 1.0 + (diff * tcr) for both + and -
    return Toleranced(1.0, abs(diff * tcr.pos), abs(diff * tcr.neg))

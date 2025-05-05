# voltage_divider Python API

A Python package for voltage divider constraint solving and circuit construction, compatible with JITX and the jitx-parts database.

## Installation

Install via pip (after cloning this repo and its dependencies):

```bash
pip install -e .
```

## Usage

### 1. Define Constraints

```python
from voltage_divider import VoltageDividerConstraints, Toleranced, tol_percent_symmetric

# Define input and output voltages with tolerances
v_in = tol_percent_symmetric(10.0, 1.0)   # 10V +/- 1%
v_out = tol_percent_symmetric(2.5, 5.0)   # 2.5V +/- 5%
current = 50e-6  # 50uA

cxt = VoltageDividerConstraints(v_in=v_in, v_out=v_out, current=current)
```

### 2. Solve for a Voltage Divider

```python
from voltage_divider import solve

solution = solve(cxt)
print("High resistor:", solution.R_h)
print("Low resistor:", solution.R_l)
print("Output voltage (Toleranced):", solution.vo)
```

### 3. Build a Circuit

```python
from voltage_divider import voltage_divider

circuit = voltage_divider(solution, name="MyVoltageDivider")
# The circuit object can be used with JITX for further PCB design and export
```

### 4. One-liner Construction

```python
from voltage_divider import forward_divider

circuit = forward_divider(v_in, v_out, current, name="QuickDivider")
```

### 5. Inverse Divider Example

```python
from voltage_divider import inverse_divider, Toleranced, min_typ_max

v_in = min_typ_max(0.788, 0.8, 0.812)  # Feedback voltage range
v_out = tol_percent_symmetric(3.3, 2.0)  # Output voltage +/- 2%
current = 50e-6

circuit = inverse_divider(v_in, v_out, current, name="FeedbackDivider")
```

## API Reference

- `VoltageDividerConstraints`, `InverseDividerConstraints`: Define the problem.
- `solve`: Solve for resistor values.
- `Toleranced`, `tol`, `tol_percent`, etc.: Tolerance helpers.
- `voltage_divider`, `voltage_divider_from_constraints`: Build a circuit from a solution or constraints.
- `forward_divider`, `inverse_divider`: One-liner helpers for common use cases.

## JITX Integration

The returned circuit objects are compatible with JITX and can be used in larger PCB design flows.

## License

See LICENSE file. 

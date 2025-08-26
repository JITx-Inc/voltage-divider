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
from voltage_divider import VoltageDividerConstraints
from jitx.toleranced import Toleranced

# Define input and output voltages with tolerances
v_in = Toleranced.percent(10.0, 1.0)   # 10V +/- 1%
v_out = Toleranced.percent(2.5, 5.0)   # 2.5V +/- 5%
current = 50e-6  # 50uA

cxt = VoltageDividerConstraints(v_in=v_in, v_out=v_out, current=current)
```

### 2. Solve for a Voltage Divider

This code needs to be run within the context of a JITX Design.
Queried parts are cached and can be locked / unlocked per design from the BOM View in VSCode.

```python
from jitx.design import Design
from voltage_divider import solve

class ExampleDesign(Design) :
    def __init__(self) :
        solution = solve(cxt)
        print("High resistor:", solution.R_h)
        print("Low resistor:", solution.R_l)
        print("Output voltage (Toleranced):", solution.vo)
```

Run JITX Design.

### 3. Build a Circuit

```python
from jitx.design import Design
from voltage_divider import voltage_divider

class ExampleDesign(Design) :
    def __init__(self) :
        self.circuit = voltage_divider(solution, name="MyVoltageDivider")
```

Run JITX Design.


### 4. One-liner Construction

```python
from jitx.design import Design
from voltage_divider import forward_divider

class ExampleDesign(Design) :
    def __init__(self) :
        self.circuit = forward_divider(v_in, v_out, current, name="QuickDivider")
```

### 5. Inverse Divider Example

```python
from jitx.design import Design
from voltage_divider import inverse_divider, Toleranced, min_typ_max


class ExampleDesign(Design) :
    def __init__(self) :
        v_in = min_typ_max(0.788, 0.8, 0.812)  # Feedback voltage range
        v_out = Toleranced.percent(3.3, 2.0)  # Output voltage +/- 2%
        current = 50e-6
        self.circuit = inverse_divider(v_in, v_out, current, name="FeedbackDivider")
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

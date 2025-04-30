# Installation

In slm.toml add:
```
voltage-divider = { git = "JITx-Inc/voltage-divider", version = "0.5.0" }
```

# Voltage divider

This project contains an [slm](https://github.com/StanzaOrg/slm)-based library for solving,
constructing, and instantiating resistive dividers in [JITX](https://www.jitx.com/).

## Forward divider

This module will attempt to compute a solution for a forward voltage divider
problem and then construct a voltage divider circuit based on the input and
output specifications.

```
  val cxt = voltage-divider/constraints/VoltageDividerConstraints(
    v-in = 10.0 +/- (1 %),
    v-out = 2.5 +/- (5 %),
    current = 50.0e-6,
    base-query = R-query
  )
    val fb-div-type = voltage-divider/circuits/voltage-divider(cxt)
    public inst fb-div : fb-div-type
    net (fb-div.hi, vout-port)
    net (fb-div.out, IC.buck.feedback)
    net (fb-div.lo, GND)
```

## Inverse divider

This type defines the parameters for a voltage divider solver
that attempts solve the inverse relationship than `VoltageDividerConstraints`.

This is typically useful for the feedback voltage divider used in
LDO's or switching converters. For example, an LDO might list specifications
for the reference voltage as a tolerance over a particular temperature range.
Then it is our job, as an engineer, to determine what voltage divider would
cause the output of the LDO to drive a voltage in that range.

This solver allows the user to spec a `v-out` for the LDO's output voltage
as the objective and then the feedback reference as a the input voltage. The
solver will then find the resistor combination with the right precision that
keeps the LDO's output voltage in the objective range.

```
    val fb-cst = voltage-divider/constraints/InverseDividerConstraints(
      ; Input is the voltage reference of the
      ;   converter
      v-in = min-typ-max(0.438, 0.45, 0.462); the LDO datasheet reference voltage
      v-out = 3.3 +/- (3 %)
      current = 100.0e-6
      base-query = R-query
    )

    val fb-div-type = voltage-divider/circuits/voltage-divider(fb-cst)
    public inst fb-div : fb-div-type
    net (fb-div.hi, vout-port)
    net (fb-div.out, IC.buck.feedback)
    net (fb-div.lo, GND)
```

# Voltage Divider

This project contains an [slm](https://github.com/StanzaOrg/slm)-based library for solving,
constructing, and instantiating resistive dividers in [JITX](https://www.jitx.com/).

Example:

```
  val cxt = VoltageDividerConstraints(
    v-in = 10.0 +/- (1 %),
    v-out = 2.5 +/- (5 %),
    current = 50.0e-6,
    base-query = ResistorQuery(
      mounting = "smd"
      min-stock = 10,
      case = ["0603"]
    )
  )

  val result = solve(cxt)
  println("VOUT: %_" % [vo(result)])
  println("R-high: %_" % [resistance $ R-h(result)])
  println("R-low:  %_" % [resistance $ R-l(result)])

  ; Generates:
  ; VOUT:   Toleranced(2.40097398146147 <= 2.49658935879945 <= 2.59575288143456)
  ; R-high: 165000.0
  ; R-low:  54900.0


```

To instantiate a voltage divider:

```
pcb-module top-level:

  val VoltageDividerConstraints(...)
  inst div : voltage-divider(cxt, name? = One("feedback-div"))

  ; or

  val sol =  VoltageDividerSolution(...)
  inst div : voltage-divider(sol, name? = One("feedback-div"))


  ; or

  inst div : forward-divider(
    v-in = 10.0 +/- (1 %),
    v-out = 2.5 +/- (5 %),
    current = 50.0e-6
  )

```

The `name?` argument is optional but useful when using multiple voltage
dividers in a circuit.

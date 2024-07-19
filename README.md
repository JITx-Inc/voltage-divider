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
  println("R1: %_" % [resistance $ r1(result)])
  println("R2: %_" % [resistance $ r2(result)])

  ; Generates:
  ; VOUT: Toleranced(2.40097398146147 <= 2.49658935879945 <= 2.59575288143456)
  ; R1: 165000.0
  ; R2: 54900.0


```

To instantiate a voltage divider:

```
pcb-module top-level:

  inst div : voltage-divider(cxt, name? = One("feedback-div"))

  ; or

  inst div : voltage-divider(
    v-in = 10.0 +/- (1 %),
    v-out = 2.5 +/- (5 %),
    current = 50.0e-6
  )

```


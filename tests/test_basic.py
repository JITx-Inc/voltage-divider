import argparse
import sys
import unittest

import jitx.run
import jitx._instantiation
from jitx.toleranced import Toleranced

from voltage_divider.circuit import voltage_divider_from_constraints
from voltage_divider.constraints import VoltageDividerConstraints
from voltage_divider.inverse import InverseDividerConstraints
from voltage_divider.solver import solve, NoPrecisionSatisfiesConstraintsError, VinRangeTooLargeError, IncompatibleVinVoutError
from jitx_parts.query_api import ResistorQuery

class TestVoltageDivider(unittest.TestCase):
    port: int

    def setUp(self):
        jitx.run.set_websocket_uri("localhost", TestVoltageDivider.port)

    def test_basic_solver(self):
        exp_vout = Toleranced.percent(2.5, 5.0)
        cxt = VoltageDividerConstraints(
            v_in=Toleranced.percent(10.0, 1.0),
            v_out=exp_vout,
            current=50.0e-6,
            temp_range=Toleranced.min_max(-20.0, 50.0),
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"])
        )
        result = solve(cxt)
        self.assertTrue(exp_vout.in_range(result.vo))
        self.assertTrue(Toleranced(165.0e3, 10.0e3).in_range(result.R_h.resistance))
        self.assertTrue(Toleranced(55.0e3, 10.0e3).in_range(result.R_l.resistance))

    def test_fail_case_1(self):
        cxt = VoltageDividerConstraints(
            v_in=Toleranced.percent(10.0, 1.0),
            v_out=Toleranced.percent(12.5, 1.0),
            current=50.0e-6,
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"])
        )
        with self.assertRaises(IncompatibleVinVoutError) as cm:
            with jitx._instantiation.instantiation.activate():
                solve(cxt)
        self.assertIn("Incompatible", str(cm.exception))

    def test_fail_case_2(self):
        cxt = VoltageDividerConstraints(
            v_in=Toleranced.percent(10.0, 10.0),
            v_out=Toleranced.percent(2.5, 0.1),
            current=50.0e-6,
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"])
        )
        with self.assertRaises(VinRangeTooLargeError) as cm:
            with jitx._instantiation.instantiation.activate():
                solve(cxt)
        self.assertIn("Range is too large", str(cm.exception))

    def test_fail_case_3(self):
        cxt = VoltageDividerConstraints(
            v_in=Toleranced.percent(10.0, 1.0),
            v_out=Toleranced.percent(2.5, 5.0),
            current=50.0e-6,
            prec_series=[20.0, 10.0, 5.0],
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"])
        )
        with self.assertRaises(NoPrecisionSatisfiesConstraintsError) as cm:
            with jitx._instantiation.instantiation.activate():
                solve(cxt)
        self.assertIn("No Precision Series", str(cm.exception))

    def test_inverse_divider(self):
        exp_vout = Toleranced.percent(3.3, 2.0)
        cxt = InverseDividerConstraints(
            v_in=Toleranced.min_typ_max(0.788, 0.8, 0.812),
            v_out=exp_vout,
            current=50.0e-6,
            temp_range=Toleranced.min_max(-20.0, 50.0),
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0402"])
        )
        with jitx._instantiation.instantiation.activate():
            result = solve(cxt)
        self.assertTrue(exp_vout.in_range(result.vo))
        self.assertTrue(Toleranced(45.0e3, 10.0e3).in_range(result.R_h.resistance))
        self.assertTrue(Toleranced(14.0e3, 5.0e3).in_range(result.R_l.resistance))

    def test_inverse_divider_circuit(self):
        cxt = InverseDividerConstraints(
            v_in=Toleranced.min_typ_max(0.788, 0.8, 0.812),
            v_out=Toleranced.percent(3.3, 2.0),
            current=50.0e-6,
            temp_range=Toleranced.min_max(-20.0, 50.0),
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0402"])
        )
        with jitx._instantiation.instantiation.activate():
            circuit = voltage_divider_from_constraints(cxt, name="test_inverse_divider_circuit")
        build_design(circuit, "test_inverse_divider_circuit")

def build_design(circuit: jitx.Circuit, design_name: str):
    """Build a design from a component and send it to the web socket.

    Args:
        circuit: The circuit to build the design from
        design_name: The name of the design
    """

    class QueryStackup(jitx.stackup.Stackup):
        layers = [
            jitx.stackup.Layer(jitx.stackup.Dielectric(), thickness=0.1),
            jitx.stackup.Layer(jitx.stackup.Conductor(), thickness=0.1),
            jitx.stackup.Layer(jitx.stackup.Dielectric(), thickness=0.1),
            jitx.stackup.Layer(jitx.stackup.Conductor(), thickness=0.1),
            jitx.stackup.Layer(jitx.stackup.Dielectric(), thickness=0.1),
        ]

    class QueryRules(jitx.substrate.FabricationConstraints):
        min_copper_width = 0.127
        min_copper_copper_space = 0.127
        min_copper_hole_space = 0.127
        min_copper_edge_space = 0.127

        min_annular_ring = 0.127
        min_drill_diameter = 0.127
        min_silkscreen_width = 0.127
        min_pitch_leaded = 0.127
        min_pitch_bga = 0.127

        max_board_width = 0.127
        max_board_height = 0.127

        min_silk_solder_mask_space = 0.127
        min_silkscreen_text_height = 0.127
        solder_mask_registration = 0.127
        min_soldermask_opening = 0.127
        min_soldermask_bridge = 0.127

        min_th_pad_expand_outer = 0.127
        min_hole_to_hole = 0.127
        min_pth_pin_solder_clearance = 0.127

    class QuerySubstrate(jitx.substrate.Substrate):
        stackup = QueryStackup()
        rules = QueryRules()

    class QueryBoard(jitx.Board):
        shape = jitx.shapes.primitive.Circle(radius=5)

    # Create a dynamic class name based on the component name
    DesignClass = type(
        f"{design_name}",
        (jitx.Design,),
        {"substrate": QuerySubstrate(), "board": QueryBoard(), "main": circuit},
    )

    jitx.run.build(
        name=design_name, design=DesignClass, formatter=text_formatter, dump=f"{design_name}.json"
    )

def text_formatter(ob, file=sys.stdout, indent=0):
    # not great but better than nothing, could use yaml or something.
    ind = "  " * indent
    if isinstance(ob, dict):
        for key, value in ob.items():
            if isinstance(value, (list, dict)):
                print(ind + key + ":", file=file)
                text_formatter(value, file, indent + 1)
            else:
                print(ind + key + ":" + " " + str(value), file=file)
    elif isinstance(ob, list):
        if not ob:
            print(ind + "[]", file=file)
        for el in ob:
            if isinstance(el, (list, dict)):
                text_formatter(el, file, indent + 1)
            else:
                text_formatter(el, file, indent)
    else:
        print(ind + str(ob), file=file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="WebSocket port number")
    args, unittest_args = parser.parse_known_args()

    # Set the port in the test class
    TestVoltageDivider.port = args.port

    # Run unittest with remaining arguments
    unittest.main(argv=sys.argv[:1] + unittest_args)

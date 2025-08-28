import argparse
import sys
import unittest
import pytest

import jitx.run
import jitx._instantiation
from jitx.toleranced import Toleranced
from jitx.sample import SampleDesign

from jitxlib.voltage_divider.circuit import voltage_divider_from_constraints
from jitxlib.voltage_divider.constraints import VoltageDividerConstraints
from jitxlib.voltage_divider.inverse import InverseDividerConstraints
from jitxlib.voltage_divider.solver import (
    solve,
    NoPrecisionSatisfiesConstraintsError,
    VinRangeTooLargeError,
    IncompatibleVinVoutError,
)
from jitxlib.parts import ResistorQuery


class TestVoltageDivider(unittest.TestCase):
    port: int

    def setUp(self):
        if hasattr(TestVoltageDivider, "port"):
            jitx.run.set_websocket_uri("localhost", TestVoltageDivider.port)

        import jitxlib.parts.commands

        jitxlib.parts.commands.ALLOW_NO_DESIGN_CONTEXT = True

    @pytest.mark.integration
    def test_basic_solver(self):
        exp_vout = Toleranced.percent(2.5, 5.0)
        cxt = VoltageDividerConstraints(
            v_in=Toleranced.percent(10.0, 1.0),
            v_out=exp_vout,
            current=50.0e-6,
            temp_range=Toleranced.min_max(-20.0, 50.0),
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"]),
        )
        with jitx._instantiation.instantiation.activate():
            result = solve(cxt)
        self.assertTrue(exp_vout.in_range(result.vo))
        self.assertTrue(Toleranced(165.0e3, 10.0e3).in_range(result.R_h.resistance))
        self.assertTrue(Toleranced(55.0e3, 10.0e3).in_range(result.R_l.resistance))

    @pytest.mark.integration
    def test_fail_case_1(self):
        cxt = VoltageDividerConstraints(
            v_in=Toleranced.percent(10.0, 1.0),
            v_out=Toleranced.percent(12.5, 1.0),
            current=50.0e-6,
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"]),
        )
        with self.assertRaises(IncompatibleVinVoutError) as cm:
            with jitx._instantiation.instantiation.activate():
                solve(cxt)
        self.assertIn("Incompatible", str(cm.exception))

    @pytest.mark.integration
    def test_fail_case_2(self):
        cxt = VoltageDividerConstraints(
            v_in=Toleranced.percent(10.0, 10.0),
            v_out=Toleranced.percent(2.5, 0.1),
            current=50.0e-6,
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"]),
        )
        with self.assertRaises(VinRangeTooLargeError) as cm:
            with jitx._instantiation.instantiation.activate():
                solve(cxt)
        self.assertIn("Range is too large", str(cm.exception))

    @pytest.mark.integration
    def test_fail_case_3(self):
        cxt = VoltageDividerConstraints(
            v_in=Toleranced.percent(10.0, 1.0),
            v_out=Toleranced.percent(2.5, 5.0),
            current=50.0e-6,
            prec_series=[20.0, 10.0, 5.0],
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"]),
        )
        with self.assertRaises(NoPrecisionSatisfiesConstraintsError) as cm:
            with jitx._instantiation.instantiation.activate():
                solve(cxt)
        self.assertIn("No Precision Series", str(cm.exception))

    @pytest.mark.integration
    def test_inverse_divider(self):
        exp_vout = Toleranced.percent(3.3, 2.0)
        cxt = InverseDividerConstraints(
            v_in=Toleranced.min_typ_max(0.788, 0.8, 0.812),
            v_out=exp_vout,
            current=50.0e-6,
            temp_range=Toleranced.min_max(-20.0, 50.0),
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0402"]),
        )
        with jitx._instantiation.instantiation.activate():
            result = solve(cxt)
        self.assertTrue(exp_vout.in_range(result.vo))
        self.assertTrue(Toleranced(45.0e3, 10.0e3).in_range(result.R_h.resistance))
        self.assertTrue(Toleranced(14.0e3, 5.0e3).in_range(result.R_l.resistance))

    @pytest.mark.integration
    def test_inverse_divider_circuit(self):
        cxt = InverseDividerConstraints(
            v_in=Toleranced.min_typ_max(0.788, 0.8, 0.812),
            v_out=Toleranced.percent(3.3, 2.0),
            current=50.0e-6,
            temp_range=Toleranced.min_max(-20.0, 50.0),
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0402"]),
        )
        with jitx._instantiation.instantiation.activate():
            circuit = voltage_divider_from_constraints(
                cxt, name="test_inverse_divider_circuit"
            )
        build_circuit_from_instance(circuit, "test_inverse_divider_circuit")

    # All tests above are integration tests. Here is an example test that actually runs in CI.
    def test_example_unit_test(self):
        self.assertTrue(True)


def build_circuit_from_instance(instance: jitx.Circuit, name: str):
    """Build a design from a circuit instance and send it to the web socket.

    Args:
        instance: The circuit instance to build the design from
        name: Design name
    """

    class TestDesign(SampleDesign):
        circuit = instance

    TestDesign.__name__ = name

    jitx.run.build(
        name=name, design=TestDesign, formatter=text_formatter, dump=f"{name}.json"
    )


def build_circuit(circ: type[jitx.Circuit], name: str):
    """Build a design from a component and send it to the web socket.

    Args:
        circ: The circuit class to build the design from
        name: Design name
    """

    class TestDesign(SampleDesign):
        circuit = circ()

    TestDesign.__name__ = name

    jitx.run.build(
        name=name, design=TestDesign, formatter=text_formatter, dump=f"{name}.json"
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

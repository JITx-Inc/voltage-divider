import argparse
import sys
import unittest
from voltage_divider.toleranced import tol_percent_symmetric, tol, min_max, min_typ_max, tol_symmetric
from voltage_divider.constraints import VoltageDividerConstraints
from voltage_divider.inverse import InverseDividerConstraints
from voltage_divider.solver import solve, NoPrecisionSatisfiesConstraintsError, VinRangeTooLargeError, IncompatibleVinVoutError
from jitx_parts.query_api import ResistorQuery
import jitx.run

class TestVoltageDivider(unittest.TestCase):
    port: int

    def setUp(self):
        jitx.run.set_websocket_uri("localhost", TestVoltageDivider.port)

    def test_basic_solver(self):
        OPERATING_TEMPERATURE = min_max(-20.0, 50.0)
        exp_vout = tol_percent_symmetric(2.5, 5.0)
        cxt = VoltageDividerConstraints(
            v_in=tol_percent_symmetric(10.0, 1.0),
            v_out=exp_vout,
            current=50.0e-6,
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"])
        )
        result = solve(cxt)
        self.assertTrue(exp_vout.in_range(result.vo))
        print(f"R_H: {result.R_h.resistance}")
        print(f"R_L: {result.R_l.resistance}")
        self.assertTrue(tol_symmetric(165.0e3, 10.0e3).in_range(result.R_h.resistance))
        self.assertTrue(tol_symmetric(55.0e3, 10.0e3).in_range(result.R_l.resistance))

    def test_fail_case_1(self):
        cxt = VoltageDividerConstraints(
            v_in=tol_percent_symmetric(10.0, 1.0),
            v_out=tol_percent_symmetric(12.5, 1.0),
            current=50.0e-6,
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"])
        )
        with self.assertRaises(IncompatibleVinVoutError) as cm:
            solve(cxt)
        self.assertIn("Incompatible", str(cm.exception))

    def test_fail_case_2(self):
        cxt = VoltageDividerConstraints(
            v_in=tol_percent_symmetric(10.0, 10.0),
            v_out=tol_percent_symmetric(2.5, 0.1),
            current=50.0e-6,
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"])
        )
        with self.assertRaises(VinRangeTooLargeError) as cm:
            solve(cxt)
        self.assertIn("Range is too large", str(cm.exception))

    def test_fail_case_3(self):
        cxt = VoltageDividerConstraints(
            v_in=tol_percent_symmetric(10.0, 1.0),
            v_out=tol_percent_symmetric(2.5, 5.0),
            current=50.0e-6,
            prec_series=[20.0, 10.0, 5.0],
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0603"])
        )
        with self.assertRaises(NoPrecisionSatisfiesConstraintsError) as cm:
            solve(cxt)
        self.assertIn("No Precision Series", str(cm.exception))

    def test_inverse_divider(self):
        OPERATING_TEMPERATURE = min_max(-20.0, 50.0)
        exp_vout = tol_percent_symmetric(3.3, 2.0)
        cxt = InverseDividerConstraints(
            v_in=min_typ_max(0.788, 0.8, 0.812),
            v_out=exp_vout,
            current=50.0e-6,
            base_query=ResistorQuery(mounting="smd", min_stock=10, case=["0402"])
        )
        result = solve(cxt)
        self.assertTrue(exp_vout.in_range(result.vo))
        self.assertTrue(tol(45.0e3, 10.0e3).in_range(result.R_h.resistance))
        self.assertTrue(tol(14.0e3, 5.0e3).in_range(result.R_l.resistance))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="WebSocket port number")
    args, unittest_args = parser.parse_known_args()

    # Set the port in the test class
    TestVoltageDivider.port = args.port

    # Run unittest with remaining arguments
    unittest.main(argv=sys.argv[:1] + unittest_args)

import contextlib
import io
import json
import unittest

from wavepilot.cli import main


class CliTests(unittest.TestCase):
    def test_simulation_emits_machine_readable_metrics(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = main([
                "simulate",
                "--text", "CLI integration test",
                "--mcs", "16qam",
                "--snr", "26",
                "--cfo", "31",
                "--timing-offset", "23",
            ])
        self.assertEqual(result, 0)
        report = json.loads(stdout.getvalue())
        self.assertTrue(report["crc_ok"])
        self.assertTrue(report["payload_match"])
        self.assertAlmostEqual(report["cfo_estimate_hz"], 31, delta=1.0)


if __name__ == "__main__":
    unittest.main()

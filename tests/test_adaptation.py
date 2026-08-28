import unittest

from wavepilot import LinkAdapter


class AdaptationTests(unittest.TestCase):
    def test_high_snr_upgrades_and_failures_downgrade(self) -> None:
        adapter = LinkAdapter(current_mcs="qpsk")
        for _ in range(8):
            adapter.update(27.0, True)
        self.assertEqual(adapter.current_mcs, "64qam")
        adapter.update(10.0, False)
        self.assertEqual(adapter.current_mcs, "16qam")
        adapter.update(10.0, False)
        self.assertEqual(adapter.current_mcs, "qpsk")


if __name__ == "__main__":
    unittest.main()


import unittest

import numpy as np

from wavepilot.modulation import hard_bits_from_llrs, qam_llrs, qam_modulate


class ModulationTests(unittest.TestCase):
    def test_all_constellations_round_trip(self) -> None:
        rng = np.random.default_rng(10)
        for bits_per_symbol in (2, 4, 6):
            with self.subTest(bits_per_symbol=bits_per_symbol):
                bits = rng.integers(0, 2, 60 * bits_per_symbol, dtype=np.uint8)
                symbols = qam_modulate(bits, bits_per_symbol)
                recovered = hard_bits_from_llrs(qam_llrs(symbols, bits_per_symbol, 1e-3))
                np.testing.assert_array_equal(recovered, bits)


if __name__ == "__main__":
    unittest.main()


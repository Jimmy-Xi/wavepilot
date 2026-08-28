import unittest

import numpy as np

from wavepilot.coding import convolutional_encode, viterbi_decode


class CodingTests(unittest.TestCase):
    def test_soft_viterbi_round_trip(self) -> None:
        rng = np.random.default_rng(11)
        bits = rng.integers(0, 2, 257, dtype=np.uint8)
        encoded = convolutional_encode(bits)
        llrs = (1.0 - 2.0 * encoded.astype(float)) * 8.0
        llrs[[20, 21, 103]] *= -1
        decoded = viterbi_decode(llrs, bits.size)
        np.testing.assert_array_equal(decoded, bits)


if __name__ == "__main__":
    unittest.main()


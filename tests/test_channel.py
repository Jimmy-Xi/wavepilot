import unittest

import numpy as np

from wavepilot.channel import ChannelConfig, apply_channel


class ChannelTests(unittest.TestCase):
    def test_seed_makes_channel_reproducible(self) -> None:
        signal = np.ones(100, dtype=complex)
        config = ChannelConfig(snr_db=15, cfo_hz=10, multipath=True, seed=99)
        np.testing.assert_array_equal(
            apply_channel(signal, 48_000, config),
            apply_channel(signal, 48_000, config),
        )


if __name__ == "__main__":
    unittest.main()


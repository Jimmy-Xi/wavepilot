import unittest

from wavepilot import ChannelConfig, OFDMModem, apply_channel


class PhyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.modem = OFDMModem()
        self.payload = b"WavePilot end-to-end payload" * 5

    def test_noiseless_round_trip_for_every_mcs(self) -> None:
        for mcs in ("qpsk", "16qam", "64qam"):
            with self.subTest(mcs=mcs):
                tx = self.modem.modulate(self.payload, mcs)
                result = self.modem.demodulate(tx.waveform)
                self.assertTrue(result.crc_ok)
                self.assertEqual(result.payload, self.payload)
                self.assertLess(result.evm_rms, 1e-10)

    def test_synchronization_cfo_and_multipath(self) -> None:
        tx = self.modem.modulate(self.payload, "16qam")
        received = apply_channel(
            tx.waveform,
            self.modem.config.sample_rate,
            ChannelConfig(snr_db=26, cfo_hz=37, timing_offset=31, multipath=True, seed=7),
        )
        result = self.modem.demodulate(received)
        self.assertTrue(result.crc_ok)
        self.assertEqual(result.payload, self.payload)
        self.assertAlmostEqual(result.cfo_estimate_hz, 37, delta=1.0)
        self.assertGreater(result.sync_score, 0.8)


if __name__ == "__main__":
    unittest.main()


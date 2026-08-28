import tempfile
import unittest
from pathlib import Path

from wavepilot import OFDMModem
from wavepilot.audio import from_passband, read_wav, to_passband, write_wav


class AudioTests(unittest.TestCase):
    def test_pcm_wav_round_trip(self) -> None:
        modem = OFDMModem()
        payload = b"16-bit PCM acoustic loopback" * 8
        tx = modem.modulate(payload, "16qam")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame.wav"
            write_wav(path, to_passband(tx.waveform, modem.config), modem.config.sample_rate)
            passband, sample_rate = read_wav(path)
        self.assertEqual(sample_rate, modem.config.sample_rate)
        result = modem.demodulate(from_passband(passband, modem.config))
        self.assertTrue(result.crc_ok)
        self.assertEqual(result.payload, payload)


if __name__ == "__main__":
    unittest.main()


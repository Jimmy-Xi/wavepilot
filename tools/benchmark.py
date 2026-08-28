#!/usr/bin/env python3
"""Reproducible end-to-end modem latency benchmark."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wavepilot import ChannelConfig, OFDMModem, apply_channel


def main() -> int:
    modem = OFDMModem()
    payload = np.random.default_rng(2026).bytes(1024)

    started = perf_counter()
    tx = modem.modulate(payload, "64qam")
    encoded_at = perf_counter()
    received = apply_channel(
        tx.waveform,
        modem.config.sample_rate,
        ChannelConfig(snr_db=20, cfo_hz=37, timing_offset=31, multipath=True, seed=2026),
    )
    result = modem.demodulate(received)
    finished = perf_counter()

    print(json.dumps({
        "payload_bytes": len(payload),
        "mcs": tx.mcs,
        "crc_ok": result.crc_ok,
        "payload_match": result.payload == payload,
        "waveform_seconds": tx.waveform.size / modem.config.sample_rate,
        "encode_seconds": round(encoded_at - started, 6),
        "channel_and_decode_seconds": round(finished - encoded_at, 6),
        "cfo_error_hz": round(abs(result.cfo_estimate_hz - 37), 6),
        "evm_rms": round(result.evm_rms, 6),
    }, indent=2, sort_keys=True))
    return 0 if result.crc_ok and result.payload == payload else 1


if __name__ == "__main__":
    raise SystemExit(main())


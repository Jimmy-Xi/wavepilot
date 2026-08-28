"""Reproducible link sweeps and machine-readable experiment reports."""

from __future__ import annotations

import statistics

import numpy as np

from .channel import ChannelConfig, apply_channel
from .config import OFDMConfig
from .phy import DecodeError, OFDMModem


def run_snr_sweep(
    snr_values: list[float],
    mcs_values: list[str],
    *,
    trials: int = 10,
    payload_bytes: int = 256,
    multipath: bool = True,
    cfo_hz: float = 25.0,
    seed: int = 2026,
    config: OFDMConfig | None = None,
) -> list[dict[str, float | int | str | None]]:
    if trials < 1 or payload_bytes < 1:
        raise ValueError("trials and payload_bytes must be positive")
    modem = OFDMModem(config)
    rng = np.random.default_rng(seed)
    payload = rng.bytes(payload_bytes)
    report: list[dict[str, float | int | str | None]] = []

    for mcs in mcs_values:
        tx = modem.modulate(payload, mcs)
        duration = tx.waveform.size / modem.config.sample_rate
        for snr_db in snr_values:
            successes = 0
            evm_values: list[float] = []
            cfo_errors: list[float] = []
            for trial in range(trials):
                channel_config = ChannelConfig(
                    snr_db=snr_db,
                    cfo_hz=cfo_hz,
                    timing_offset=17,
                    multipath=multipath,
                    seed=seed + trial,
                )
                received = apply_channel(tx.waveform, modem.config.sample_rate, channel_config)
                try:
                    result = modem.demodulate(received)
                except DecodeError:
                    continue
                successes += int(result.crc_ok and result.payload == payload)
                evm_values.append(result.evm_rms)
                cfo_errors.append(abs(result.cfo_estimate_hz - cfo_hz))
            report.append({
                "mcs": mcs,
                "snr_db": float(snr_db),
                "trials": trials,
                "successes": successes,
                "bler": 1.0 - successes / trials,
                "mean_evm_rms": statistics.fmean(evm_values) if evm_values else 1.0,
                "mean_cfo_error_hz": statistics.fmean(cfo_errors) if cfo_errors else None,
                "offered_payload_bps": payload_bytes * 8 / duration,
                "goodput_bps": payload_bytes * 8 * successes / (trials * duration),
            })
    return report

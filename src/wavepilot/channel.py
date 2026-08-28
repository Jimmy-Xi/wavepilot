"""Deterministic complex-baseband channel models."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray


@dataclass(frozen=True, slots=True)
class ChannelConfig:
    snr_db: float = 30.0
    cfo_hz: float = 0.0
    timing_offset: int = 0
    multipath: bool = False
    burst_probability: float = 0.0
    burst_scale: float = 8.0
    seed: int = 2026

    def validate(self) -> None:
        if self.timing_offset < 0:
            raise ValueError("timing_offset cannot be negative")
        if not 0.0 <= self.burst_probability <= 1.0:
            raise ValueError("burst_probability must be between zero and one")
        if self.burst_scale < 0:
            raise ValueError("burst_scale cannot be negative")


def apply_channel(
    waveform: ArrayLike,
    sample_rate: int,
    config: ChannelConfig | None = None,
) -> NDArray[np.complex128]:
    cfg = config or ChannelConfig()
    cfg.validate()
    signal = np.asarray(waveform, dtype=np.complex128).reshape(-1).copy()
    rng = np.random.default_rng(cfg.seed)

    if cfg.multipath:
        taps = np.zeros(13, dtype=np.complex128)
        taps[0] = 1.0
        taps[4] = 0.34 * np.exp(1j * 0.7)
        taps[11] = 0.18 * np.exp(-1j * 1.1)
        signal = np.convolve(signal, taps)

    if cfg.timing_offset:
        signal = np.concatenate((np.zeros(cfg.timing_offset, dtype=np.complex128), signal))

    if cfg.cfo_hz:
        time = np.arange(signal.size) / sample_rate
        signal *= np.exp(2j * np.pi * cfg.cfo_hz * time)

    power = float(np.mean(np.abs(signal) ** 2))
    noise_variance = power / (10.0 ** (cfg.snr_db / 10.0)) if power else 0.0
    noise = np.sqrt(noise_variance / 2.0) * (
        rng.standard_normal(signal.size) + 1j * rng.standard_normal(signal.size)
    )
    if cfg.burst_probability:
        mask = rng.random(signal.size) < cfg.burst_probability
        noise[mask] += cfg.burst_scale * np.sqrt(max(noise_variance, 1e-15)) * (
            rng.standard_normal(mask.sum()) + 1j * rng.standard_normal(mask.sum())
        )
    return signal + noise


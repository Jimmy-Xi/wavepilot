"""Offline real-passband WAV transport for the complex OFDM waveform."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .config import OFDMConfig


def to_passband(baseband: ArrayLike, config: OFDMConfig | None = None) -> NDArray[np.float64]:
    cfg = config or OFDMConfig()
    signal = np.asarray(baseband, dtype=np.complex128).reshape(-1)
    time = np.arange(signal.size) / cfg.sample_rate
    return np.sqrt(2.0) * np.real(signal * np.exp(2j * np.pi * cfg.carrier_hz * time))


def from_passband(passband: ArrayLike, config: OFDMConfig | None = None) -> NDArray[np.complex128]:
    cfg = config or OFDMConfig()
    signal = np.asarray(passband, dtype=np.float64).reshape(-1)
    time = np.arange(signal.size) / cfg.sample_rate
    mixed = np.sqrt(2.0) * signal * np.exp(-2j * np.pi * cfg.carrier_hz * time)
    frequencies = np.fft.fftfreq(signal.size, d=1.0 / cfg.sample_rate)
    cutoff = cfg.occupied_bandwidth_hz + 2 * cfg.subcarrier_hz
    mask = np.abs(frequencies) <= cutoff
    return np.fft.ifft(np.fft.fft(mixed) * mask).astype(np.complex128)


def write_wav(path: str | Path, passband: ArrayLike, sample_rate: int = 48_000) -> None:
    signal = np.asarray(passband, dtype=np.float64).reshape(-1)
    peak = float(np.max(np.abs(signal))) if signal.size else 0.0
    scaled = signal * (0.9 / peak) if peak > 0 else signal
    pcm = np.clip(np.round(scaled * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(pcm.tobytes())


def read_wav(path: str | Path) -> tuple[NDArray[np.float64], int]:
    with wave.open(str(path), "rb") as stream:
        if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
            raise ValueError("WavePilot expects mono 16-bit PCM WAV")
        sample_rate = stream.getframerate()
        pcm = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2")
    return pcm.astype(np.float64) / 32768.0, sample_rate


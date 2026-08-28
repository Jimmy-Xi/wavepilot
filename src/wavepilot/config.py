"""Physical-layer constants and carrier allocation."""

from __future__ import annotations

from dataclasses import dataclass

MCS_BITS_PER_SYMBOL = {"qpsk": 2, "16qam": 4, "64qam": 6}
MCS_TO_ID = {"qpsk": 0, "16qam": 1, "64qam": 2}
ID_TO_MCS = {value: key for key, value in MCS_TO_ID.items()}


@dataclass(frozen=True, slots=True)
class OFDMConfig:
    """Default 48 kHz acoustic OFDM profile."""

    sample_rate: int = 48_000
    n_fft: int = 256
    cp_len: int = 64
    guard_len: int = 256
    carrier_hz: float = 12_000.0
    active_min: int = -24
    active_max: int = 24
    pilot_carriers: tuple[int, ...] = (-21, -7, 7, 21)
    header_repetitions: int = 2

    def __post_init__(self) -> None:
        if self.n_fft <= 0 or self.n_fft & (self.n_fft - 1):
            raise ValueError("n_fft must be a positive power of two")
        if not 0 < self.cp_len < self.n_fft:
            raise ValueError("cp_len must be between zero and n_fft")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.header_repetitions < 1:
            raise ValueError("header_repetitions must be positive")
        if len(self.data_carriers) * 2 != 88:
            raise ValueError("default header requires exactly 44 data carriers")
        bandwidth = (max(abs(self.active_min), abs(self.active_max)) + 1) * self.subcarrier_hz
        if self.carrier_hz - bandwidth <= 0 or self.carrier_hz + bandwidth >= self.sample_rate / 2:
            raise ValueError("acoustic carrier leaves insufficient Nyquist guard")

    @property
    def active_carriers(self) -> tuple[int, ...]:
        return tuple(
            carrier
            for carrier in range(self.active_min, self.active_max + 1)
            if carrier != 0
        )

    @property
    def data_carriers(self) -> tuple[int, ...]:
        pilots = set(self.pilot_carriers)
        return tuple(carrier for carrier in self.active_carriers if carrier not in pilots)

    @property
    def subcarrier_hz(self) -> float:
        return self.sample_rate / self.n_fft

    @property
    def symbol_samples(self) -> int:
        return self.n_fft + self.cp_len

    @property
    def occupied_bandwidth_hz(self) -> float:
        return max(abs(self.active_min), abs(self.active_max)) * self.subcarrier_hz


def normalize_mcs(name: str) -> str:
    normalized = name.lower().replace("-", "")
    aliases = {"qpsk": "qpsk", "16qam": "16qam", "qam16": "16qam", "64qam": "64qam", "qam64": "64qam"}
    if normalized not in aliases:
        raise ValueError(f"unsupported MCS: {name}")
    return aliases[normalized]


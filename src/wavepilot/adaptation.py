"""Explainable MCS selection under an explicit BLER target."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(slots=True)
class LinkAdapter:
    target_bler: float = 0.1
    hysteresis_db: float = 1.5
    ewma_alpha: float = 0.25
    current_mcs: str = "qpsk"
    smoothed_snr_db: float | None = None
    smoothed_bler: float = 0.0

    _ORDER: ClassVar[tuple[str, ...]] = ("qpsk", "16qam", "64qam")
    _THRESHOLDS: ClassVar[dict[str, float]] = {"qpsk": 7.0, "16qam": 15.0, "64qam": 23.0}

    def __post_init__(self) -> None:
        if not 0 < self.target_bler < 1:
            raise ValueError("target_bler must be between zero and one")
        if self.current_mcs not in self._ORDER:
            raise ValueError("invalid current_mcs")

    def update(self, snr_db: float, block_ok: bool) -> str:
        alpha = self.ewma_alpha
        self.smoothed_snr_db = (
            float(snr_db)
            if self.smoothed_snr_db is None
            else (1 - alpha) * self.smoothed_snr_db + alpha * float(snr_db)
        )
        self.smoothed_bler = (1 - alpha) * self.smoothed_bler + alpha * (0.0 if block_ok else 1.0)

        current_index = self._ORDER.index(self.current_mcs)
        if self.smoothed_bler > self.target_bler and current_index > 0:
            self.current_mcs = self._ORDER[current_index - 1]
            return self.current_mcs

        selected = "qpsk"
        for candidate in self._ORDER:
            required = self._THRESHOLDS[candidate]
            if self.smoothed_snr_db >= required:
                selected = candidate
        selected_index = self._ORDER.index(selected)
        if selected_index > current_index:
            threshold = self._THRESHOLDS[selected]
            if self.smoothed_snr_db < threshold + self.hysteresis_db:
                selected = self.current_mcs
        self.current_mcs = selected
        return selected

    def decision(self) -> dict[str, float | str]:
        return {
            "mcs": self.current_mcs,
            "smoothed_snr_db": self.smoothed_snr_db if self.smoothed_snr_db is not None else float("nan"),
            "smoothed_bler": self.smoothed_bler,
            "target_bler": self.target_bler,
        }

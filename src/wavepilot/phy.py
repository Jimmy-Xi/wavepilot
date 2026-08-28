"""End-to-end synchronized OFDM transmitter and receiver."""

from __future__ import annotations

import binascii
import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .coding import TAIL_BITS, convolutional_encode, viterbi_decode
from .config import ID_TO_MCS, MCS_BITS_PER_SYMBOL, MCS_TO_ID, OFDMConfig, normalize_mcs
from .modulation import nearest_symbols, qam_llrs, qam_modulate

HEADER_MAGIC = 0x5750
HEADER_VERSION = 1
HEADER_BITS = 88
MAX_PAYLOAD_BYTES = 16 * 1024 * 1024


class DecodeError(RuntimeError):
    """Raised when synchronization or the robust header cannot be decoded."""


@dataclass(frozen=True, slots=True)
class TxFrame:
    waveform: NDArray[np.complex128]
    mcs: str
    payload_bytes: int
    coded_bits: int
    ofdm_data_symbols: int
    payload_crc32: int


@dataclass(frozen=True, slots=True)
class RxResult:
    payload: bytes
    crc_ok: bool
    mcs: str
    payload_crc32: int
    calculated_crc32: int
    frame_start: int
    sync_score: float
    cfo_estimate_hz: float
    evm_rms: float
    estimated_snr_db: float
    ofdm_data_symbols: int


def _int_to_bits(value: int, width: int) -> NDArray[np.uint8]:
    return np.array([(value >> shift) & 1 for shift in range(width - 1, -1, -1)], dtype=np.uint8)


def _bits_to_int(bits: ArrayLike) -> int:
    value = 0
    for bit in np.asarray(bits, dtype=np.uint8).reshape(-1):
        value = (value << 1) | int(bit)
    return value


class OFDMModem:
    def __init__(self, config: OFDMConfig | None = None) -> None:
        self.config = config or OFDMConfig()
        self._active = np.array(self.config.active_carriers, dtype=int)
        self._data = np.array(self.config.data_carriers, dtype=int)
        self._pilots = np.array(self.config.pilot_carriers, dtype=int)
        self._preamble = self._build_preamble()
        self._ltf_bins = self._build_ltf_bins()
        self._ltf = self._symbol_from_bins(self._ltf_bins, add_cp=True)

    def _build_preamble(self) -> NDArray[np.complex128]:
        rng = np.random.default_rng(0x57505631)
        carriers = np.array([carrier for carrier in self._active if carrier % 2 == 0], dtype=int)
        bins = np.zeros(self.config.n_fft, dtype=np.complex128)
        bins[carriers % self.config.n_fft] = rng.choice((-1.0, 1.0), size=carriers.size)
        preamble = np.fft.ifft(bins) * self.config.n_fft / np.sqrt(carriers.size)
        if not np.allclose(preamble[: self.config.n_fft // 2], preamble[self.config.n_fft // 2 :]):
            raise AssertionError("Schmidl-Cox preamble must contain repeated halves")
        return preamble.astype(np.complex128)

    def _build_ltf_bins(self) -> NDArray[np.complex128]:
        rng = np.random.default_rng(0x4C544631)
        bins = np.zeros(self.config.n_fft, dtype=np.complex128)
        bins[self._active % self.config.n_fft] = rng.choice((-1.0, 1.0), size=self._active.size)
        return bins

    def _pilot_values(self, symbol_index: int) -> NDArray[np.complex128]:
        base = np.array((1.0, 1.0, 1.0, -1.0), dtype=np.complex128)
        return base * (1.0 if symbol_index % 2 == 0 else -1.0)

    def _symbol_from_bins(self, bins: NDArray[np.complex128], *, add_cp: bool) -> NDArray[np.complex128]:
        if not np.any(bins):
            raise ValueError("OFDM symbol must contain active carriers")
        active_count = self._active.size
        time = np.fft.ifft(bins) * self.config.n_fft / np.sqrt(active_count)
        if add_cp:
            time = np.concatenate((time[-self.config.cp_len :], time))
        return time.astype(np.complex128)

    def _build_data_symbol(self, data_symbols: NDArray[np.complex128], symbol_index: int) -> NDArray[np.complex128]:
        if data_symbols.size != self._data.size:
            raise ValueError("incorrect number of data-carrier symbols")
        bins = np.zeros(self.config.n_fft, dtype=np.complex128)
        bins[self._data % self.config.n_fft] = data_symbols
        bins[self._pilots % self.config.n_fft] = self._pilot_values(symbol_index)
        return self._symbol_from_bins(bins, add_cp=True)

    def _header_bits(self, mcs: str, payload_length: int, payload_crc32: int) -> NDArray[np.uint8]:
        fields = (
            _int_to_bits(HEADER_MAGIC, 16),
            _int_to_bits(HEADER_VERSION, 4),
            _int_to_bits(MCS_TO_ID[mcs], 2),
            _int_to_bits(0, 2),
            _int_to_bits(payload_length, 32),
            _int_to_bits(payload_crc32, 32),
        )
        header = np.concatenate(fields)
        if header.size != HEADER_BITS:
            raise AssertionError("header must fit one QPSK OFDM symbol")
        return header

    def modulate(self, payload: bytes, mcs: str = "qpsk") -> TxFrame:
        selected_mcs = normalize_mcs(mcs)
        if len(payload) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"payload exceeds the {MAX_PAYLOAD_BYTES}-byte safety limit")
        bits_per_symbol = MCS_BITS_PER_SYMBOL[selected_mcs]
        payload_crc = binascii.crc32(payload) & 0xFFFFFFFF

        header_symbols = qam_modulate(self._header_bits(selected_mcs, len(payload), payload_crc), 2)

        payload_bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
        coded = convolutional_encode(payload_bits)
        qam_padding = (-coded.size) % bits_per_symbol
        if qam_padding:
            coded_for_qam = np.pad(coded, (0, qam_padding))
        else:
            coded_for_qam = coded
        mapped = qam_modulate(coded_for_qam, bits_per_symbol)
        carrier_padding = (-mapped.size) % self._data.size
        if carrier_padding:
            mapped = np.pad(mapped, (0, carrier_padding), constant_values=0)
        symbol_matrix = mapped.reshape(-1, self._data.size)
        data_time = [
            self._build_data_symbol(row, index + self.config.header_repetitions)
            for index, row in enumerate(symbol_matrix)
        ]

        parts = [
            np.zeros(self.config.guard_len, dtype=np.complex128),
            self._preamble,
            self._ltf,
        ]
        parts.extend(
            self._build_data_symbol(header_symbols, repetition)
            for repetition in range(self.config.header_repetitions)
        )
        parts.extend(data_time)
        parts.append(np.zeros(self.config.guard_len, dtype=np.complex128))
        waveform = np.concatenate(parts)
        return TxFrame(
            waveform=waveform,
            mcs=selected_mcs,
            payload_bytes=len(payload),
            coded_bits=int(coded.size),
            ofdm_data_symbols=int(symbol_matrix.shape[0]),
            payload_crc32=payload_crc,
        )

    def _synchronize(self, received: NDArray[np.complex128]) -> tuple[int, float, float]:
        length = self.config.n_fft
        if received.size < length:
            raise DecodeError("capture is shorter than the synchronization preamble")
        correlation = np.correlate(received, self._preamble, mode="valid")
        energy = np.convolve(np.abs(received) ** 2, np.ones(length), mode="valid")
        score = np.abs(correlation) / np.sqrt(np.maximum(energy, 1e-15) * np.vdot(self._preamble, self._preamble).real)
        start = int(np.argmax(score))
        best_score = float(score[start])
        if best_score < 0.35:
            raise DecodeError(f"preamble not found (normalized score={best_score:.3f})")
        half = length // 2
        first = received[start : start + half]
        second = received[start + half : start + length]
        phase = float(np.angle(np.vdot(first, second)))
        cfo_hz = phase * self.config.sample_rate / (np.pi * self.config.n_fft)
        return start, best_score, cfo_hz

    def _extract_symbol(self, corrected: NDArray[np.complex128], start: int) -> NDArray[np.complex128]:
        end = start + self.config.symbol_samples
        if end > corrected.size:
            raise DecodeError("capture ended inside an OFDM symbol")
        time = corrected[start + self.config.cp_len : end]
        return np.fft.fft(time)

    def _equalized_data(
        self,
        corrected: NDArray[np.complex128],
        start: int,
        channel: NDArray[np.complex128],
        symbol_index: int,
    ) -> tuple[NDArray[np.complex128], float]:
        spectrum = self._extract_symbol(corrected, start)
        equalized_active = spectrum[self._active % self.config.n_fft] / channel
        active_lookup = {carrier: index for index, carrier in enumerate(self._active)}
        pilot_indices = np.array([active_lookup[int(carrier)] for carrier in self._pilots])
        data_indices = np.array([active_lookup[int(carrier)] for carrier in self._data])
        expected_pilots = self._pilot_values(symbol_index)
        phase = np.angle(np.vdot(expected_pilots, equalized_active[pilot_indices]))
        equalized_active *= np.exp(-1j * phase)
        pilot_error = equalized_active[pilot_indices] - expected_pilots
        noise_variance = float(max(np.mean(np.abs(pilot_error) ** 2), 1e-6))
        return equalized_active[data_indices], noise_variance

    def demodulate(self, waveform: ArrayLike) -> RxResult:
        received = np.asarray(waveform, dtype=np.complex128).reshape(-1)
        frame_start, sync_score, cfo_hz = self._synchronize(received)
        time = np.arange(received.size) / self.config.sample_rate
        corrected = received * np.exp(-2j * np.pi * cfo_hz * time)

        ltf_start = frame_start + self.config.n_fft
        ltf_spectrum = self._extract_symbol(corrected, ltf_start)
        active_reference = self._ltf_bins[self._active % self.config.n_fft]
        channel = ltf_spectrum[self._active % self.config.n_fft] / active_reference
        if np.any(np.abs(channel) < 1e-8):
            raise DecodeError("channel estimate contains a spectral null")

        symbol_start = ltf_start + self.config.symbol_samples
        combined_header_llrs = np.zeros(HEADER_BITS, dtype=np.float64)
        for repetition in range(self.config.header_repetitions):
            equalized, variance = self._equalized_data(
                corrected,
                symbol_start + repetition * self.config.symbol_samples,
                channel,
                repetition,
            )
            combined_header_llrs += qam_llrs(equalized, 2, variance)
        header_bits = (combined_header_llrs < 0).astype(np.uint8)
        magic = _bits_to_int(header_bits[0:16])
        version = _bits_to_int(header_bits[16:20])
        mcs_id = _bits_to_int(header_bits[20:22])
        payload_length = _bits_to_int(header_bits[24:56])
        payload_crc = _bits_to_int(header_bits[56:88])
        if magic != HEADER_MAGIC:
            raise DecodeError(f"header magic mismatch: 0x{magic:04x}")
        if version != HEADER_VERSION:
            raise DecodeError(f"unsupported header version: {version}")
        if mcs_id not in ID_TO_MCS:
            raise DecodeError(f"unsupported MCS id: {mcs_id}")
        if payload_length > MAX_PAYLOAD_BYTES:
            raise DecodeError(f"header payload length exceeds the {MAX_PAYLOAD_BYTES}-byte safety limit")
        mcs = ID_TO_MCS[mcs_id]
        bits_per_symbol = MCS_BITS_PER_SYMBOL[mcs]

        information_bits = payload_length * 8
        coded_bits = 2 * (information_bits + TAIL_BITS)
        qam_symbol_count = math.ceil(coded_bits / bits_per_symbol)
        ofdm_symbol_count = math.ceil(qam_symbol_count / self._data.size)
        data_start = symbol_start + self.config.header_repetitions * self.config.symbol_samples
        llrs: list[NDArray[np.float64]] = []
        equalized_symbols: list[NDArray[np.complex128]] = []
        for index in range(ofdm_symbol_count):
            equalized, variance = self._equalized_data(
                corrected,
                data_start + index * self.config.symbol_samples,
                channel,
                index + self.config.header_repetitions,
            )
            equalized_symbols.append(equalized)
            llrs.append(qam_llrs(equalized, bits_per_symbol, variance))
        all_llrs = np.concatenate(llrs)[:coded_bits]
        decoded_bits = viterbi_decode(all_llrs, information_bits)
        payload = np.packbits(decoded_bits).tobytes()[:payload_length]
        calculated_crc = binascii.crc32(payload) & 0xFFFFFFFF

        used_qam_symbols = np.concatenate(equalized_symbols)[:qam_symbol_count]
        decisions = nearest_symbols(used_qam_symbols, bits_per_symbol)
        error_power = float(np.mean(np.abs(used_qam_symbols - decisions) ** 2))
        reference_power = float(np.mean(np.abs(decisions) ** 2))
        evm = math.sqrt(error_power / max(reference_power, 1e-15))
        estimated_snr = -20.0 * math.log10(max(evm, 1e-12))
        return RxResult(
            payload=payload,
            crc_ok=calculated_crc == payload_crc,
            mcs=mcs,
            payload_crc32=payload_crc,
            calculated_crc32=calculated_crc,
            frame_start=frame_start,
            sync_score=sync_score,
            cfo_estimate_hz=cfo_hz,
            evm_rms=evm,
            estimated_snr_db=estimated_snr,
            ofdm_data_symbols=ofdm_symbol_count,
        )

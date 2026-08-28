"""Gray-coded square QAM mapping and max-log soft demapping."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _gray_to_binary(value: int) -> int:
    result = value
    while value:
        value >>= 1
        result ^= value
    return result


@lru_cache(maxsize=3)
def constellation(bits_per_symbol: int) -> tuple[NDArray[np.complex128], NDArray[np.uint8]]:
    if bits_per_symbol not in (2, 4, 6):
        raise ValueError("bits_per_symbol must be 2, 4 or 6")
    count = 1 << bits_per_symbol
    axis_bits = bits_per_symbol // 2
    axis_size = 1 << axis_bits
    labels = np.array(
        [[(index >> shift) & 1 for shift in range(bits_per_symbol - 1, -1, -1)] for index in range(count)],
        dtype=np.uint8,
    )
    points = np.empty(count, dtype=np.complex128)
    for index, label in enumerate(labels):
        i_gray = int("".join(str(int(bit)) for bit in label[:axis_bits]), 2)
        q_gray = int("".join(str(int(bit)) for bit in label[axis_bits:]), 2)
        i_level = 2 * _gray_to_binary(i_gray) - (axis_size - 1)
        q_level = 2 * _gray_to_binary(q_gray) - (axis_size - 1)
        points[index] = i_level + 1j * q_level
    points /= np.sqrt(np.mean(np.abs(points) ** 2))
    return points, labels


def qam_modulate(bits: ArrayLike, bits_per_symbol: int) -> NDArray[np.complex128]:
    bit_array = np.asarray(bits, dtype=np.uint8).reshape(-1)
    if bit_array.size % bits_per_symbol:
        raise ValueError("bit length must be divisible by bits_per_symbol")
    if np.any(bit_array > 1):
        raise ValueError("bits must contain only zero and one")
    points, _ = constellation(bits_per_symbol)
    grouped = bit_array.reshape(-1, bits_per_symbol)
    weights = 1 << np.arange(bits_per_symbol - 1, -1, -1)
    indices = grouped @ weights
    return points[indices]


def qam_llrs(symbols: ArrayLike, bits_per_symbol: int, noise_variance: float = 1.0) -> NDArray[np.float64]:
    received = np.asarray(symbols, dtype=np.complex128).reshape(-1)
    points, labels = constellation(bits_per_symbol)
    variance = max(float(noise_variance), 1e-12)
    distances = np.abs(received[:, None] - points[None, :]) ** 2
    llrs = np.empty((received.size, bits_per_symbol), dtype=np.float64)
    for bit_index in range(bits_per_symbol):
        minimum_zero = distances[:, labels[:, bit_index] == 0].min(axis=1)
        minimum_one = distances[:, labels[:, bit_index] == 1].min(axis=1)
        llrs[:, bit_index] = (minimum_one - minimum_zero) / variance
    return llrs.reshape(-1)


def hard_bits_from_llrs(llrs: ArrayLike) -> NDArray[np.uint8]:
    return (np.asarray(llrs) < 0).astype(np.uint8)


def nearest_symbols(symbols: ArrayLike, bits_per_symbol: int) -> NDArray[np.complex128]:
    received = np.asarray(symbols, dtype=np.complex128).reshape(-1)
    points, _ = constellation(bits_per_symbol)
    indices = np.abs(received[:, None] - points[None, :]).argmin(axis=1)
    return points[indices]


"""Rate-1/2, constraint-length-7 convolutional code and soft Viterbi decoder."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

CONSTRAINT_LENGTH = 7
TAIL_BITS = CONSTRAINT_LENGTH - 1
GENERATORS = (0o133, 0o171)
STATE_COUNT = 1 << TAIL_BITS


def _parity(value: int) -> int:
    return value.bit_count() & 1


def convolutional_encode(bits: ArrayLike, *, terminate: bool = True) -> NDArray[np.uint8]:
    source = np.asarray(bits, dtype=np.uint8).reshape(-1)
    if np.any(source > 1):
        raise ValueError("bits must contain only zero and one")
    if terminate:
        source = np.concatenate((source, np.zeros(TAIL_BITS, dtype=np.uint8)))
    encoded = np.empty(source.size * 2, dtype=np.uint8)
    state = 0
    for index, bit in enumerate(source):
        register = ((state << 1) | int(bit)) & 0x7F
        encoded[2 * index] = _parity(register & GENERATORS[0])
        encoded[2 * index + 1] = _parity(register & GENERATORS[1])
        state = register & (STATE_COUNT - 1)
    return encoded


def _trellis() -> tuple[NDArray[np.int16], NDArray[np.uint8]]:
    next_state = np.empty((STATE_COUNT, 2), dtype=np.int16)
    output = np.empty((STATE_COUNT, 2, 2), dtype=np.uint8)
    for state in range(STATE_COUNT):
        for bit in (0, 1):
            register = ((state << 1) | bit) & 0x7F
            next_state[state, bit] = register & (STATE_COUNT - 1)
            output[state, bit, 0] = _parity(register & GENERATORS[0])
            output[state, bit, 1] = _parity(register & GENERATORS[1])
    return next_state, output


_NEXT_STATE, _OUTPUT = _trellis()


def viterbi_decode(llrs: ArrayLike, information_bits: int, *, terminated: bool = True) -> NDArray[np.uint8]:
    values = np.asarray(llrs, dtype=np.float64).reshape(-1)
    if values.size % 2:
        raise ValueError("rate-1/2 code requires an even number of LLRs")
    steps = values.size // 2
    expected_steps = information_bits + (TAIL_BITS if terminated else 0)
    if steps < expected_steps:
        raise ValueError("insufficient coded bits")
    steps = expected_steps
    values = values[: steps * 2].reshape(steps, 2)

    metrics = np.full(STATE_COUNT, np.inf)
    metrics[0] = 0.0
    previous_state = np.zeros((steps, STATE_COUNT), dtype=np.int16)
    previous_bit = np.zeros((steps, STATE_COUNT), dtype=np.uint8)

    for step in range(steps):
        updated = np.full(STATE_COUNT, np.inf)
        for state in range(STATE_COUNT):
            if not np.isfinite(metrics[state]):
                continue
            for bit in (0, 1):
                target = int(_NEXT_STATE[state, bit])
                expected = _OUTPUT[state, bit].astype(np.int8)
                branch = float(np.logaddexp(0.0, (2 * expected - 1) * values[step]).sum())
                candidate = metrics[state] + branch
                if candidate < updated[target]:
                    updated[target] = candidate
                    previous_state[step, target] = state
                    previous_bit[step, target] = bit
        metrics = updated

    state = 0 if terminated else int(np.argmin(metrics))
    decoded = np.empty(steps, dtype=np.uint8)
    for step in range(steps - 1, -1, -1):
        decoded[step] = previous_bit[step, state]
        state = int(previous_state[step, state])
    return decoded[:information_bits]

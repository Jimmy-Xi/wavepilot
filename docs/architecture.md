# Architecture

## Transmitter

1. Compute IEEE CRC-32 over the payload.
2. Build an 88-bit header containing magic, version, MCS, flags, payload length and CRC.
3. Convert payload bytes to bits and terminate a rate-1/2, K=7 convolutional code with six zero tail bits.
4. Gray-map coded bits to QPSK, 16QAM or 64QAM.
5. Fill 44 data carriers and four pilots. Zero-pad only the final OFDM symbol.
6. Apply IFFT and a 64-sample cyclic prefix.
7. Prepend a repeated-half synchronization preamble, a long-training symbol and two independently piloted copies of the header.

## Receiver

1. Correlate against the known preamble and normalize by receive-window energy.
2. Estimate CFO from the phase rotation between the repeated preamble halves.
3. Correct CFO across the capture.
4. Divide the received long-training carriers by their known values to estimate the complex channel.
5. Equalize each active carrier and use pilots to remove common phase error per symbol.
6. Add soft LLRs from the two QPSK header repetitions and parse the frame metadata.
7. Max-log demap the payload constellation and soft-decode the convolutional code with Viterbi.
8. Recover bytes, verify CRC and calculate EVM/estimated SNR.

## Invariants

- The header always occupies exactly 44 QPSK data carriers, or 88 bits.
- Every data/training OFDM symbol uses the same 48-carrier normalization, including a partially filled final symbol.
- CFO must fall inside the repeated-half estimator's unambiguous range of approximately ±187.5 Hz.
- The cyclic prefix exceeds the built-in channel's maximum 11-sample path delay.
- Payload allocation is capped at 16 MiB before trusting decoded header length.
- A successful block requires both CRC equality and byte-for-byte payload equality in experiments.

## Why two header repetitions

The receiver cannot know the payload MCS or length until the header is decoded. Keeping the header in QPSK and summing two independent soft observations improves robustness without creating a separate coding format.

## Why deterministic impairments

Channel seeds make every noisy regression repeatable. Unlike a fixed saved waveform, the model can generate many reproducible cases while still letting CI identify the exact case that failed.

## Current boundary

The PCM WAV path is an offline real-passband loopback. It exercises quantization, upconversion, downconversion and filtering, but it does not yet compensate sound-card latency, sample-rate mismatch or acoustic echo. Those are explicit live-audio roadmap items.


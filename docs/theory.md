# Theory notes

## OFDM orthogonality

With a 48 kHz sample rate and a 256-point FFT, adjacent carriers are spaced by 187.5 Hz. One useful symbol is therefore 5.333 ms. A 64-sample cyclic prefix adds 1.333 ms and protects against multipath delays shorter than that interval.

## CFO estimator

The preamble has two identical halves of length `N/2`. If the second half rotates by phase `phi`, the estimate is:

```text
f_hat = phi * sample_rate / (pi * N)
```

The estimator is unambiguous for approximately ±`sample_rate/N`, or ±187.5 Hz in the default profile.

## One-tap equalizer

After the cyclic prefix removes linear-convolution memory, each active subcarrier is modeled as `Y[k] = H[k]X[k] + W[k]`. The long-training field provides known `X[k]`, so the zero-forcing estimate is `H_hat[k] = Y[k]/X[k]`; payload carriers are equalized with `Y[k]/H_hat[k]`.

## Max-log LLR

For every received QAM point and bit position, WavePilot finds the nearest constellation point labeled zero and the nearest labeled one. The squared-distance difference divided by estimated noise variance is used as the soft LLR. Positive LLR favors bit zero.

## Viterbi metric

The decoder uses the soft LLRs as branch evidence over a 64-state trellis. Six terminating zeros force the encoder back to state zero, making final-state selection unambiguous.

## EVM and SNR estimate

RMS EVM is measured against the nearest ideal constellation decision. WavePilot reports `-20 log10(EVM)` as an approximate decision-directed SNR. At low SNR it is optimistic because incorrect points can still be close to a wrong decision, so BLER and CRC remain the authoritative reliability metrics.


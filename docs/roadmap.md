# Roadmap

## v0.2 — Live acoustic transport

- Add sounddevice-based playback and capture with device enumeration.
- Estimate sample-rate offset from pilot phase slope.
- Add automatic gain control, acoustic echo guard and latency calibration.
- Publish distance, room, loudness and hardware details with every real measurement.

## v0.3 — Link reliability

- Add frequency/time interleaving for burst noise.
- Implement sequence numbers, ACK/NACK and selective-repeat ARQ.
- Add punctured convolutional rates and LDPC.
- Drive MCS selection from measured goodput confidence intervals.

## v0.4 — Performance

- Move FFT, demapper and Viterbi hot paths to C++ with pybind11.
- Add SIMD branch-metric updates and profiling reports.
- Support streaming frames instead of whole-capture processing.

## v1.0 — Radio and hardware acceleration

- Package synchronization/equalization as GNU Radio blocks.
- Connect to an SDR frontend with an explicit legal test band/configuration.
- Implement FFT/equalizer/Viterbi accelerators in FPGA with bit-exact Python reference tests.
- Compare CPU, SDR and FPGA latency, throughput and energy.


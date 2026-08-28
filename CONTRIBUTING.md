# Contributing

1. Keep channel experiments deterministic by exposing and recording the seed.
2. Add an end-to-end CRC assertion for changes to framing, synchronization, equalization, modulation or coding.
3. Distinguish software-channel results from real sound-card or over-the-air measurements.
4. Run `make test`, `make demo` and Ruff before submitting a pull request.
5. Frame-format changes must update `docs/architecture.md` and explain compatibility impact.


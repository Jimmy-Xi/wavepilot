PYTHON ?= python3

.PHONY: test demo sweep benchmark

test:
	$(PYTHON) -m unittest discover -s tests -v

demo:
	$(PYTHON) -m wavepilot simulate --text "WavePilot synchronized OFDM demo" --mcs 16qam --snr 24 --cfo 37 --timing-offset 31 --multipath

sweep:
	$(PYTHON) -m wavepilot sweep --snr 0 4 8 12 --mcs qpsk 16qam 64qam --trials 5 --payload-bytes 256 --cfo 37

benchmark:
	$(PYTHON) tools/benchmark.py


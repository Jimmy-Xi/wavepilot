"""WavePilot command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from .audio import from_passband, read_wav, to_passband, write_wav
from .channel import ChannelConfig, apply_channel
from .config import MCS_BITS_PER_SYMBOL, normalize_mcs
from .experiments import run_snr_sweep
from .phy import DecodeError, OFDMModem, RxResult


def _result_report(result: RxResult, *, input_payload: bytes | None = None, duration: float | None = None) -> dict:
    report = {
        "crc_ok": result.crc_ok,
        "mcs": result.mcs,
        "payload_bytes": len(result.payload),
        "payload_crc32": f"{result.payload_crc32:08x}",
        "calculated_crc32": f"{result.calculated_crc32:08x}",
        "frame_start": result.frame_start,
        "sync_score": result.sync_score,
        "cfo_estimate_hz": result.cfo_estimate_hz,
        "evm_rms": result.evm_rms,
        "estimated_snr_db": result.estimated_snr_db,
        "ofdm_data_symbols": result.ofdm_data_symbols,
    }
    if input_payload is not None:
        compared = min(len(input_payload), len(result.payload))
        if compared:
            first = np.unpackbits(np.frombuffer(input_payload[:compared], dtype=np.uint8))
            second = np.unpackbits(np.frombuffer(result.payload[:compared], dtype=np.uint8))
            errors = int(np.count_nonzero(first != second)) + 8 * abs(len(input_payload) - len(result.payload))
            report["post_fec_ber"] = errors / (8 * max(len(input_payload), len(result.payload)))
        else:
            report["post_fec_ber"] = 0.0 if input_payload == result.payload else 1.0
        report["payload_match"] = input_payload == result.payload
    if duration is not None:
        report["duration_seconds"] = duration
        report["payload_throughput_bps"] = len(result.payload) * 8 / duration
    return report


def _payload_from_args(args: argparse.Namespace) -> bytes:
    if args.input:
        return Path(args.input).read_bytes()
    return args.text.encode("utf-8")


def simulate(args: argparse.Namespace) -> int:
    modem = OFDMModem()
    payload = _payload_from_args(args)
    tx = modem.modulate(payload, normalize_mcs(args.mcs))
    channel_config = ChannelConfig(
        snr_db=args.snr,
        cfo_hz=args.cfo,
        timing_offset=args.timing_offset,
        multipath=args.multipath,
        burst_probability=args.burst_probability,
        seed=args.seed,
    )
    received = apply_channel(tx.waveform, modem.config.sample_rate, channel_config)
    try:
        result = modem.demodulate(received)
    except DecodeError as exc:
        print(json.dumps({"crc_ok": False, "decode_error": str(exc)}, indent=2), file=sys.stdout)
        return 2
    if args.output:
        Path(args.output).write_bytes(result.payload)
    report = _result_report(
        result,
        input_payload=payload,
        duration=tx.waveform.size / modem.config.sample_rate,
    )
    report["channel"] = {
        "snr_db": args.snr,
        "cfo_hz": args.cfo,
        "timing_offset": args.timing_offset,
        "multipath": args.multipath,
        "burst_probability": args.burst_probability,
        "seed": args.seed,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if result.crc_ok and result.payload == payload else 1


def encode(args: argparse.Namespace) -> int:
    modem = OFDMModem()
    payload = Path(args.input).read_bytes()
    tx = modem.modulate(payload, normalize_mcs(args.mcs))
    write_wav(args.output, to_passband(tx.waveform, modem.config), modem.config.sample_rate)
    print(json.dumps({
        "output": str(Path(args.output)),
        "payload_bytes": len(payload),
        "mcs": tx.mcs,
        "sample_rate": modem.config.sample_rate,
        "duration_seconds": tx.waveform.size / modem.config.sample_rate,
        "payload_crc32": f"{tx.payload_crc32:08x}",
    }, indent=2, sort_keys=True))
    return 0


def decode(args: argparse.Namespace) -> int:
    modem = OFDMModem()
    passband, sample_rate = read_wav(args.input)
    if sample_rate != modem.config.sample_rate:
        raise SystemExit(f"expected {modem.config.sample_rate} Hz WAV, got {sample_rate} Hz")
    result = modem.demodulate(from_passband(passband, modem.config))
    Path(args.output).write_bytes(result.payload)
    print(json.dumps(_result_report(result), indent=2, sort_keys=True))
    return 0 if result.crc_ok else 1


def sweep(args: argparse.Namespace) -> int:
    snr_values = [float(value) for value in args.snr]
    mcs_values = [normalize_mcs(value) for value in args.mcs]
    report = run_snr_sweep(
        snr_values,
        mcs_values,
        trials=args.trials,
        payload_bytes=args.payload_bytes,
        multipath=not args.no_multipath,
        cfo_hz=args.cfo,
        seed=args.seed,
    )
    serialized = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wavepilot", description="Adaptive acoustic OFDM modem")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sim = subparsers.add_parser("simulate", help="run an end-to-end deterministic channel simulation")
    payload = sim.add_mutually_exclusive_group()
    payload.add_argument("--input", help="input file; defaults to UTF-8 demo text")
    payload.add_argument("--text", default="WavePilot adaptive OFDM demonstration")
    sim.add_argument("--output", help="write the recovered payload")
    sim.add_argument("--mcs", default="qpsk", choices=tuple(MCS_BITS_PER_SYMBOL))
    sim.add_argument("--snr", type=float, default=24.0)
    sim.add_argument("--cfo", type=float, default=25.0)
    sim.add_argument("--timing-offset", type=int, default=19)
    sim.add_argument("--multipath", action=argparse.BooleanOptionalAction, default=True)
    sim.add_argument("--burst-probability", type=float, default=0.0)
    sim.add_argument("--seed", type=int, default=2026)
    sim.set_defaults(handler=simulate)

    enc = subparsers.add_parser("encode", help="encode a file into mono 48 kHz PCM WAV")
    enc.add_argument("input")
    enc.add_argument("output")
    enc.add_argument("--mcs", default="qpsk", choices=tuple(MCS_BITS_PER_SYMBOL))
    enc.set_defaults(handler=encode)

    dec = subparsers.add_parser("decode", help="decode a WavePilot WAV into a file")
    dec.add_argument("input")
    dec.add_argument("output")
    dec.set_defaults(handler=decode)

    scan = subparsers.add_parser("sweep", help="measure BLER and goodput across SNR and MCS")
    scan.add_argument("--snr", nargs="+", default=[8, 12, 16, 20, 24, 28])
    scan.add_argument("--mcs", nargs="+", default=list(MCS_BITS_PER_SYMBOL))
    scan.add_argument("--trials", type=int, default=5)
    scan.add_argument("--payload-bytes", type=int, default=128)
    scan.add_argument("--cfo", type=float, default=25.0)
    scan.add_argument("--seed", type=int, default=2026)
    scan.add_argument("--no-multipath", action="store_true")
    scan.add_argument("--output")
    scan.set_defaults(handler=sweep)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (DecodeError, ValueError) as exc:
        print(f"wavepilot: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


#!/usr/bin/env python3
"""Extract frames from the archived 6 MHz A6000 captures for offline research.

This independent UART sampler does not execute the sigrok decoder. It uses the
capture's channel metadata, CS windows, and the five-low-bit F0 sync pattern.
It is an evidence tool for these recordings, not a general logic analyzer.
"""

import argparse
import collections
import configparser
import hashlib
import json
import re
import zipfile
from pathlib import Path


def extract_window(signal, begin, end):
    first = signal.find(b"\x01\x00", begin, end)
    if first == -1:
        return None
    start = first + 1
    low_end = signal.find(b"\x01", start, end)
    if low_end == -1:
        return {"error": "incomplete-sync"}
    measured_bit_samples = (low_end - start) / 5
    bit_samples = min((4, 8), key=lambda n: abs(n - measured_bit_samples))
    if abs(bit_samples - measured_bit_samples) > 0.5:
        return {"error": "unrecognized-sync-width", "low_samples": low_end - start}
    frame = bytearray()
    framing_errors = 0
    cursor = start
    while cursor + 9.5 * bit_samples < end:
        sample = lambda bit: signal[int(cursor + bit * bit_samples)]
        if sample(0.5) != 0 or sample(9.5) != 1:
            framing_errors += 1
        frame.append(sum(sample(1.5 + bit) << bit for bit in range(8)))
        next_edge = signal.find(b"\x01\x00", int(cursor + 9.5 * bit_samples), end)
        if next_edge == -1:
            break
        cursor = next_edge + 1
    result = {"baud": 6_000_000 // bit_samples, "hex": frame.hex(),
              "uart_framing_errors": framing_errors}
    if len(frame) < 9 or frame[0] != 0xF0:
        result["error"] = "short-or-missing-sync"
        return result
    declared = int.from_bytes(frame[1:3], "little")
    result["declared_length"] = declared
    if declared < 9 or declared > len(frame):
        result["error"] = "invalid-or-truncated-length"
        return result
    expected = sum(frame[1:declared - 3]) & 0xFFFF
    observed = int.from_bytes(frame[declared - 3:declared - 1], "little")
    result.update({"class": frame[3], "sequence": frame[4], "type": frame[5],
                   "checksum": observed, "checksum_valid": observed == expected,
                   "terminator_valid": frame[declared - 1] == 0x55,
                   "padding_bytes": len(frame) - declared,
                   "padding_all_zero": all(b == 0 for b in frame[declared:])})
    return result


def analyze(path):
    with zipfile.ZipFile(path) as archive:
        corrupt = archive.testzip()
        if corrupt:
            raise ValueError(f"ZIP CRC failure: {path.name}:{corrupt}")
        metadata = configparser.ConfigParser()
        metadata.read_string(archive.read("metadata").decode())
        device = metadata["device 1"]
        if device["samplerate"] != "6 MHz" or device["unitsize"] != "1":
            raise ValueError(f"Unsupported capture layout: {path}")
        probes = {v: int(k[5:]) - 1 for k, v in device.items() if k.startswith("probe")}
        prefix = device["capturefile"] + "-"
        chunks = sorted((n for n in archive.namelist() if n.startswith(prefix)),
                        key=lambda n: int(n[len(prefix):]))
        raw = b"".join(archive.read(n) for n in chunks)
    rows = []
    counters = collections.Counter()
    for direction, data_name, cs_name in (
        ("lens-to-body", "RXD", "LENS_CS_BODY"),
        ("body-to-lens", "TXD", "BODY_CS_LENS"),
    ):
        bitstream = lambda pin: raw.translate(bytes((b >> pin) & 1 for b in range(256)))
        signal, chip_select = bitstream(probes[data_name]), bitstream(probes[cs_name])
        for match in re.finditer(b"\x01+", chip_select):
            begin, end = match.span()
            if begin == 0 or end == len(raw):
                counters["partial_windows"] += 1
                continue
            counters["complete_cs_windows"] += 1
            result = extract_window(signal, begin, end)
            if result is None:
                counters["windows_without_start_edge"] += 1
                continue
            result.update({"capture": path.name, "direction": direction,
                           "cs_start_sample": begin, "cs_end_sample": end})
            rows.append(result)
            if result.get("error"):
                counters["extraction_errors"] += 1
            elif (result["checksum_valid"] and result["terminator_valid"]
                  and not result["uart_framing_errors"]):
                counters["validated_frames"] += 1
            else:
                counters["validation_failures"] += 1
    rows.sort(key=lambda row: row["cs_start_sample"])
    return rows, {"capture": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "zip_crc_valid": True, "sample_rate_hz": 6_000_000,
                  "samples": len(raw), "probes_zero_based": probes,
                  "counts": dict(sorted(counters.items())),
                  "baud_counts": dict(collections.Counter(str(r["baud"]) for r in rows if "baud" in r)),
                  "message_types": sorted({f"0x{r['type']:02X}" for r in rows if "type" in r})}


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures", type=Path, default=root / "upstream/Entropy512/sigrok-dumps/lens_mounts/sony_emount")
    parser.add_argument("--output", type=Path, default=root / "analysis")
    args = parser.parse_args()
    paths = sorted(args.captures.glob("*.sr"))
    if not paths:
        parser.error("No .sr captures found")
    rows, summaries = [], []
    for path in paths:
        records, summary = analyze(path)
        rows.extend(records)
        summaries.append(summary)
        print(path.name, json.dumps(summary["counts"], sort_keys=True))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "entropy512-frames.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    (args.output / "entropy512-capture-summary.json").write_text(json.dumps({
        "schema_version": 1, "method": "Independent CS-gated 8N1 UART sampling; not a sigrok runtime replay",
        "checksum_rule": "sum(frame[1:declared_length-3]) modulo 65536, little-endian footer",
        "captures": summaries,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()

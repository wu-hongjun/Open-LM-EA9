#!/usr/bin/env python3
"""Offline comparison of reconnect CHECK/READ evidence with the saved baseline."""
import argparse
import json
from collections import Counter
from pathlib import Path

from verify_ea9_backup import digest, require, word


def verify(folder, baseline):
    inventory = [json.loads(x) for x in (folder / "inventory-session.jsonl").read_text().splitlines()]
    old_inventory = [json.loads(x) for x in (baseline / "inventory-session.jsonl").read_text().splitlines()]
    devices = [x for x in inventory if x["event"] == "device"]
    old_devices = [x for x in old_inventory if x["event"] == "device"]
    require(len(devices) == len(old_devices) == 1, "Ambiguous inventory")
    require(not any(x["event"] in ("request", "reply") for x in inventory), "Inventory sent requests")
    identity_fields = ("product", "serial", "vid", "pid", "usage_page", "usage",
                       "max_input", "max_output", "report_descriptor")
    device, old_device = devices[0], old_devices[0]
    require(all(device[k] == old_device[k] for k in identity_fields), "Device identity changed")
    ranges = {
        "app-vectors": (0x5000, 64), "device-id": (0x41002018, 64),
        "nvm-status": (0x41004000, 64), "user-row": (0x00804000, 64),
        "calibration": (0x00806000, 64), "port-a": (0x41004400, 128),
        "full-flash": (0, 0x20000),
    }
    counts, samples = Counter(), {}
    prior_flash = (baseline / "full-flash-read1.bin").read_bytes()
    require(prior_flash == (baseline / "full-flash-read2.bin").read_bytes(), "Prior full reads differ")
    for name, (address, length) in ranges.items():
        events = [json.loads(x) for x in (folder / f"{name}-session.jsonl").read_text().splitlines()]
        session_devices = [x for x in events if x["event"] == "device"]
        require(len(session_devices) == 1 and
                all(session_devices[0][k] == device[k] for k in identity_fields), f"{name}: identity changed")
        transfers = [x for x in events if x["event"] in ("request", "reply")]
        require(len(transfers) == 2 * (1 + length // 64), f"{name}: wrong exchange count")
        dump = (folder / f"{name}.bin").read_bytes()
        require(len(dump) == length, f"{name}: wrong dump length")
        reconstructed = bytearray()
        for i in range(0, len(transfers), 2):
            request, reply = transfers[i:i + 2]
            operation = "READ" if i else "CHECK"
            target = address + 64 * (i // 2 - 1) if i else 0
            code = 3 if i else 2
            expected = bytearray.fromhex("95276818") + bytes([code, code]) + bytes(58)
            if i:
                expected[6:10] = target.to_bytes(4, "little")
            require(request["event"] == "request" and reply["event"] == "reply", f"{name}: unpaired transfer")
            require(bytes.fromhex(request["hex"]) == expected, f"{name}: unexpected command bytes")
            for item in (request, reply):
                require(item["operation"] == operation and item["address"] == target, f"{name}: address mismatch")
            payload = bytes.fromhex(reply["hex"])
            require(len(payload) == 64, f"{name}: wrong report length")
            if i:
                reconstructed.extend(payload)
            else:
                require(payload[:9] == bytes.fromhex("952768180202010800"), f"{name}: wrong CHECK reply")
            counts[operation] += 1
        require(dump == bytes(reconstructed), f"{name}: transcript/file mismatch")
        if name == "app-vectors":
            previous = prior_flash[0x5000:0x5040]
        elif name == "full-flash":
            previous = prior_flash
        else:
            previous = (baseline / f"{name}-read1.bin").read_bytes()
        same = dump == previous
        if name != "port-a":
            require(same, f"{name}: baseline changed")
        samples[name] = {"address": f"0x{address:08X}", "length": length,
                         "matches_previous": same, "sha256": digest(dump)}
    require(not any(p.read_bytes() for p in folder.glob("*-stderr.txt")), "Probe reported stderr")
    nvm = (folder / "nvm-status.bin").read_bytes()
    port = (folder / "port-a.bin").read_bytes()
    context = json.loads((folder / "session-context.json").read_text())
    return {
        "schema_version": 1, "date": "2026-10-10", "verification": "passed",
        "user_report": context["user_report"], "equipment_available": context["equipment_available"],
        "identity_matches_previous": True,
        "registry_entry_changed": device["registry_id"] != old_device["registry_id"],
        "currently_present": True, "CHECK_version": "1.8.0",
        "request_reply_counts": dict(counts), "total_exchanges": sum(counts.values()),
        "scope": "HID enumeration, CHECK and previously qualified memory READ; no programming or reset",
        "samples": samples, "main_flash_bytes": len(prior_flash),
        "protection_unchanged": samples["nvm-status"]["matches_previous"] and samples["user-row"]["matches_previous"],
        "security_bit_active": bool(word(nvm, 0x18, 2) & 0x100),
        "live_lock_bits": f"0x{word(nvm, 0x20, 2):04X}",
        "PA23": {"input_high": bool(word(port, 0x20) & (1 << 23)),
                 "direction_output": bool(word(port, 0) & (1 << 23)),
                 "output_latch_high": bool(word(port, 0x10) & (1 << 23)),
                 "pincfg": f"0x{port[0x57]:02X}"},
        "restart_evidence": "User reports unplug; matching device re-enumerated with a new registry entry; firmware and qualified snapshots match.",
        "limitations": ["Power/reset timing and pin voltages were not instrumented",
                        "USB is the only available access; no continuity, electrical, SWD or independent restoration test",
                        "The stock cap still supplies no demonstrated application launch or custom management service"]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.folder, args.baseline)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"verification": report["verification"], "total_exchanges": report["total_exchanges"],
                      "registry_entry_changed": report["registry_entry_changed"],
                      "full_flash_matches": report["samples"]["full-flash"]["matches_previous"]}, indent=2))


if __name__ == "__main__":
    main()

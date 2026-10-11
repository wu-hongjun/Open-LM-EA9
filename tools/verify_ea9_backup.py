#!/usr/bin/env python3
"""Verify local EA9 read-only evidence. Never connects to hardware.

Produces a summary without USB serial/location or firmware bytes. Raw input
files must stay private. Only the documented stock 1.8.0 investigation is
qualified; this is not a generic image validator or restoration tool.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


WINDOWS = {
    "device-id": (0x41002018, 64),
    "nvm-status": (0x41004000, 64),
    "user-row": (0x00804000, 64),
    "calibration": (0x00806000, 64),
    "port-a": (0x41004400, 128),
    "full-flash": (0, 0x20000),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def word(data, offset, length=4):
    return int.from_bytes(data[offset:offset + length], "little")


def verify(folder, stock, previous):
    counts = Counter()
    pairs = {}
    sessions = []
    inventory = [json.loads(line) for line in (folder / "inventory-session.jsonl").read_text().splitlines()]
    require(not any(x["event"] in ("request", "reply") for x in inventory),
            "Inventory contains unexpected hardware requests")
    devices = [x for x in inventory if x["event"] == "device"]
    require(len(devices) == 1, "Inventory device ambiguity")
    baseline = devices[0]
    identity_fields = ("product", "serial", "vid", "pid", "usage_page", "usage",
                       "max_input", "max_output", "report_descriptor")
    for name, (address, length) in WINDOWS.items():
        reads = []
        for pass_number in (1, 2):
            stem = f"{name}-read{pass_number}"
            data = (folder / f"{stem}.bin").read_bytes()
            require(len(data) == length, f"{stem}: wrong dump length")
            events = [json.loads(line) for line in
                      (folder / f"{stem}-session.jsonl").read_text().splitlines()]
            session_devices = [x for x in events if x["event"] == "device"]
            require(len(session_devices) == 1 and
                    all(session_devices[0][key] == baseline[key] for key in identity_fields),
                    f"{stem}: device identity mismatch")
            exchanges = [x for x in events if x["event"] in ("request", "reply")]
            require(len(exchanges) == 2 * (1 + length // 64), f"{stem}: wrong exchange count")
            reconstructed = bytearray()
            for i in range(0, len(exchanges), 2):
                request, reply = exchanges[i:i + 2]
                require(request["event"] == "request" and reply["event"] == "reply",
                        f"{stem}: missing/reordered request/reply")
                raw = bytes.fromhex(request["hex"])
                payload = bytes.fromhex(reply["hex"])
                require(len(raw) == len(payload) == 64, f"{stem}: wrong report length")
                operation = "CHECK" if i == 0 else "READ"
                code = 2 if operation == "CHECK" else 3
                expected_address = 0 if i == 0 else address + 64 * (i // 2 - 1)
                expected = bytearray.fromhex("95276818") + bytes([code, code]) + bytes(58)
                if operation == "READ":
                    expected[6:10] = expected_address.to_bytes(4, "little")
                require(raw == expected, f"{stem}: non-whitelisted request")
                for event in (request, reply):
                    require(event["operation"] == operation and event["address"] == expected_address,
                            f"{stem}: command/address mismatch")
                if operation == "CHECK":
                    require(payload[:9] == bytes.fromhex("952768180202010800"),
                            f"{stem}: unexpected stock CHECK reply")
                else:
                    reconstructed.extend(payload)
                counts[operation] += 1
            require(bytes(reconstructed) == data, f"{stem}: file differs from transcript")
            versions = [x["value"] for x in events if x["event"] == "version"]
            require(versions == ["1.8.0"], f"{stem}: unexpected version event")
            reads.append(data)
            sessions.append({"name": stem, "CHECK": 1, "READ": length // 64})
        equal = reads[0] == reads[1]
        if name != "port-a":
            require(equal, f"{name}: repeated immutable/status reads differ")
        pairs[name] = {"address": f"0x{address:08X}", "length": length,
                       "identical": equal, "sha256_read1": digest(reads[0]),
                       "sha256_read2": digest(reads[1])}

    flash = (folder / "full-flash-read1.bin").read_bytes()
    application = stock.read_bytes()
    require(flash[0x5000:0x5000 + len(application)] == application, "Installed/cache mismatch")
    old_boot = (previous / "bootloader-read1.bin").read_bytes()
    old_app = (previous / "application-read1.bin").read_bytes()
    require(flash[:len(old_boot)] == old_boot and flash[0x5000:0x5000 + len(old_app)] == old_app,
            "Earlier boot/application evidence changed")
    nvm = (folder / "nvm-status-read1.bin").read_bytes()
    param = word(nvm, 8)
    page_size = 8 << ((param >> 16) & 7)
    pages = param & 0xFFFF
    require(pages * page_size == len(flash), "Flash dump/capacity mismatch")
    did = word((folder / "device-id-read1.bin").read_bytes(), 0)
    require(did == 0x1001030B, "Unqualified device/revision")
    fuses = word((folder / "user-row-read1.bin").read_bytes(), 0, 8)
    bootprot, eeprom = fuses & 7, (fuses >> 4) & 7
    ports = []
    for i in (1, 2):
        port = (folder / f"port-a-read{i}.bin").read_bytes()
        ports.append({"direction_output": bool(word(port, 0) & (1 << 23)),
                      "output_latch_high": bool(word(port, 0x10) & (1 << 23)),
                      "input_high": bool(word(port, 0x20) & (1 << 23)),
                      "pincfg": f"0x{port[0x57]:02X}", "mux_function": port[0x3B] >> 4})
    calibration = word((folder / "calibration-read1.bin").read_bytes(), 0x20, 16)
    return {
        "schema_version": 1, "date": "2026-10-10", "verification": "passed",
        "scope": "CHECK and qualified memory READ only; no programming/reset/debug attachment",
        "identity_matches_previous": json.loads((folder / "identity-comparison.json").read_text())["identity_matches_previous"],
        "CHECK_version": "1.8.0", "request_reply_counts": dict(counts),
        "total_exchanges": sum(counts.values()), "sessions": sessions, "repeated_dumps": pairs,
        "chip": {"DID": f"0x{did:08X}", "part": "ATSAMD21E17A", "die_revision": "D",
                 "NVM_PARAM": f"0x{param:08X}", "page_bytes": page_size, "pages": pages,
                 "main_flash_bytes": pages * page_size, "RWWEE_pages": param >> 20},
        "protection": {"BOOTPROT": bootprot, "boot_protected_bytes": 0 if bootprot == 7 else 32768 >> bootprot,
                       "EEPROM": eeprom, "emulation_bytes": 0 if eeprom == 7 else 16384 >> eeprom,
                       "security_bit_active": bool(word(nvm, 0x18, 2) & 0x100),
                       "live_lock_bits": f"0x{word(nvm, 0x20, 2):04X}",
                       "user_lock_bits": f"0x{(fuses >> 48) & 0xFFFF:04X}",
                       "NVM_MANW": bool(word(nvm, 4) & 0x80),
                       "NVM_error_flags": word(nvm, 0x18, 2) & 0x1C},
        "PA23_samples": ports,
        "calibration": {"USB_TRANSN": (calibration >> 45) & 31, "USB_TRANSP": (calibration >> 50) & 31,
                        "USB_TRIM": (calibration >> 55) & 7, "DFLL48M_COARSE": (calibration >> 58) & 63},
        "flash_layout": {"installed_image_matches_cache": True, "installed_image_sha256": digest(application),
                         "previous_boot_and_application_match": True,
                         "additional_image_address": "0xA080",
                         "additional_image_matches_cache": flash[0xA080:0xA080 + len(application)] == application,
                         "command_shaped_blocks": {"0xA000": "CHECK", "0xA040": "START"},
                         "all_ff_from_0xF080": all(x == 255 for x in flash[0xF080:])},
        "limitations": ["Cold boot not confirmed by a physical reconnect in this run",
                        "No voltage, continuity, chip marking or SWD pad measurement",
                        "No independent restoration or custom service execution",
                        "User-row backup is a 64-byte window including all documented 64 fuse bits; not all auxiliary/lockbit/serial rows",
                        "PA23 is a digital register sample, not a voltage measurement; register byte reads are not atomic",
                        "Second image origin/function is unknown; not a proven recovery slot"]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--stock", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.folder, args.stock, args.previous)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"verification": report["verification"],
                      "total_exchanges": report["total_exchanges"],
                      "main_flash_bytes": report["chip"]["main_flash_bytes"],
                      "full_flash_sha256": report["repeated_dumps"]["full-flash"]["sha256_read1"]}, indent=2))


if __name__ == "__main__":
    main()

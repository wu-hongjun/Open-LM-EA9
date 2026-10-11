#!/usr/bin/env python3
"""Verify a prototype .ea9backup offline. Never opens USB or prints device serials."""
import argparse
import hashlib
import json
import re
from pathlib import Path

EXPECTED_FILES = {"flash.bin": 131072, "user-row.bin": 64, "calibration.bin": 64,
                  "device-id.bin": 64, "nvm-status.bin": 64}
BOOT_HASH = "8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895"


def verify(path: Path) -> dict:
    manifest_file = path / "manifest.json"
    if manifest_file.is_symlink() or manifest_file.stat().st_size > 65536:
        raise ValueError("Manifest must be a regular file no larger than 64 KiB")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if type(manifest["schemaVersion"]) is not int or manifest["schemaVersion"] != 1:
        raise ValueError("Unsupported backup schema")
    if set(manifest["files"]) != set(EXPECTED_FILES):
        raise ValueError("Unexpected manifest file set")
    data_by_name = {}
    for name, length in EXPECTED_FILES.items():
        file = path / name
        if file.is_symlink() or not file.is_file() or file.stat().st_size != length:
            raise ValueError(f"Invalid file type or size: {name}")
        data = file.read_bytes()
        record = manifest["files"][name]
        expected_hash = record["sha256"]
        if record["bytes"] != length or not re.fullmatch(r"[a-f0-9]{64}", expected_hash):
            raise ValueError(f"Invalid digest record: {name}")
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError(f"Checksum mismatch: {name}")
        data_by_name[name] = data
    boot_hash = hashlib.sha256(data_by_name["flash.bin"][:0x4000]).hexdigest()
    if boot_hash != BOOT_HASH or manifest["bootCodeSHA256"] != boot_hash:
        raise ValueError("Unrecognized bootloader code")
    if int.from_bytes(data_by_name["device-id.bin"][:4], "little") != 0x1001030B:
        raise ValueError("Unexpected MCU identity")
    param = int.from_bytes(data_by_name["nvm-status.bin"][8:12], "little")
    if param & 0xFFFF != 2048 or (param >> 16) & 7 != 3:
        raise ValueError("Unexpected flash geometry")
    if (manifest["flashBytes"], manifest["flashReadPasses"], manifest["auxiliaryReadPasses"], manifest["reportExchanges"]) != (131072, 2, 2, 4359):
        raise ValueError("Unexpected recorded read counts")
    if manifest["restorationQualified"] is not False:
        raise ValueError("Prototype backups must not claim qualified restoration")
    return {"valid": True, "flash_bytes": 131072, "flash_sha256": manifest["files"]["flash.bin"]["sha256"],
            "recorded_flash_passes": 2, "recorded_exchanges": 4359, "restoration_qualified": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.backup)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Backup verification failed: {error}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

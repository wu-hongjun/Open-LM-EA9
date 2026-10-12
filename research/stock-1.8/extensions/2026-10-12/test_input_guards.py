#!/usr/bin/env python3
"""Check research CLI guards with synthetic files; no original input writes."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FIRMWARE = ROOT / "firmware/recovery/stock-1.8.0/application.bin"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if sys.flags.optimize:
        raise SystemExit("guard-test assertions require ordinary Python")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        help="optional new JSON file; existing files are never overwritten")
    args = parser.parse_args()
    original_sha = sha(FIRMWARE)
    validator = HERE / "validate_sensor_boundary.py"
    results = []
    with tempfile.TemporaryDirectory(prefix="ea9-sensor-guard-") as directory:
        directory = Path(directory)
        wrong = directory / "wrong-size.bin"
        wrong.write_bytes(b"\x00")
        altered = directory / "wrong-digest.bin"
        synthetic = bytearray(FIRMWARE.read_bytes())
        synthetic[0] ^= 1
        altered.write_bytes(synthetic)
        cases = [
            ("existing-output", [], ["--output", str(directory)], "FileExistsError"),
            ("optimized-python", ["-O"], ["--output", str(directory / "optimized")],
             "Python optimization disables fixture assertions"),
            ("wrong-size", [], ["--firmware", str(wrong), "--output", str(directory / "size")],
             "oracle must be the 20,172-byte stock 1.8.0 application"),
            ("wrong-digest", [], ["--firmware", str(altered), "--output", str(directory / "digest")],
             "oracle SHA-256 does not match pinned stock 1.8.0"),
        ]
        before = sorted(p.name for p in directory.iterdir())
        for name, python_flags, arguments, reason in cases:
            completed = subprocess.run(
                [sys.executable, *python_flags, str(validator), *arguments],
                capture_output=True, text=True, check=False
            )
            assert completed.returncode != 0, name
            assert reason in completed.stderr, (name, completed.stderr)
            assert sorted(p.name for p in directory.iterdir()) == before, name
            results.append({"case": name, "result": "rejected as expected",
                            "newFilesOrDirectories": 0})
    assert sha(FIRMWARE) == original_sha
    report = {
        "researchDate": "2026-10-12", "cases": len(results), "results": results,
        "originalInputSHA256": original_sha, "originalInputUnchanged": True,
        "sourcesSHA256": {
            str(path.relative_to(ROOT)): sha(path) for path in [
                Path(__file__).resolve(), validator, HERE.parents[1] / "config.py"
            ]
        },
        "usbReports": 0, "hardwareOperations": 0,
    }
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        with args.output.open("x") as output:
            output.write(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()

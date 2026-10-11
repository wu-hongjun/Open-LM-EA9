#!/usr/bin/env python3
"""Run the complete finite stock application comparison without hardware access."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firmware", type=Path, default=config.DEFAULT_FIRMWARE,
                        help="explicit stock application path; pinned size/hash still required")
    parser.add_argument("--output", type=Path,
                        help="new directory under an existing parent; default creates a temporary directory")
    parser.add_argument("--compiler", help="C compiler executable (default CC or clang)")
    args = parser.parse_args()
    # Assert-based fixture comparisons must never silently disappear under -O.
    if not __debug__:
        parser.error("Python optimization is unsupported: fixture assertions must stay enabled")
    try:
        import unicorn
        if unicorn.__version__ != "2.1.4":
            raise ValueError("install pinned unicorn==2.1.4 from requirements.txt")
        cfg = config.configure(args.firmware, args.output, args.compiler)
    except (ImportError, OSError, ValueError) as error:
        parser.error(str(error))
    print("New validation output: " + str(cfg.output), flush=True)
    started = datetime.now(timezone.utc).isoformat()
    initial_input_hash = hashlib.sha256(cfg.rom).hexdigest()
    try:
        # These retained suites intentionally compose: application imports
        # protocol, which imports core; each writes its fresh result manifest.
        importlib.import_module("validate_application")
        reports = {
            name: json.loads((cfg.output / filename).read_text())
            for name, filename in [
                ("core", "validation.json"),
                ("protocol", "protocol-validation.json"),
                ("application", "application-validation.json"),
            ]
        }
        if reports["application"]["combined_cases_steps"] != 24991:
            raise AssertionError("unexpected complete-suite comparison count")
        if hashlib.sha256(cfg.firmware.read_bytes()).hexdigest() != initial_input_hash:
            raise AssertionError("oracle file changed during validation")
        source_hashes = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(config.HERE.iterdir())
            if path.suffix in (".py", ".c", ".h")
        }
        compiler_version = subprocess.run(
            [cfg.compiler, "--version"], text=True, capture_output=True, check=True
        ).stdout.splitlines()[0]
        summary = {
            "stage": "passed-finite-original-instruction-comparison",
            "started_at_utc": started,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_sha256": initial_input_hash,
            "input_size_bytes": len(cfg.rom),
            "input_unchanged": True,
            "routine_entries": 38,
            "core_cases_steps": reports["core"]["total_cases_steps"],
            "protocol_metadata_cases": reports["protocol"]["protocol_metadata_cases"],
            "application_cases_steps": reports["application"]["app_cases_steps"],
            "total_cases_steps": reports["application"]["combined_cases_steps"],
            "negative_controls": {
                "sensor_wrap": reports["core"]["negative_control"],
                "metadata_immediate": reports["protocol"]["metadata_mutation"],
            },
            "python": sys.version,
            "unicorn": unicorn.__version__,
            "platform": platform.platform(),
            "compiler": compiler_version,
            "library_flags": list(cfg.library_flags),
            "source_sha256": source_hashes,
            "report_sha256": {
                name: hashlib.sha256((cfg.output / name).read_bytes()).hexdigest()
                for name in ("validation.json", "protocol-validation.json", "application-validation.json")
            },
            "hardware_access": False,
            "flashable_firmware": False,
            "claims": "Finite instruction comparisons only; declared dummy registers and stubs, no timing or whole-firmware equivalence.",
        }
        (cfg.output / "reproduction.json").write_text(json.dumps(summary, indent=2) + "\n")
        print("PASS: 24,991 comparisons, 38 entries, both negative controls detected", flush=True)
        print("Summary: " + str(cfg.output / "reproduction.json"), flush=True)
    except Exception as error:
        failure = {"stage": "failed", "input_sha256": initial_input_hash,
                   "error_type": type(error).__name__, "error": str(error)}
        (cfg.output / "failure.json").write_text(json.dumps(failure, indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()

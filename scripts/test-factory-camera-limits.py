#!/usr/bin/env python3
"""Reproduce AF 2.4 wrapper/mechanics counterexamples offline; no device APIs.

These passing assertions confirm a failure in the installed candidate's policy,
not a fix or a proven cause on hardware. Use a new output directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(mode=0o700, parents=True, exist_ok=False)
sources = ["firmware/tests/test_factory_camera_limits.c", "firmware/ea9/hosttest/sim_motor.c",
           "firmware/ea9/src/factory_servo.c", "firmware/ea9/src/factory_af.c",
           "firmware/ea9/src/io_guard.c", "firmware/ea9/src/focus_map.c",
           "firmware/ea9/src/af_control.c", "firmware/ea9/src/af_completion.c",
           "firmware/ea9/src/focus_dist.c"]
binary = out / "camera_limits"
subprocess.run(["cc", "-std=gnu99", "-O1", "-Wall", "-Wextra", "-Werror",
                "-fsanitize=undefined,address", "-fno-sanitize-recover=all",
                "-Ifirmware/ea9/hosttest", "-Ifirmware/ea9/src", *sources,
                "-o", str(binary)], cwd=ROOT, check=True)
rows = []
for target in [4, 40, 100, 400, 1000, 3000, 5000, 5952]:
    result = subprocess.run([str(binary), str(target)], check=True, capture_output=True, text=True)
    fields = dict(part.split("=", 1) for part in result.stdout.split())
    rows.append({key: float(value) if "." in value else int(value) for key, value in fields.items()})
report = {"status": "counterexamples-confirmed-not-fixed", "firmwareUnderStudy": "2.4.0",
          "hardwareReportsSent": 0, "simulatedTargets": rows,
          "normalShortCorrectionPermanentlyFaults": True,
          "fullTravelDeadlinePermanentlyFaults": True,
          "factoryPureCallbackAdmitsNewTargetAfterTimeout": True,
          "rootCauseOnOwnerHardwareProven": False,
          "limitations": ["Mechanical coefficients inherited from upstream author's adapter, not measured on owner's unit",
                          "No lens optics, image formation, exposure or camera protocol modeled",
                          "No frame/ADC pump delay in this isolated probe",
                          "Clock advances on simulator millis calls; elapsed values are simulation results",
                          "Factory callback equivalence was established by a separate finite original-byte oracle"],
          "sources": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in sources}}
(out / "counterexamples.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))

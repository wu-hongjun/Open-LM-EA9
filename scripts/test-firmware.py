#!/usr/bin/env python3
"""Run inherited behavioral checks and cross-language profile/frame checks."""
from pathlib import Path
import argparse
import subprocess
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--af", action="store_true", help="Also validate the separate AF template/profile fixtures")
with_af = parser.parse_args().af
BASE = ROOT / "firmware/ea9"
OUT = ROOT / "artifacts/firmware-milestone/hosttests"
OUT.mkdir(parents=True, exist_ok=True)
COMMON = ["cc", "-std=gnu99", "-Wall", "-Wextra", "-O1", "-Ihosttest", "-Isrc"]
tests = {
    "emount": ["hosttest/test_emount.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c"],
    "servo": ["hosttest/test_servo.c", "hosttest/sim_motor.c", "src/servo.c", "src/io_guard.c"],
    "nobody": ["hosttest/test_nobody.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c"],
    "init": ["hosttest/test_init.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c"],
    "focus": ["hosttest/test_focus.c", "src/focus_map.c"],
    "focus_dist": ["hosttest/test_focus_dist.c", "src/focus_dist.c", "-lm"],
    "focus_pred": ["hosttest/test_focus_pred.c", "src/focus_pred.c"],
    "af_control": ["../tests/test_af_control.c", "src/af_control.c", "src/focus_map.c", "src/focus_dist.c"],
    "io_guard": ["hosttest/test_io_guard.c", "src/io_guard.c"],
    "af_reconciliation": ["../tests/test_af_reconciliation.c", "src/af_reference.c", "src/af_completion.c", "src/af_control.c", "src/focus_map.c", "src/focus_dist.c"],
    "af_lifecycle": ["-DEA9_SIM_MOTOR", "-DEA9_NO_LOG", "-ffunction-sections", "-fdata-sections", "-Wl,-dead_strip", "hosttest/test_af_lifecycle.c", "hosttest/sim_motor.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c", "src/servo.c", "src/af_control.c", "src/af_reference.c", "src/af_completion.c", "src/io_guard.c", "src/focus_map.c", "src/focus_dist.c", "src/focus_pred.c"],
    "profile": ["../tests/test_profile.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c"],
}
for name, files in tests.items():
    binary = OUT / f"test_{name}"
    subprocess.run(COMMON + files + ["-o", str(binary)], cwd=BASE, check=True)
    if name == "profile":
        continue
    variants = [["nobody"], ["slowbody"]] if name == "nobody" else [[]]
    if name == "io_guard": variants = [[x] for x in ["ready", "timeout", "wrap", "frozen"]]
    if name == "af_lifecycle": variants = [[str(x)] for x in range(13)]
    for args in variants:
        subprocess.run([str(binary)] + args, check=True)
# Compile actual sensor and PWM drivers against DFP-shaped register memory.
mmio = OUT / "test_mmio_faults"
subprocess.run(["cc", "-std=gnu99", "-O1", "-Wall", "-Wextra", "-ffunction-sections", "-fdata-sections", "-Wl,-dead_strip", "-DEA9_AF_BUILD", "-D__SAMD21E17A__", "-Isrc", "-I../../tools/firmware-deps/samd21-dfp-2/samd21a/include", "-I../../tools/firmware-deps/CMSIS_5-5.9.0/CMSIS/Core/Include", "-include", "hosttest/mmio/registers.h", "hosttest/mmio/test_faults.c", "src/io_guard.c", "src/motor.c", "src/abs_encoder.c", "src/vdd.c", "src/em_uart.c", "-o", str(mmio)], cwd=BASE, check=True)
for case in ["encoder", "encoder-reset", "adc", "burst-frozen", "uart", "uart-rx", "pwm", "release", "irq", "irq-masked", "frozen"]:
    subprocess.run([str(mmio), case], check=True)
delays = OUT / "test_mmio_delays"
subprocess.run(["cc", "-std=gnu99", "-O1", "-Wall", "-Wextra", "-ffunction-sections", "-fdata-sections", "-Wl,-dead_strip", "-DEA9_AF_BUILD", "-D__SAMD21E17A__", "-Isrc", "-I../../tools/firmware-deps/samd21-dfp-2/samd21a/include", "-I../../tools/firmware-deps/CMSIS_5-5.9.0/CMSIS/Core/Include", "-include", "hosttest/mmio/registers.h", "hosttest/mmio/test_delays.c", "src/io_guard.c", "src/motor.c", "src/delay.c", "-o", str(delays)], cwd=BASE, check=True)
for case in ["us", "ms"]:
    subprocess.run([str(delays), case], check=True)
inventory = json.loads((ROOT / "profiles/requested-lenses.json").read_text())["lenses"]
cli = ROOT / "apps/macos/.build/out/Products/Debug/ea9ctl"
if with_af:
    subprocess.run(COMMON + ["-DEM_FW_VERSION_BCD=0x22u", "-DEA9_PROFILE_ADDRESS=0x9f00u"] + tests["profile"]
                   + ["-o", str(OUT / "test_af_profile")], cwd=BASE, check=True)
for lens in inventory:
    if lens["kind"] == "zoom":
        continue
    image = OUT / f'{lens["id"]}.bin'
    if image.exists():
        image.unlink() # Generated fixture only; never hardware backups.
    subprocess.run([str(cli), "--state-directory", str(OUT / "state"), "prepare", lens["id"], str(image)], check=True)
    subprocess.run([str(OUT / "test_profile"), str(image)], check=True)
    if with_af:
        candidate = OUT / f'{lens["id"]}-af.bin'
        for path in (candidate, candidate.with_suffix(".manifest.json")):
            if path.exists(): path.unlink() # Generated fixtures only.
        subprocess.run([sys.executable, str(ROOT / "scripts/prepare-af.py"), str(image), str(candidate)], check=True)
        subprocess.run([str(OUT / "test_af_profile"), str(candidate)], check=True)

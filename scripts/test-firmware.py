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
    "stock_query": ["-fsanitize=undefined,address", "-fno-sanitize-recover=all", "../tests/test_stock_query.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c", "src/lens_aperture.c"],
    "factory_servo": ["-fsanitize=undefined,address", "-fno-sanitize-recover=all", "hosttest/test_factory_servo.c", "src/factory_servo.c", "src/factory_af.c", "src/io_guard.c", "src/focus_map.c"],
    "emount": ["hosttest/test_emount.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c", "src/lens_aperture.c"],
    "servo": ["hosttest/test_servo.c", "hosttest/sim_motor.c", "src/servo.c", "src/io_guard.c"],
    "nobody": ["hosttest/test_nobody.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c", "src/lens_aperture.c"],
    "init": ["hosttest/test_init.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c", "src/lens_aperture.c"],
    "focus": ["hosttest/test_focus.c", "src/focus_map.c"],
    "focus_dist": ["hosttest/test_focus_dist.c", "src/focus_dist.c", "-lm"],
    "focus_pred": ["hosttest/test_focus_pred.c", "src/focus_pred.c", "src/focus_motion.c"],
    "af_control": ["../tests/test_af_control.c", "src/af_control.c", "src/focus_map.c", "src/focus_dist.c"],
    "io_guard": ["hosttest/test_io_guard.c", "src/io_guard.c"],
    "af_reconciliation": ["../tests/test_af_reconciliation.c", "src/af_reference.c", "src/af_completion.c", "src/af_control.c", "src/focus_map.c", "src/focus_dist.c"],
    "af_lifecycle": ["-DEA9_SIM_MOTOR", "-DEA9_NO_LOG", "-ffunction-sections", "-fdata-sections", "-Wl,-dead_strip", "hosttest/test_af_lifecycle.c", "hosttest/sim_motor.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c", "src/lens_aperture.c", "src/servo.c", "src/af_control.c", "src/af_reference.c", "src/af_completion.c", "src/io_guard.c", "src/focus_map.c", "src/focus_dist.c", "src/focus_pred.c", "src/focus_motion.c"],
    "af_hardening": ["-DEA9_HOST_IRQ_TEST", "-DEA9_SIM_MOTOR", "-DEA9_NO_LOG", "-ffunction-sections", "-fdata-sections", "-Wl,-dead_strip", "hosttest/test_af_hardening.c", "hosttest/sim_motor.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c", "src/lens_aperture.c", "src/servo.c", "src/af_control.c", "src/af_reference.c", "src/af_completion.c", "src/io_guard.c", "src/focus_map.c", "src/focus_dist.c", "src/focus_pred.c", "src/focus_motion.c"],
    "profile": ["../tests/test_profile.c", "hosttest/shim.c", "src/emount.c", "src/emount_packets.c", "src/lens_profile.c", "src/lens_aperture.c"],
}
# Reuse the production-main lifecycle/dispatch checks with the new backend.
for old, new in [("af_lifecycle", "factory_lifecycle"), ("af_hardening", "factory_hardening")]:
    tests[new] = ["-DEA9_FACTORY_AF", "-DUPSTREAM_PROFILE=FACTORY_PROFILE"] + [
        part if part != "src/servo.c" else "src/factory_servo.c" for part in tests[old]
    ] + ["src/factory_af.c"]
tests['af_queue_retarget'] = [part if part != 'hosttest/test_af_lifecycle.c'
                            else 'hosttest/test_af_queue_retarget.c' for part in tests['factory_lifecycle']]
tests['event_queue'] = ['-DEA9_NO_LOG', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                        'hosttest/test_event_queue.c', 'hosttest/shim.c', 'src/emount_packets.c',
                        'src/lens_profile.c', 'src/lens_aperture.c']
tests['factory_retarget'] = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                            'hosttest/test_factory_retarget.c', 'src/factory_servo.c',
                            'src/factory_af.c', 'src/io_guard.c', 'src/focus_map.c']
tests['focus_motion'] = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                         'hosttest/test_focus_motion.c', 'src/focus_motion.c']
tests['motion_telemetry'] = [part if part != 'hosttest/test_af_lifecycle.c'
                           else 'hosttest/test_motion_telemetry.c' for part in tests['factory_lifecycle']]
for name, files in tests.items():
    binary = OUT / f"test_{name}"
    subprocess.run(COMMON + files + ["-o", str(binary)], cwd=BASE, check=True)
    if name == "profile":
        continue
    variants = [["nobody"], ["slowbody"]] if name == "nobody" else [[]]
    if name == 'af_queue_retarget': variants = [[x] for x in ['stop-fifo', 'stop-pending', 'stop-coalesce', 'stop-reordered', 'repeat', 'single']]
    if name == 'factory_retarget': variants = [[str(x)] for x in range(4)]
    if name == 'focus_motion': variants = [[x] for x in ['coast','slow','reversal','stale','vd-gap','no-vd','wrap','limits','reset','burst','resume-history','sub-resolution-jitter','slow-frames']]
    if name == 'motion_telemetry': variants = [[x] for x in ['coast40','coast5952','reverse-stop','gap-reset']]
    if name == "io_guard": variants = [[x] for x in ["ready", "timeout", "wrap", "frozen"]]
    if name == "af_lifecycle": variants = [[str(x)] for x in range(13)]
    if name == "af_hardening": variants = [[str(x)] for x in range(21)]
    if name == "factory_hardening": variants = [[str(x)] for x in range(21)]
    # Legacy cases 11/12 assert speed/dwell/band arrival, which factory replaces
    # with crossing; the new scripted wrapper suite tests its arrival guards.
    if name == "factory_lifecycle": variants = [[str(x)] for x in range(11)]
    if name == "factory_servo": variants = [[x] for x in ["success", "wrap", "retarget", "stop", "stop-cross", "late-stop", "early-fault", "late-fault", "gap", "frozen", "runaway", "final-drift", "wrong-way", "stall", "timeout", "dry", "invalid-positive", "invalid-negative", "resolution", "resolution-stop", "progress-timeout", "deadline-stop", "retarget-limit-stop", "runaway-stop", "wrong-way-stop", "mid-invalid", "final-invalid", "repeat-quantized", "repeat-stop", "retarget-budget"]]
    for args in variants:
        subprocess.run([str(binary)] + args, check=True)
# Compile actual sensor and PWM drivers against DFP-shaped register memory.
mmio = OUT / "test_mmio_faults"
subprocess.run(["cc", "-std=gnu99", "-O1", "-Wall", "-Wextra", "-ffunction-sections", "-fdata-sections", "-Wl,-dead_strip", "-DEA9_AF_BUILD", "-D__SAMD21E17A__", "-Isrc", "-I../../tools/firmware-deps/samd21-dfp-2/samd21a/include", "-I../../tools/firmware-deps/CMSIS_5-5.9.0/CMSIS/Core/Include", "-include", "hosttest/mmio/registers.h", "hosttest/mmio/test_faults.c", "src/io_guard.c", "src/motor.c", "src/abs_encoder.c", "src/vdd.c", "src/em_uart.c", "-o", str(mmio)], cwd=BASE, check=True)
for case in ["encoder", "encoder-reset", "adc", "burst-frozen", "uart", "uart-rx", "pwm", "release", "irq", "irq-masked", "frozen"]:
    subprocess.run([str(mmio), case], check=True)
delays = OUT / "test_mmio_delays"
subprocess.run(["cc", "-std=gnu99", "-O1", "-Wall", "-Wextra", "-ffunction-sections", "-fdata-sections", "-Wl,-dead_strip", "-DEA9_AF_BUILD", "-D__SAMD21E17A__", "-Isrc", "-I../../tools/firmware-deps/samd21-dfp-2/samd21a/include", "-I../../tools/firmware-deps/CMSIS_5-5.9.0/CMSIS/Core/Include", "-include", "hosttest/mmio/registers.h", "hosttest/mmio/test_delays.c", "src/io_guard.c", "src/motor.c", "src/delay.c", "-o", str(delays)], cwd=BASE, check=True)
for case in ["us", "ms", "cycles"]:
    subprocess.run([str(delays), case], check=True)
startup = OUT / "test_mmio_startup"
subprocess.run(["cc", "-std=gnu99", "-O1", "-Wall", "-Wextra", "-ffunction-sections", "-fdata-sections", "-Wl,-dead_strip", "-DEA9_AF_BUILD", "-D__SAMD21E17A__", "-Isrc", "-I../../tools/firmware-deps/samd21-dfp-2/samd21a/include", "-I../../tools/firmware-deps/CMSIS_5-5.9.0/CMSIS/Core/Include", "-include", "hosttest/mmio/registers.h", "hosttest/mmio/test_startup.c", "src/io_guard.c", "src/motor.c", "src/clock.c", "src/em_eic.c", "src/em_uart.c", "-o", str(startup)], cwd=BASE, check=True)
for case in range(11):
    subprocess.run([str(startup), str(case)], check=True)
inventory = json.loads((ROOT / "profiles/requested-lenses.json").read_text())["lenses"]
cli = ROOT / "apps/macos/.build/out/Products/Debug/ea9ctl"
if with_af:
    subprocess.run(COMMON + ["-DEM_FW_VERSION_BCD=0x28u", "-DEA9_PROFILE_ADDRESS=0x9f00u"] + tests["profile"]
                   + ["-o", str(OUT / "test_af_profile")], cwd=BASE, check=True)
# This isolated generated library is never the owner's normal app state.
# Materialize it offline, then select 50mm for the zoom fixture as well.
state = OUT / 'state'
seed = OUT / 'seed.bin'
if seed.exists(): seed.unlink()
subprocess.run([str(cli), '--state-directory', str(state), 'prepare', 'contax-zeiss-50-f1-4', str(seed)], check=True)
profile_file = state / 'profiles.json'
library = json.loads(profile_file.read_text())
for p in library['profiles']:
    if p['kind'] == 'zoom': p['activeFocalLengthMM'] = 50
profile_file.write_text(json.dumps(library, indent=2) + '\n')
for lens in inventory:
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

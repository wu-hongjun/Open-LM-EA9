#!/usr/bin/env python3
"""Offline AF 2.9 capture-service boundary comparison, not camera qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unicorn

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
out = parser.parse_args().output.resolve()
sys.path.insert(0, str(ROOT / 'research/stock-1.8'))
from config import configure, FIRMWARE_SHA256
configure(ROOT / 'firmware/recovery/stock-1.8.0/application.bin', out, 'clang')
from oracle import Machine

factory = []
for window_open in [False, True]:
    calls = []
    def send(machine):
        calls.append({'length': machine.calls[-1]['args'][1]})
        return -7
    machine = Machine({0x91c4: 0, 0x91ac: 0, 0x51c8: 0, 0x9180: send})
    machine.u.mem_map(0x41004000, 0x1000)
    machine.u.mem_map(0x60000000, 0x1000)
    machine.u.mem_write(0x20000000, bytes(2048))
    frame = bytearray(48)
    frame[0:6] = bytes([0xf0, 48, 0, 1, 0, 6])
    machine.u.mem_write(0x20000000, bytes(frame))
    for off, value, width in [(0x522, 1, 1), (0x51f, 4, 1), (0x520, 3, 1),
                             (0x51e, 0, 1), (0x660, 0x20000000, 4), (0x655, 48, 1)]:
        machine.set(0x20000000 + off, value, width)
    if window_open:
        machine.set(0x41004420, 4, 4)
        machine.run(0x53a4, 4)  # Actual CS callback sets the interlock in phase 3.
    interlock = machine.get(0x2000051e, 1)
    machine.run(0x54d8)  # Actual delayed status06 sender.
    assert interlock == int(window_open)
    assert calls == ([] if window_open else [{'length': 48}])
    factory.append({'bodyReceiveWindowOpen': window_open,
                    'interlockAfterCallback': interlock,
                    'status06Transmits': len(calls)})

base = ROOT / 'firmware/ea9'
sources = ['hosttest/test_capture_boundary.c', 'hosttest/shim.c', 'src/emount_packets.c',
           'src/lens_profile.c', 'src/lens_aperture.c', 'src/io_guard.c']
flags = ['clang', '-std=gnu99', '-O1', '-Wall', '-Wextra', '-Werror', '-Wno-over-aligned',
         '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
         '-ffunction-sections', '-fdata-sections', '-Wl,-dead_strip',
         '-DEA9_NO_LOG', '-DEA9_AF_BUILD', '-Ihosttest', '-Isrc']
candidate = ROOT / 'firmware/candidates/2.9.0/contax-zeiss-50-f1-4.bin'
image = candidate.read_bytes()
assert hashlib.sha256(image).hexdigest() == 'c5fac2eeb7b8c26833b37555f25598352c850f224dba1d091379c09cd9a6ffc3'

custom = {}
for label in ['current', 'host-only-window-guard']:
    directory = out / label / 'sources'
    extra = []
    for path in set(base.rglob('*.h')) | {base / s for s in sources} | {base / 'src/emount.c'}:
        destination = directory / path.relative_to(base)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    # Event injection at the host delay boundary only; production delays and
    # responder are unchanged. Both baseline/control use identical injection.
    shim = directory / 'hosttest/shim.c'
    text = shim.read_text()
    before = 'void delay_us(uint32_t us) { (void)us; }'
    assert text.count(before) == 1
    shim.write_text(text.replace(before,
        'void host_probe_delay_us(uint32_t us);\nvoid delay_us(uint32_t us) { host_probe_delay_us(us); }'))
    if label != 'current':
        emount = directory / 'src/emount.c'
        text = emount.read_text()
        before = 'void em_pump_status(void)\n{'
        assert text.count(before) == 1
        text = text.replace(before, before + '\n\tif (em_pin_level(EM_PIN_BODY_CS)) return;')
        emount.write_text(text)
        extra = ['-DEA9_PROBE_WINDOW_GUARD']
    exe = out / (label + '-probe')
    subprocess.run(flags + extra + sources + ['-o', str(exe)], cwd=directory, check=True)
    result = subprocess.run([str(exe), str(candidate)], capture_output=True, text=True, check=True)
    custom[label] = json.loads(result.stdout)

assert custom['current']['statusFramesWhileReceiveWindowOpen'] == 2
assert custom['host-only-window-guard']['statusFramesWhileReceiveWindowOpen'] == 0
assert all(case['status06FramesAfterReceiveOpensInGap'] == 1 for case in custom.values())
inputs = {base / s for s in sources} | set(base.rglob('*.h')) | {base / 'src/emount.c', Path(__file__).resolve()}
inputs |= {ROOT / name for name in ['research/stock-1.8/config.py', 'research/stock-1.8/oracle.py', 'research/stock-1.8/requirements.txt']}
evidence = {
    'dateLocal': '2026-10-12', 'timezone': 'America/New_York',
    'status': 'finite-protocol-scheduling-difference-reproduced-hardware-cause-unproven',
    'sourceApplicationSHA256': FIRMWARE_SHA256,
    'candidateImageSHA256': hashlib.sha256(image).hexdigest(),
    'factoryOriginalInstructionCases': factory,
    'customResponderCases': custom,
    'hardwareReportsSent': 0, 'productionFirmwareChanged': False,
    'cameraQualified': False, 'ownerFreezeCauseProven': False,
    'probeExitCodes': {'current': 0, 'host-only-window-guard': 0},
    'hostTestSanitizers': ['address', 'undefined'],
    'unicornVersion': unicorn.__version__,
    'nativeCompiler': subprocess.run(['clang', '--version'], capture_output=True, text=True, check=True).stdout.splitlines()[0],
    'factoryContract': 'Seeded initialized mode 4 / phase 3 / callbacks enabled; actual 0x53a4 CS-rise callback and 0x54d8 status06 sender, UART driver/RX setup cut, dummy register memory. Not full capture flow or ordinary reachability.',
    'customContract': 'Actual emount responder with completed synthetic initialization, supplied CS-rise/VD callbacks and immediate host transmit; no actual main, motor, concurrent IRQ, UART timing or camera.',
    'syntheticCaptureContract': 'Upstream a9 II documented nine-ID order; synthetic checksum-valid 11-byte frames, each serviced before the next. Not recovered full request payloads or A7C II traffic.',
    'hostBoundaryInstrumentation': 'Both copies inject a supplied CS-rise callback from the host delay shim during the 300us status gap; actual elapsed time and concurrent IRQs are not simulated. Shared shim and production sources remain unchanged.',
    'guardControl': 'One receive-window check inserted only at status-pump entry in an ignored host copy. It suppresses already-open-window sends but fails to suppress status06 when CS rises during the gap. Not a firmware patch or factory phase-machine implementation.',
    'sourceSHA256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)},
    'upstreamBasisSHA256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in [
        'references/upstream/weiziqian/E-mount-protocol-RE/docs/msg_0x1B.md',
        'references/upstream/weiziqian/E-mount-protocol-RE/README.md']},
}
(out / 'results.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps({k: evidence[k] for k in ['status', 'factoryOriginalInstructionCases',
      'customResponderCases', 'hardwareReportsSent', 'productionFirmwareChanged', 'ownerFreezeCauseProven']}, indent=2))

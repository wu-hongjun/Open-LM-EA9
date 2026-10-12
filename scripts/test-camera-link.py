#!/usr/bin/env python3
"""Offline camera-link fault tests with real drivers and frozen 2.8 controls."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
out = parser.parse_args().output.resolve()
out.mkdir(mode=0o700, parents=True, exist_ok=False)
base = ROOT / 'firmware/ea9'
record = json.loads((ROOT / 'firmware/candidates/2.8.0/regression-inputs.json').read_text())
frozen = out / 'frozen28/firmware/ea9'
for name, digest in record['files'].items():
    data = subprocess.run(['git', 'show', record['sourceGitCommit'] + ':' + name], cwd=ROOT, capture_output=True, check=True).stdout
    if hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError('Frozen source digest mismatch: ' + name)
    destination = out / 'frozen28' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
for name in ['hosttest/test_camera_link.c', 'hosttest/mmio/test_link_faults.c', 'hosttest/mmio/test_startup.c', 'hosttest/mmio/test_delays.c']:
    (frozen / name).write_bytes((base / name).read_bytes())
# Test-boundary instrumentation only: discard a chosen frame in the old void
# send shim. The original production code/headers are not changed in this control.
shim = frozen / 'hosttest/shim.c'
text = shim.read_text()
before = 'void em_uart_send(const uint8_t *buf, uint16_t len)\n{'
assert text.count(before) == 1
text = text.replace(before, 'int host_tx_fail_id = -1;\n' + before + '\n\tif (host_tx_fail_id == buf[5]) return;')
text = text.replace('int em_pin_level(uint8_t pin)\n{', 'int host_vd_reads;\nint em_pin_level(uint8_t pin)\n{\n\tif (pin == EM_PIN_BODY_VD) ++host_vd_reads;')
shim.write_text(text)
flags = ['cc', '-std=gnu99', '-O1', '-Wall', '-Wextra', '-Werror', '-Wno-over-aligned',
         '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
         '-ffunction-sections', '-fdata-sections', '-Wl,-dead_strip']
mmio = ['-DEA9_AF_BUILD', '-D__SAMD21E17A__', '-Isrc',
        '-I' + str(ROOT / 'tools/firmware-deps/samd21-dfp-2/samd21a/include'),
        '-I' + str(ROOT / 'tools/firmware-deps/CMSIS_5-5.9.0/CMSIS/Core/Include'),
        '-include', 'hosttest/mmio/registers.h']
groups = {
    'uart': (mmio, ['hosttest/mmio/test_link_faults.c', 'src/io_guard.c', 'src/motor.c', 'src/em_uart.c']),
    'startup': (mmio, ['hosttest/mmio/test_startup.c', 'src/io_guard.c', 'src/motor.c', 'src/clock.c', 'src/em_eic.c', 'src/em_uart.c']),
    'delay': (mmio, ['hosttest/mmio/test_delays.c', 'src/io_guard.c', 'src/motor.c', 'src/delay.c']),
    'session': (['-DEA9_SIM_MOTOR', '-DEA9_NO_LOG', '-DEA9_FACTORY_AF', '-DEA9_AF_BUILD', '-Ihosttest', '-Isrc'],
                ['hosttest/test_camera_link.c', 'hosttest/sim_motor.c', 'hosttest/shim.c', 'src/emount.c', 'src/emount_packets.c',
                 'src/lens_profile.c', 'src/lens_aperture.c', 'src/factory_servo.c', 'src/factory_af.c', 'src/af_control.c',
                 'src/af_reference.c', 'src/af_completion.c', 'src/io_guard.c', 'src/focus_map.c', 'src/focus_dist.c', 'src/focus_motion.c']),
}
cases = {
    'uart': ['encoder', 'adc', 'pwm', 'combined', 'mid-adc', 'uart', 'clock', 'timebase', 'eic', 'stall', 'frozen', 'healthy'],
    'startup': [str(i) for i in range(14)],
    'delay': ['us', 'ms', 'cycles', 'adc-us', 'adc-ms'],
    'session': ['normal', 'fault-home', 'fault-idle', 'fail-init', 'fail-tail', 'fail-shutdown', 'restart-init'],
}
negative = {
    'uart': {case: 'motion fault suppressed healthy UART' for case in ['encoder', 'adc', 'pwm', 'combined', 'mid-adc']},
    'startup': {str(i): 'motion fault blocked link initialization' for i in range(11, 14)},
    'delay': {case: 'motion fault skipped protocol delay' for case in ['adc-us', 'adc-ms']},
    'session': {'fail-init': 'failed final init armed handshake', 'fail-tail': 'unsent event tail consumed', 'fail-shutdown': 'failed shutdown falsely acknowledged', 'fault-idle': 'motion fault skipped shutdown VD wait', 'restart-init': 'new initializer retained old status handshake'},
}
results = []
for group, (extra, sources) in groups.items():
    for label, directory in [('current', base), ('frozen28', frozen)]:
        exe = out / (group + '-' + label)
        subprocess.run(flags + extra + (['-DEA9_FROZEN28'] if label == 'frozen28' else []) + sources + ['-o', str(exe)], cwd=directory, check=True)
        selected = cases[group] if label == 'current' else negative[group]
        for case in selected:
            args = [str(exe), case]
            if group == 'session': args.append(str(ROOT / 'firmware/candidates/2.8.0/contax-zeiss-50-f1-4.bin'))
            run = subprocess.run(args, capture_output=True, text=True)
            expected = 0 if label == 'current' else 1
            if run.returncode != expected or (expected and negative[group][case] not in run.stderr):
                raise RuntimeError(f'{label}/{group}/{case}: {run.returncode}\n{run.stdout}{run.stderr}')
            results.append({'source': label, 'group': group, 'case': case, 'exitCode': run.returncode,
                            'output': run.stdout.strip(), 'diagnostic': run.stderr.strip()})
inputs = set(base / s for _, sources in groups.values() for s in sources)
inputs.add(base / 'src/main.c')  # Included by the composed session translation unit.
inputs.update(base.rglob('*.h'))
inputs.add(Path(__file__).resolve())
evidence = {
    'scope': 'Finite register-backed actual drivers and composed production startup/reference/shutdown routines; not physical camera timing or full reset entry',
    'hardwareReportsSent': 0, 'cameraQualified': False, 'frozenSourceGitCommit': record['sourceGitCommit'],
    'frozenShimInstrumentation': 'Host transmit boundary discards a chosen frame; host VD reads counted. Original production source and headers remain exact',
    'passingCurrentCases': sum(r['source'] == 'current' for r in results),
    'detectedFrozenCases': sum(r['source'] == 'frozen28' for r in results), 'cases': results,
    'sourceSHA256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)},
}
(out / 'results.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps({k: evidence[k] for k in ['passingCurrentCases', 'detectedFrozenCases', 'hardwareReportsSent', 'cameraQualified']}, indent=2))

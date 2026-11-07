#!/usr/bin/env python3
"""Test camera-dial aperture metadata through the production protocol sources."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'firmware/hosttest'
FIELDS = ('emount.c', 'emount_packets.c', 'optical_file.c', 'reported_aperture.c')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if not __debug__:
        raise SystemExit('Run without Python optimization.')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    from datetime import datetime
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    if a.build is None:
        a.build = ROOT / 'artifacts/private' / ('firmware-test-build-' + stamp)
        subprocess.run(['python3', str(ROOT / 'scripts/build-firmware.py'), '--output', str(a.build)], check=True)
    if a.output is None:
        a.output = ROOT / 'artifacts/private' / ('firmware-tests-' + stamp)
    build, out = a.build.resolve(), a.output.resolve()
    assert out.is_relative_to(ROOT / 'artifacts/private')
    manifest = json.loads((build / 'manifest.json').read_text())
    wide = manifest['loaderVersion'] == [4,6,0]
    image_name = 'biotar-wide-aperture.bin' if wide else 'biotar-camera-aperture.bin'
    assert sha(build / image_name) == manifest['imageSHA256']
    for name, digest in manifest['sources'].items():
        assert sha(build / 'src' / name) == digest, name
    out.mkdir(exist_ok=False)

    host = out / 'host'
    shutil.copytree(build / 'tools/hosttest', host)
    sam = host / 'sam.h'
    s = sam.read_text()
    assert s.count('static inline void __disable_irq(void) {}') == 1
    s = s.replace('static inline void __disable_irq(void) {}', '''#include <stdint.h>
extern uint32_t host_primask;
static inline void __disable_irq(void) { host_primask = 1; }
static inline uint32_t __get_PRIMASK(void) { return host_primask; }
static inline void __set_PRIMASK(uint32_t key) { host_primask = key; }''')
    s = s.replace('static inline void __enable_irq(void) {}',
                  'static inline void __enable_irq(void) { host_primask = 0; }')
    sam.write_text(s)
    shim = host / 'shim.c'
    s = shim.read_text()
    marker = 'void em_uart_send(const uint8_t *buf, uint16_t len)\n{'
    assert s.count(marker) == 1
    s = s.replace(marker, '''uint32_t host_primask;
void (*host_tx_hook)(void);
void em_uart_send(const uint8_t *buf, uint16_t len)
{
    if (host_tx_hook) {
        void (*callback)(void) = host_tx_hook;
        host_tx_hook = 0;
        callback();
    }''')
    shim.write_text(s)

    flags = ['-std=gnu99', '-Os', '-DNDEBUG', '-DEA9_NO_LOG', '-Wall', '-Wextra',
             '-Werror', '-fsanitize=address,undefined', '-fno-sanitize-recover=all']
    results = []
    for case in ('production', 'missing-input-hook', 'publish-from-irq'):
        src = out / case
        shutil.copytree(build / 'src', src)
        if case == 'missing-input-hook':
            path = src / 'emount.c'
            s = path.read_text()
            assert s.count('\t\treported_aperture_offer(rx, n);') == 1
            path.write_text(s.replace('\t\treported_aperture_offer(rx, n);', '\t\t(void)rx;'))
        elif case == 'publish-from-irq':
            path = src / 'reported_aperture.c'
            s = path.read_text()
            old = 'if (value >= EM_APERTURE_MAX && value <= EM_APERTURE_MIN) pending = value;'
            assert s.count(old) == 1
            path.write_text(s.replace(old, 'if (value >= EM_APERTURE_MAX && value <= EM_APERTURE_MIN) {\n'
                                          '        pending = value;\n        reported_aperture_commit();\n    }'))
        binary = out / (case + '-test')
        subprocess.run(['clang', *flags, f'-I{host}', f'-I{src}', str(HERE / 'test_camera_aperture.c'),
                        str(shim), *(str(src / name) for name in FIELDS), '-o', str(binary)], check=True)
        r = subprocess.run([str(binary)], capture_output=True, text=True, timeout=20)
        assert (r.returncode == 0) == (case == 'production'), (case, r.stdout, r.stderr)
        if case == 'production':
            assert not r.stderr, r.stderr
            print(r.stdout, end='')
        else:
            expected = ('sent_n == start + 1 && u16(sent[start] + 6) == 5120'
                        if case == 'missing-input-hook' else
                        'u16(em_msg_05 + 6) == value && u16(em_msg_05 + 8) == value')
            assert r.returncode == 2 and r.stderr.rstrip().endswith(expected), (case, r.stderr)
        results.append({'case': case, 'exitCode': r.returncode,
                        'expected': 'passes' if case == 'production' else 'rejected',
                        'failedAssertion': None if case == 'production' else expected})

    # Keep the upstream broad protocol/servo/focus tests, adjusting profile literals.
    suite = host / 'test_emount.c'
    s = suite.read_text()
    replacements = {
        'const uint8_t MAXD = 0x16, MIND = 0x16;': ('const uint8_t MAXD = 0x0c, MIND = 0x50;' if wide else 'const uint8_t MAXD = 0x18, MIND = 0x48;'),
        'em_msg_08[0x17] != 0x50': 'em_msg_08[0x17] != 0x58',
        '{ 0x32, 0x16 }, { 0x34, 0x16 }': ('{ 0x32, 0x0c }, { 0x34, 0x0c }' if wide else '{ 0x32, 0x18 }, { 0x34, 0x18 }'),
        '{ 0x39, 0x16 }, { 0x3A, 0x16 }': ('{ 0x39, 0x0c }, { 0x3A, 0x50 }' if wide else '{ 0x39, 0x18 }, { 0x3A, 0x48 }'),
    }
    for old, new in replacements.items():
        assert s.count(old) == 1, old
        s = s.replace(old, new)
    suite.write_text(s)
    binary = out / 'broad-protocol-test'
    subprocess.run(['clang', *flags, f'-I{host}', f'-I{build / "src"}', str(suite), str(shim),
                    *(str(build / 'src' / name) for name in FIELDS), '-o', str(binary)], check=True)
    r = subprocess.run([str(binary)], capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, (r.stdout, r.stderr)
    print(r.stdout, end='')

    for test, sources in [
        ('test_servo', ['tools/hosttest/sim_motor.c', 'src/servo.c']),
        ('test_focus', ['src/focus_map.c']),
        ('test_focus_dist', ['src/focus_dist.c']),
    ]:
        binary = out / test
        subprocess.run(['clang', *flags, f'-I{host}', f'-I{build / "src"}',
                        str(build / f'tools/hosttest/{test}.c'),
                        *(str(build / source) for source in sources), '-lm', '-o', str(binary)], check=True)
        r = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, (test, r.stdout, r.stderr)
    # This release, like 4.4, compiles diagnostic flash writes out. The
    # upstream no-body fixture expects a persistent tally; keep its wait/
    # frame-sync assertions, but require no tally from this release build.
    nobody = host / 'test_nobody.c'
    s = nobody.read_text()
    old = '''ok(host_tally_n == 1, "exactly one tally mark");
\t\tok(host_tally_n == 1 && host_tally_code == 0xB6,
\t\t   "and it is the NO BODY mark");'''
    assert s.count(old) == 1
    nobody.write_text(s.replace(old, '''ok(host_tally_n == 0, "diagnostic-free release writes no tally");
\t\tok(host_millis >= 3000, "waited until chip select rose");'''))
    for name, cases in [('test_nobody', ('nobody', 'slowbody')), ('test_init', ('',))]:
        binary = out / name
        subprocess.run(['clang', *flags, f'-I{host}', f'-I{build / "src"}',
                        str(host / f'{name}.c'), str(shim),
                        *(str(build / 'src' / source) for source in FIELDS), '-o', str(binary)], check=True)
        for case in cases:
            command = [str(binary)] + ([case] if case else [])
            r = subprocess.run(command, capture_output=True, text=True, timeout=10)
            assert r.returncode == 0, (name, case, r.stdout, r.stderr)
    result = {'status': 'passed-offline-camera-aperture-tests', 'candidateSHA256': manifest['imageSHA256'],
              'productionAndControls': results, 'hardwareReportsSent': 0,
              'scope': 'Synthetic frames, supplied UART/CS/time and simulated motor; camera dial, exposure and autofocus remain hardware checks.'}
    (out / 'results.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Broad protocol, servo, focus mapping and focus distance tests passed.')


if __name__ == '__main__':
    main()

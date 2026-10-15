#!/usr/bin/env python3
"""Probe pinned upstream 3.1 readiness/aperture boundaries without hardware.

Requires the materialized build from build-upstream-baseline.py. Its C sources,
headers and host shim are checked against the committed build provenance before
copying to a new output directory. No firmware artifacts or USB state are changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda data: hashlib.sha256(data).hexdigest()
FIXTURE = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "emount.h"
#include "emount_packets.h"
extern int sent_n, sent_overflow;
extern uint8_t sent[][256];
void host_body_frame(const uint8_t *, uint16_t);
void host_frame_sync(void);

static unsigned read16(unsigned off) {
    return ea9_data[off] | ((unsigned)ea9_data[off + 1] << 8);
}
static void request(uint8_t id, uint8_t seq, uint8_t capability) {
    uint8_t f[11] = {0xF0, 11, 0, 2, seq, id, 0, capability, 0, 0, 0x55};
    uint16_t sum = 0;
    for (unsigned i = 1; i <= 7; i++) sum += f[i];
    f[8] = (uint8_t)sum; f[9] = (uint8_t)(sum >> 8);
    host_body_frame(f, sizeof(f)); em_poll();
}
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    const int initial = strcmp(argv[1], "init-only") == 0;
    const int complete = strncmp(argv[1], "complete-", 9) == 0;
    const int omit = strstr(argv[1], "omit") != NULL;
    static const uint8_t ids[] = {1, 7, 0x0B, 8, 9, 0x0D, 0x10, 0x0A};
    em_init();
    if (!initial) {
        unsigned count = complete ? sizeof(ids) : sizeof(ids) - 1;
        for (unsigned i = 0; i < count; i++)
            request(ids[i], (uint8_t)(0x40 + i), ids[i] == 8 && omit ? 0x80 : 0);
    }
    int before = sent_n;
    host_frame_sync(); em_poll();
    unsigned aperture05 = read16(EA9_OFF_05 + 6);
    unsigned aperture28 = read16(EA9_OFF_28 + 15);
    unsigned status = (unsigned)(sent_n - before);
    unsigned expected28 = initial || omit ? 0 : EM_APERTURE_NOW;
    int passed = em_handshake_done == complete && status == (complete ? 2u : 0u)
        && aperture05 == EM_APERTURE_NOW && aperture28 == expected28
        && !sent_overflow;
    if (complete) passed &= sent[before][5] == 5 && sent[before + 1][5] == 6;
    printf("{\"case\":\"%s\",\"handshakeDone\":%s,\"statusFramesOnVD\":%u,"
           "\"message05ApertureAV\":%u,\"message28OptionalApertureAV\":%u,"
           "\"message07LensID\":%u,\"passed\":%s}\n", argv[1],
           em_handshake_done ? "true" : "false", status, aperture05, aperture28,
           read16(EA9_OFF_07 + 15), passed ? "true" : "false");
    return passed ? 0 : 1;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.parent.is_dir():
        raise SystemExit('Output must be a new directory under an existing parent.')
    provenance_path = ROOT/'docs/evidence/upstream-baseline-build-2026-10-14.json'
    provenance = json.loads(provenance_path.read_text())
    source = ROOT/'firmware/upstream-baseline/build/50f14'
    checksums = dict(provenance['results']['50f14']['sources'])
    prefix = 'upstream/weiziqian/E-mount-impl-on-Techart-EA9/'
    for line in (ROOT/'references/checksums.sha256').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if name in {prefix + 'tools/hosttest/' + n for n in
                    ('shim.c', 'sam.h', 'sam_servo.h')}:
            checksums[name[len(prefix):]] = digest
    for name, digest in checksums.items():
        if SHA((source/name).read_bytes()) != digest:
            raise SystemExit('Source checksum mismatch: ' + name)
    expected = '528225e6f6472da0d92479da2b3e475a32f82735347231b6dc7c3d0dc7e8b39f'
    if SHA((ROOT/'firmware/candidates/3.1.0/contax-zeiss-50-f1-4.bin').read_bytes()) != expected:
        raise SystemExit('Pinned camera-test image mismatch.')
    out.mkdir()
    snapshot = out/'snapshot'
    for name in checksums:
        target = snapshot/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/name, target)
    (out/'probe.c').write_text(FIXTURE)
    command = ['clang', '-std=gnu99', '-O2', '-DNDEBUG', '-DEA9_NO_LOG',
               '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
               '-fno-omit-frame-pointer', '-I'+str(snapshot/'tools/hosttest'),
               '-I'+str(snapshot/'src'), str(out/'probe.c'),
               str(snapshot/'tools/hosttest/shim.c'), str(snapshot/'src/emount.c'),
               str(snapshot/'src/emount_packets.c'), '-o', str(out/'probe')]
    subprocess.run(command, check=True, capture_output=True, text=True)
    cases = []
    for name in ('init-only', 'partial-report', 'partial-omit',
                 'complete-report', 'complete-omit'):
        run = subprocess.run([str(out/'probe'), name], check=True,
                             capture_output=True, text=True, timeout=10)
        if run.stderr:
            raise SystemExit('Unexpected diagnostic output: ' + run.stderr)
        cases.append(json.loads(run.stdout))
    result = {
        'status': 'passed-offline-boundary-probe-physical-cause-unproven',
        'upstreamCommit': provenance['upstreamCommit'],
        'imageSHA256': expected, 'fixtureSHA256': SHA(FIXTURE.encode()),
        'buildProvenanceSHA256': SHA(provenance_path.read_bytes()),
        'compiledSourceSHA256': {name: checksums[name] for name in
            ('src/emount.c', 'src/emount_packets.c', 'src/emount.h', 'tools/hosttest/shim.c')},
        'hostOptimization': '-O2 -DNDEBUG -DEA9_NO_LOG',
        'sanitizers': ['AddressSanitizer', 'UndefinedBehaviorSanitizer'],
        'cases': cases, 'hardwareReportsSent': 0, 'firmwareChanged': False,
        'limitations': [
            'Synthetic checksum-valid requests and scripted GPIO/VD/UART; not recovered A7C II traffic.',
            'The real main loop, startup, sensor, motor, power and IRQ timing are not executed.',
            'Handshake flag and status suppression do not prove homing readiness or camera acceptance.',
            'Optional message 0x28 zero does not mean all aperture fields are unknown.',
            'Neither an incomplete handshake nor an aperture capability-bit cause is proven on hardware.',
        ],
    }
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

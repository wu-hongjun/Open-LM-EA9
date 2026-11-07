#!/usr/bin/env python3
"""Configuration rejection and custom lens bytes through the production C responder."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from firmware_config import load_config

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'firmware/configurations/contax-50-f14.example.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True, help='Custom build output from build-firmware.py.')
    parser.add_argument('--negative-control-build', type=Path,
                        help='Unmodified 4.5 build; must fail the custom focal-length assertion.')
    args = parser.parse_args()
    original = json.loads(EXAMPLE.read_text())
    with tempfile.TemporaryDirectory(prefix='openlensadapter-config-') as temp:
        config_path = Path(temp) / 'config.json'
        mutations = [
            ('published-version', lambda c: c.update(version=[4, 5, 0])),
            ('path-traversal', lambda c: c.update(target='../lm-ea9')),
            ('focal-overflow', lambda c: c['lens'].update(focalMM10=65536)),
            ('name-overflow', lambda c: c['lens'].update(name='x' * 64)),
            ('name-control', lambda c: c['lens'].update(name='bad\nname')),
            ('negative-aperture', lambda c: c['reportedAperture'].update(maximumAV=-1)),
            ('invalid-boot-aperture', lambda c: c['reportedAperture'].update(initialAV=4096)),
            ('unsupported-nameplate', lambda c: c['reportedAperture'].update(maximumAV=6144, initialAV=6144)),
            ('unknown-field', lambda c: c.update(unsafeFlash=True)),
        ]
        for name, mutate in mutations:
            config = copy.deepcopy(original)
            mutate(config)
            config_path.write_text(json.dumps(config))
            try:
                load_config(config_path, ROOT / 'firmware/releases')
            except ValueError:
                pass
            else:
                raise AssertionError('Accepted invalid configuration: ' + name)

    build = args.build.resolve()
    manifest = json.loads((build / 'manifest.json').read_text())
    assert hashlib.sha256((build / 'custom-firmware.bin').read_bytes()).hexdigest() == manifest['imageSHA256']
    for name, digest in manifest['sources'].items():
        assert hashlib.sha256((build / 'src' / name).read_bytes()).hexdigest() == digest
    assert manifest['lens'] == original['lens'] and manifest['reportedAperture'] == original['reportedAperture']
    assert manifest['cameraQualified'] is False and manifest['uploadQualified'] is False
    # Use the real responder/mailbox, with only UART/time/CS supplied by the host shim.
    # This also checks the wire-frame checksum after replacing a shorter lens name.
    code = r'''
#include "protocol_fixture.h"
#include "emount_packets.h"
int main(void) {
    em_init();
    CHECK(em_focal_mm10 == 500 && u16(em_msg_05 + 0x1e) == 500);
    CHECK(em_msg_08[0x16] == 0 && em_msg_08[0x17] == 0x50);
    CHECK(u16(em_msg_05 + 6) == 4352);
    CHECK(u16(em_msg_08 + 6) == 4224 && u16(em_msg_08 + 8) == 6400);
    uint8_t frame[64], payload[2] = {0};
    uint16_t n = request(frame, 0x3f, payload, 0);
    host_body_frame(frame, n); em_poll(); reply(sent_n - 1, 2, 0x3f);
    CHECK(sent_len[sent_n - 1] == 74);
    CHECK(!strcmp((char *)sent[sent_n - 1] + 7, "Contax Zeiss Planar 50mm f/1.4"));
    for (unsigned value = 0; value <= UINT16_MAX; ++value) {
        payload[0] = (uint8_t)value; payload[1] = (uint8_t)(value >> 8);
        n = request(frame, 0x1b, payload, 2);
        host_body_frame(frame, n); em_poll(); reply(sent_n - 1, 2, 0x1b);
        uint16_t expected = value < 4224 ? 4352 : value <= 6400 ? value : 6400;
        CHECK(u16(em_msg_05 + 6) == expected && u16(em_msg_1B + 6) == expected);
        sent_n = 0;
    }
    CHECK(!sent_overflow && host_baud == EM_BAUD && host_baud_changes == 0);
    puts("Custom focal length, BCD focal field, name reply/checksum, range, boot value and 65536 aperture operands passed.");
}
'''
    source = build / 'test-custom-profile.c'
    source.write_text(code)
    binary = build / 'test-custom-profile'
    host, src = build / 'tools/hosttest', build / 'src'
    # Preserve IRQ masks just as the production aperture test does.
    sam = host / 'sam.h'
    text = sam.read_text()
    if '__get_PRIMASK' not in text:
        text = text.replace('static inline void __disable_irq(void) {}',
                            'static inline unsigned __get_PRIMASK(void) { return 0; }\n'
                            'static inline void __set_PRIMASK(unsigned key) { (void)key; }\n'
                            'static inline void __disable_irq(void) {}')
        sam.write_text(text)
    subprocess.run(['clang', '-std=gnu99', '-Os', '-DNDEBUG', '-DEA9_NO_LOG', '-Wall', '-Wextra',
                    '-Werror', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    f'-I{host}', f'-I{src}', str(source), str(host / 'shim.c'),
                    *(str(src / name) for name in ['emount.c', 'emount_packets.c', 'optical_file.c', 'reported_aperture.c']),
                    '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=30)
    if args.negative_control_build:
        control_src = args.negative_control_build.resolve() / 'src'
        control = build / 'test-unmodified-control'
        subprocess.run(['clang', '-std=gnu99', '-Os', '-DNDEBUG', '-DEA9_NO_LOG',
                        '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                        '-fno-sanitize-recover=all', f'-I{host}', f'-I{control_src}',
                        str(source), str(host / 'shim.c'),
                        *(str(control_src / name) for name in ['emount.c', 'emount_packets.c', 'optical_file.c', 'reported_aperture.c']),
                        '-o', str(control)], check=True)
        result = subprocess.run([str(control)], capture_output=True, text=True, timeout=30)
        assert result.returncode == 2 and result.stderr.rstrip().endswith(
            'em_focal_mm10 == 500 && u16(em_msg_05 + 0x1e) == 500'), result.stderr
        print('Unmodified Biotar negative control failed the required custom focal-length assertion.')
    print(f'{len(mutations)} invalid configuration controls rejected. No hardware access.')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Exercise selected profile flash words through production C, offline."""
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not __debug__:
        raise SystemExit('Run without Python optimization; assertion checks are required.')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    build, out = a.build.resolve(), a.output.resolve()
    assert out.is_relative_to(ROOT / 'artifacts/private')
    out.mkdir(exist_ok=False)
    host = out / 'host'
    shutil.copytree(build / 'tools/hosttest', host)
    sam = host / 'sam.h'
    text = sam.read_text()
    if '__get_PRIMASK' not in text:
        sam.write_text(text.replace('static inline void __disable_irq(void) {}',
            'static inline unsigned __get_PRIMASK(void) { return 0; }\n'
            'static inline void __set_PRIMASK(unsigned key) { (void)key; }\n'
            'static inline void __disable_irq(void) {}'))
    cases = json.loads((ROOT / 'profiles/requested-lenses.json').read_text())['lenses']
    results = []
    for index, lens in enumerate(cases):
        # Explicit test zoom position; the app requires the user to choose it.
        focal = 500 if lens['kind'] == 'zoom' else round(lens['focal_length_mm'] * 10)
        aperture = lens.get('nominal_maximum_aperture', lens.get('reported_nominal_maximum_aperture'))
        boot = 4096 + round(16 * math.log2(aperture)) * 32
        directory = out / ('profile-' + str(index))
        shutil.copytree(build / 'src', directory)
        packets = directory / 'emount_packets.c'
        text = packets.read_text()
        for old, new in [
            ('const uint16_t em_focal_mm10 = EM_FOCAL_MM10;', f'const uint16_t em_focal_mm10 = {focal}u;'),
            ('const uint16_t em_startup_aperture_av = EM_APERTURE_NOW;', f'const uint16_t em_startup_aperture_av = {boot}u;')]:
            assert text.count(old) == 1
            text = text.replace(old, new)
        frame = bytes([240,74,0,2,0,63,0]) + lens['display_name'].encode('ascii').ljust(64,b'\0') + bytes([0,0,85])
        assert len(frame) == 74
        text, count = re.subn(r'uint8_t em_msg_3F\[EA9_LEN_3F\] = \{[^}]*\};',
            lambda _: 'uint8_t em_msg_3F[EA9_LEN_3F] = {' + ','.join(hex(b) for b in frame) + '};', text)
        assert count == 1
        packets.write_text(text)

        def run(case):
            binary = out / (case + '-' + str(index))
            subprocess.run(['clang','-std=gnu99','-Os','-DNDEBUG','-DEA9_NO_LOG',
                '-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',
                f'-DEXPECT_FOCAL={focal}', f'-DEXPECT_BOOT={boot}',
                '-DEXPECT_NAME=' + json.dumps(lens['display_name']),
                f'-I{host}',f'-I{directory}',str(ROOT/'firmware/hosttest/test_profile_runtime.c'),
                str(host/'shim.c'),*(str(directory/name) for name in
                ['emount.c','emount_packets.c','optical_file.c','reported_aperture.c']),'-o',str(binary)],check=True)
            return subprocess.run([str(binary)],capture_output=True,text=True,timeout=20)

        result = run('production')
        assert result.returncode == 0, (lens['id'],result.stdout,result.stderr)
        results.append(dict(profileID=lens['id'],focalMM10=focal,startupAV=boot,passed=True))
        if lens['id'] == 'contax-zeiss-35-f1-4':
            source = directory / 'reported_aperture.c'
            text = source.read_text()
            assert text.count('pending = em_startup_aperture_av;') == 1
            source.write_text(text.replace('pending = em_startup_aperture_av;', 'pending = EM_APERTURE_NOW;'))
            broken = run('ignored-startup-word')
            assert broken.returncode == 2 and broken.stderr.rstrip().endswith(
                'u16(em_msg_05 + 6) == EXPECT_BOOT && u16(em_msg_1B + 6) == EXPECT_BOOT'), broken.stderr
    (out/'results.json').write_text(json.dumps(dict(profiles=results,
        negativeControl='ignored startup word rejected at exact startup assertion',
        hardwareAccess=False),indent=2)+'\n')
    print('All eight selected lens profiles passed production C startup, camera aperture and new-session tests; startup-word failing control rejected.')


if __name__ == '__main__':
    main()

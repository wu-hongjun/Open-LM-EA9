#!/usr/bin/env python3
"""Reproduce the 4.8-based 4.8.1 motion diagnostic sparse package offline."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from firmware_config import load_target, require

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / 'tools/firmware-deps'
ARM = str(DEPS / 'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
RELEASE = ROOT / 'firmware/releases/4.8.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlay(path, changes):
    source = path.read_text()
    for old, new in changes:
        require(source.count(old) == 1, f'4.8 overlay anchor changed in {path.name}: {old}')
        source = source.replace(old, new)
    path.write_text(source)


def add_hooks(src):
    overlay(src / 'abs_encoder.h', [
        ('void    abs_encoder_track_reset(void);',
         'void    abs_encoder_track_reset(void);\nuint16_t abs_encoder_track_raw(void);'),
    ])
    with (src / 'abs_encoder.c').open('a') as f:
        f.write('\nuint16_t abs_encoder_track_raw(void)\n{\n\treturn g_track_last;\n}\n')

    overlay(src / 'main.c', [
        ('#include "vdd.h"', '#include "vdd.h"\n#include "motion_trace.h"\n#include "profile_nvm.h"'),
        ('static const struct servo_cfg STOCK = {',
         'static const struct servo_cfg STOCK = {\n\t.trace_motion = 1,'),
        ('static void motor_home(void)', 'static __attribute__((noinline)) void motor_home(void)'),
        ('\tint32_t  before, after;', '\tint32_t  before, after;\n\tuint8_t drive_still = 0, settle_still = 0;'),
        ('\tbefore = abs_encoder_track();',
         '\tbefore = abs_encoder_track();\n'
         '\tmt_home_phase(millis(), MT_DRIVE_START, abs_encoder_track_raw(), before);'),
        ('\t\tpump(0);\n\t\tif (i < SERVO_TRACE_N',
         '\t\tpump(0);\n'
         '\t\tif (mt_home_sample_due(millis()))\n'
         '\t\t\tmt_record(millis(), MT_HOME_SAMPLE, MT_DRIVE_START, abs_encoder_raw(), 0, 0);\n'
         '\t\tif (i < SERVO_TRACE_N'),
        ('\t\t    && home_still_for(&still, HOME_STILL_MS)) {\n\t\t\tbreak;\n\t\t}\n\t}\n\tdrive_ms',
         '\t\t    && home_still_for(&still, HOME_STILL_MS)) {\n\t\t\tdrive_still = 1;\n'
         '\t\t\tbreak;\n\t\t}\n\t}\n\tdrive_ms'),
        ('\tvdd_track_result(&load_lo, &load_hi);\n\n\tt0 = millis();',
         '\tvdd_track_result(&load_lo, &load_hi);\n'
         '\tint32_t drive_end = abs_encoder_track();\n'
         '\tmt_home_phase(millis(), drive_still ? MT_DRIVE_STILL : MT_DRIVE_CAP,\n'
         '\t              abs_encoder_track_raw(), drive_end);\n\n\tt0 = millis();\n'
         '\tmt_home_phase(t0, MT_SETTLE_START, abs_encoder_track_raw(), drive_end);'),
        ('\t\tpump(0);                /* still pre-homing; see above */',
         '\t\tpump(0);                /* still pre-homing; see above */\n'
         '\t\tif (mt_home_sample_due(millis()))\n'
         '\t\t\tmt_record(millis(), MT_HOME_SAMPLE, MT_SETTLE_START, abs_encoder_raw(), 0, 0);'),
        ('\t\t    && home_still_for(&still, HOME_STILL_MS)) {\n\t\t\tbreak;\n\t\t}\n\t}\n\tsettle_ms',
         '\t\t    && home_still_for(&still, HOME_STILL_MS)) {\n\t\t\tsettle_still = 1;\n'
         '\t\t\tbreak;\n\t\t}\n\t}\n\tsettle_ms'),
        ('\tafter = abs_encoder_track();',
         '\tafter = abs_encoder_track();\n'
         '\tmt_home_phase(millis(), settle_still ? MT_SETTLE_STILL : MT_SETTLE_CAP,\n'
         '\t              abs_encoder_track_raw(), after);'),
        ('\tabs_encoder_track_reset();\n\tg_homed = 1;',
         '\tabs_encoder_track_reset();\n'
         '\tmt_home_phase(millis(), MT_ORIGIN, abs_encoder_track_raw(), 0);\n\tg_homed = 1;'),
        ('\t\treturn SERVO_OK;\n\t}\n\n\t/* The reported target',
         '\t\tmt_record(millis(), MT_LEG_SKIPPED, g_last_op, 0, here, want);\n'
         '\t\treturn SERVO_OK;\n\t}\n\n\t/* The reported target'),
        ('\tservo_move_rel(delta, cfg, &r);\n\tg_moving',
         '\tmt_record(millis(), MT_LEG_START, g_last_op, target_u, here, want);\n'
         '\tservo_move_rel(delta, cfg, &r);\n'
         '\tmt_record(millis(), MT_LEG_END, r.outcome, r.duty_peak, r.end, r.target);\n\tg_moving'),
        ('\t\tem_poll();\n\n\t\t/* If the handshake',
         '\t\tem_poll();\n'
         '\t\t/* Outer loop only: park and any nested AF call have returned. */\n'
         '\t\tif (g_homed && g_pa23_at && em_shutdown_acked)\n'
         '\t\t\tmt_save((const uint8_t *)MT_ADDRESS, mt_samd21_write_page);\n'
         '\n\t\t/* If the handshake'),
    ])
    overlay(src / 'emount.c', [
        ('#include "emount.h"', '#include "emount.h"\n#include "motion_trace.h"'),
        ('\t__enable_irq();\n\treturn 1;\n}\n\nuint8_t em_peek_focus_op',
         '\t__enable_irq();\n'
         '\t/* Record accepted mailbox consumption, including retargets and Stop. */\n'
         '\tif (out->op == EM_OP_SCAN) {\n'
         '\t\tmt_record(millis(), MT_COMMAND, out->op, (out->scan_flags << 8) | out->scan_speed,\n'
         '\t\t          out->scan_a, (int32_t)((uint32_t)out->scan_b | (uint32_t)out->scan_centre << 16));\n'
         '\t} else {\n'
         '\t\tmt_record(millis(), MT_COMMAND, out->op, out->drive_param, out->target,\n'
         '\t\t          out->op == EM_OP_DRIVE ? out->drive_vel : out->delta);\n'
         '\t}\n\treturn 1;\n}\n\nuint8_t em_peek_focus_op'),
    ])
    overlay(src / 'servo.h', [('uint8_t  dry;', 'uint8_t  dry;\n\tuint8_t  trace_motion;')])
    overlay(src / 'servo.c', [
        ('#include "servo.h"', '#include "servo.h"\n#include "motion_trace.h"'),
        ('\t\t\t\t\ttarget      = nt;\n\t\t\t\t\tout->target = target;',
         '\t\t\t\t\ttarget      = nt;\n\t\t\t\t\tif (cfg->trace_motion)\n'
         '\t\t\t\t\t\tmt_record(millis(), MT_RETARGET, 0, 0, pos, target);\n\t\t\t\t\tout->target = target;'),
        ('\t\t\t\t\ttarget = nt;\n\t\t\t\t\tif (n_retarget',
         '\t\t\t\t\ttarget = nt;\n\t\t\t\t\tif (cfg->trace_motion)\n'
         '\t\t\t\t\t\tmt_record(millis(), MT_RETARGET, reversed, 0, pos, target);\n\t\t\t\t\tif (n_retarget'),
        ('\t\t\t\tmotor_drive((int16_t)duty);',
         '\t\t\t\tmotor_drive((int16_t)duty);\n'
         '\t\t\t\tif (cfg->trace_motion) mt_servo_sample(millis(), pos, target, (int16_t)duty);'),
    ])


def add_trace_nvm(src):
    # Reuse the 4.8 RAM command port. The new entry point can only program a
    # blank trace page. Journal access still uses its existing range checks.
    overlay(src / 'profile_nvm.c', [
        ('#include "profile_nvm.h"', '#include "profile_nvm.h"\n#include "motion_trace.h"'),
        ('int mutate(unsigned offset,', 'int mutate(unsigned address,'),
        ('(PB_JOURNAL_ADDRESS+offset);', 'address;'),
        ('(PB_JOURNAL_ADDRESS+offset)/2', 'address/2'),
        ('int allowed(int writing)', 'int allowed(unsigned address, int writing)'),
        ('(PB_JOURNAL_ADDRESS/8192u)', '(address/8192u)'),
        ('!allowed(0)', '!allowed(PB_JOURNAL_ADDRESS,0)'),
        ('!pb_journal_range(off,64,256) || !allowed(1)', '!pb_journal_range(off,64,256) || !allowed(PB_JOURNAL_ADDRESS,1)'),
        ('!pb_journal_range(off,256,256) || !allowed(1)', '!pb_journal_range(off,256,256) || !allowed(PB_JOURNAL_ADDRESS,1)'),
        ('mutate(off,page)', 'mutate(PB_JOURNAL_ADDRESS+off,page)'),
        ('mutate(off,0)', 'mutate(PB_JOURNAL_ADDRESS+off,0)'),
    ])
    with (src / 'profile_nvm.c').open('a') as f:
        f.write("""
int mt_samd21_write_page(unsigned off, const uint8_t *page)
{
    if (!page || off % MT_PAGE || off >= MT_BYTES * MT_SLOTS ||
        !allowed(MT_ADDRESS + off, 1)) return -1;
    const volatile uint8_t *dst = (const volatile uint8_t *)(MT_ADDRESS + off);
    for (unsigned i = 0; i < MT_PAGE; ++i) {
        if (dst[i] != 255) return -1;
    }
    return mutate(MT_ADDRESS + off, page);
}
""")
    overlay(src / 'profile_nvm.h', [('#endif', 'int mt_samd21_write_page(unsigned off, const uint8_t *page);\n#endif')])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    out = p.parse_args().output.resolve()
    require(out.is_relative_to(ROOT / 'artifacts/private'), 'Use a new artifacts/private folder.')
    out.mkdir(exist_ok=False)
    build = out / 'work'
    base_builder = ROOT / 'scripts/build-profile-bank.py'
    subprocess.run([sys.executable, str(base_builder), '--output', str(build)], check=True)
    baseline = json.loads((build / 'manifest.json').read_text())
    src = build / 'src'
    for f in (ROOT / 'firmware/features/motion_trace').glob('*.[ch]'):
        shutil.copy2(f, src / f.name)
    add_hooks(src)
    add_trace_nvm(src)
    elf_name = 'build/ea9-rebuild-release.elf'
    with (build / 'optimizations.mk').open('a') as f:
        f.write(f'\nOBJS += $(OBJDIR)/motion_trace.o\n{elf_name}: $(OBJDIR)/motion_trace.o\n')
    overlay(src / 'ea9.ld', [
        ('*profile_runtime.o(.text* .rodata*)',
         '*profile_runtime.o(.text* .rodata*) *motion_trace.o(.text* .rodata*) *main.o(.text.motor_home)'),
    ])
    # Rebuild every object in a fresh directory after applying the hooks.
    (build / 'build').rename(build / 'baseline-build')
    _, target = load_target(ROOT, 'lm-ea9')
    includes = '-Isrc ' + ' '.join('-I' + str(DEPS / n) for n in target['includeDirectories'])
    with (out / 'build.log').open('w') as log:
        subprocess.run(['make', '-f', target['makefile'], 'BUILD=release', 'OPT=-Os',
                        f'TOOLCHAIN={ARM}', 'INCLUDES=' + includes, elf_name],
                       cwd=build, check=True, stdout=log, stderr=subprocess.STDOUT)
    elf = build / elf_name
    symbols = {}
    for line in subprocess.check_output([ARM + 'nm', str(elf)], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    end = symbols['_etext'] + symbols['_erelocate'] - symbols['_srelocate']
    require(end <= 0xa000 and symbols['_estack'] <= 0x20004000, 'Base application/RAM overflow.')
    require(symbols['_estack'] - symbols['_sstack'] == 8192, 'Stack reserve changed.')
    require(not any(n.startswith(('diag_', 'trail_')) for n in symbols), 'Legacy flash logging linked.')
    require('em_uart_set_baud' not in symbols, 'Working 750 kbaud changed.')
    for n in ('ready', 'command', 'mutate'):
        require(0x20000000 <= symbols[n] < 0x20004000, 'NVM command code is not in RAM: ' + n)
    for n in ('mt_save', 'mt_record', 'mt_samd21_write_page', 'pb_boot', 'profile_runtime_init'):
        require(0x10000 <= symbols[n] < 0x12000, 'Extension symbol misplaced: ' + n)

    def extract(name, sections, size):
        file = out / name
        subprocess.run([ARM + 'objcopy', '-O', 'binary', '--gap-fill=0xff',
                        *['--only-section=' + s for s in sections], str(elf), str(file)], check=True)
        data = file.read_bytes()
        require(len(data) <= size, 'Segment overflow: ' + name)
        file.write_bytes(data.ljust(size, b'\xff'))
        return len(data)

    require(extract('application.bin', ['.text', '.ARM.exidx', '.relocate'], 0x5000) == end - 0x5000,
            'Base load mapping changed.')
    extension_size = extract('extension.bin', ['.profile'], 0x2000)
    segments = [dict(address=address, bytes=(out / name).stat().st_size, file=name, sha256=sha(out / name))
                for address, name in [(0x5000, 'application.bin'), (0x10000, 'extension.bin')]]
    manifest = dict(
        schemaVersion=1, version=[4, 8, 1], target='lm-ea9', format='offline-motion-diagnostic',
        hardwareAccess=False, uploadQualified=False, cameraQualified=False, transmissionEnabled=False,
        baselineVersion=baseline['version'],
        baselineManifestSHA256=sha(ROOT / 'firmware/releases/4.8.0/manifest.json'),
        baselineSegments=baseline['segments'], segments=segments,
        preserveRanges=[[0, 0x5000], [0xa000, 0x10000], [0x12000, 0x20000]],
        requiredBlankBeforeInstall=[0x14000, 0x16000],
        runtimeTraceRange=[0x14000, 0x16000], traceFormat='OLAMOT1!',
        baseCodeAndDataEnd=hex(end), extensionUsedBytes=extension_size,
        stackReservedBytes=8192, freeBytesAboveStack=0x20004000 - symbols['_estack'],
        sources={f.name: sha(f) for f in sorted(src.iterdir()) if f.is_file()},
        buildRules={n: sha(build / n) for n in target['buildRules']},
        builderSHA256=sha(Path(__file__)), baselineBuilderSHA256=sha(base_builder),
        installation='Diagnostic only. Requires a separate exact-source installer preserving live 4.8 settings and all protected data.',
    )
    if (RELEASE / 'manifest.json').is_file():
        require(manifest == json.loads((RELEASE / 'manifest.json').read_text()), 'Published diagnostic manifest differs.')
        for segment in segments:
            require(sha(RELEASE / segment['file']) == segment['sha256'], 'Published diagnostic segment differs.')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'4.8.1 offline diagnostic package: {out}')


if __name__ == '__main__':
    main()

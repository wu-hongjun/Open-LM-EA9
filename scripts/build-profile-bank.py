#!/usr/bin/env python3
"""Build experimental 4.8.0 sparse profile-bank package, entirely offline."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from firmware_config import assemble, load_target, source_files, require
from profile_bank import make_bank, setting, JOURNAL_BYTES

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT/'tools/firmware-deps'
ARM = str(DEPS/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
FEATURE = ROOT/'firmware/features/profile_bank'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def replace(path, old, new, count=1):
    s = path.read_text()
    require(s.count(old) == count, 'Overlay anchor changed: ' + path.name)
    path.write_text(s.replace(old, new))


def main():
    if not __debug__:
        raise SystemExit('Run without Python optimization.')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--inventory', type=Path, help='Custom inventory; requires --version.')
    p.add_argument('--version', help='New custom version, e.g. 4.9.1; never overwrite a release.')
    p.add_argument('--default-profile', default='zeiss-jena-biotar-55-f2')
    a = p.parse_args()
    custom = bool(a.inventory or a.version or a.default_profile!='zeiss-jena-biotar-55-f2')
    version = [4,8,0]
    if custom:
        require(a.version is not None, 'A custom bank requires an unpublished --version.')
        parts=a.version.split('.')
        require(len(parts)==3 and all(x.isascii() and x.isdigit() for x in parts), 'Use major.minor.patch.')
        version=list(map(int,parts))
        require(all(0<=x<=255 for x in version) and version>[4,8,0], 'Use a new version after 4.8.0.')
        require(not (ROOT/'firmware/releases'/'.'.join(map(str,version))).exists(), 'Version is already published.')
    out = a.output.resolve()
    require(out.is_relative_to(ROOT/'artifacts/private'), 'Use a new artifacts/private folder.')
    base = json.loads((ROOT/'firmware/releases/4.5.0/manifest.json').read_text())
    target_dir, target = load_target(ROOT, 'lm-ea9')
    files = source_files(ROOT, target_dir)
    require({n:sha(f) for n,f in files.items()} == base['sources'], 'Working source pins changed.')
    out.mkdir(parents=True, exist_ok=False)
    src = out/'src'
    assemble(files, src)
    shutil.copytree(ROOT/'firmware/hosttest', out/'tools/hosttest')
    for directory in (FEATURE,target_dir/'profile-bank'):
        for f in directory.iterdir():
            if f.suffix in ('.c', '.h'):
                require(not (src/f.name).exists(), 'Duplicate feature/port file: '+f.name)
                shutil.copy2(f,src/f.name)
    for name in target['buildRules']: shutil.copy2(target_dir/name, out/name)
    header = src/'emount.h'
    replace(header, '#define EM_APERTURE_MAX  0x1200u', '#define EM_APERTURE_MAX  0x1080u')
    replace(header, '#define EM_APERTURE_MIN  0x1800u', '#define EM_APERTURE_MIN  0x1900u')
    replace(header, 'extern const uint16_t em_focal_mm10;',
            'extern uint16_t em_focal_mm10;\nextern uint16_t em_startup_aperture_av;')
    replace(src/'emount_packets.c', 'const uint16_t em_focal_mm10 = EM_FOCAL_MM10;',
            'uint16_t em_focal_mm10 = EM_FOCAL_MM10;')
    replace(src/'reported_aperture.c', '= EM_APERTURE_NOW;', '= em_startup_aperture_av;', 2)
    replace(src/'main.c', 'int main(void)', '#include "profile_runtime.h"\n\nint main(void)')
    replace(src/'main.c', '\tdelay_init();', '\tdelay_init();\n\t/* No sensor, motor, bus IRQ or handshake exists during settings commit. */\n\tif (!profile_runtime_init()) for (;;) {}')
    objects = ['profile_bank', 'profile_nvm', 'profile_runtime']
    with (out/'optimizations.mk').open('a') as f:
        f.write('\nOBJS += ' + ' '.join('$(OBJDIR)/'+n+'.o' for n in objects) + '\n')
        f.write(target['elf']+': '+ ' '.join('$(OBJDIR)/'+n+'.o' for n in objects)+'\n')
    ld = src/'ea9.ld'
    replace(ld, '  ram      (rwx)', '  extension (rx) : ORIGIN = 0x10000, LENGTH = 0x2000\n  ram      (rwx)')
    # Consume feature sections before the baseline wildcard sections; reset .text's
    # VMA explicitly so the vector table stays at the stock entry point.
    replace(ld, '    .text :', '    .profile 0x10000 : { '+
            ' '.join('*'+n+'.o(.text* .rodata*)' for n in objects)+
            ' } > extension\n\n    .text 0x5000 :')
    includes = '-Isrc ' + ' '.join('-I'+str(DEPS/n) for n in target['includeDirectories'])
    with (out/'build.log').open('w') as log:
        subprocess.run(['make','-f',target['makefile'],'BUILD=release','OPT=-Os',f'TOOLCHAIN={ARM}',
                        'INCLUDES='+includes,target['elf']],cwd=out,check=True,stdout=log,stderr=subprocess.STDOUT)
    elf = out/target['elf']
    symbols = {}
    for line in subprocess.check_output([ARM+'nm',str(elf)], text=True).splitlines():
        fields = line.split()
        if len(fields)==3: symbols[fields[2]] = int(fields[0],16)
    end = symbols['_etext'] + symbols['_erelocate'] - symbols['_srelocate']
    require(end <= 0xa000 and symbols['_estack'] <= 0x20004000, 'Base application/RAM overflow.')
    require(not any(n.startswith(('diag_', 'trail_')) for n in symbols), 'Unexpected diagnostics.')
    require('em_uart_set_baud' not in symbols, 'Working 750 kbaud changed.')
    for n in ('ready','command','mutate'):
        require(0x20000000 <= symbols[n] < 0x20004000, 'NVM command code is not in RAM: '+n)
    for n in ('pb_boot','pb_store','profile_runtime_init','profile_apply_record'):
        require(0x10000 <= symbols[n] < 0x12000, 'Feature misplaced: '+n)
    # Extract noncontiguous segments: never fill the existing 0xa000..0x10000 data with FF.
    subprocess.run([ARM+'objcopy','-O','binary','--gap-fill=0xff','--only-section=.text',
                    '--only-section=.ARM.exidx','--only-section=.relocate',str(elf),str(out/'application.bin')],check=True)
    data = (out/'application.bin').read_bytes()
    require(len(data)==end-0x5000, 'Base load mapping changed.')
    (out/'application.bin').write_bytes(data.ljust(0x5000,b'\xff'))
    subprocess.run([ARM+'objcopy','-O','binary','--only-section=.profile',str(elf),str(out/'extension.bin')],check=True)
    extension=(out/'extension.bin').read_bytes()
    require(len(extension)<=0x2000, 'Extension overlaps bank.')
    (out/'extension.bin').write_bytes(extension.ljust(0x2000,b'\xff'))
    inventory = a.inventory or ROOT/'profiles/requested-lenses.json'
    bank, included, omitted = make_bank(json.loads(inventory.read_text()),a.default_profile)
    (out/'bank.bin').write_bytes(bank)
    (out/'settings.bin').write_bytes(setting(bank,bank[15]).ljust(JOURNAL_BYTES,b'\xff'))
    segments = [dict(address=a,bytes=(out/n).stat().st_size,file=n,sha256=sha(out/n)) for a,n in
                [(0x5000,'application.bin'),(0x10000,'extension.bin'),(0x12000,'bank.bin'),(0x13000,'settings.bin')]]
    manifest = dict(schemaVersion=1,version=version,target='lm-ea9',format='offline-sparse-package',
        hardwareAccess=False,uploadQualified=False,cameraQualified=False,transmissionEnabled=False,
        baselineVersion='4.6.0',baselineImageSHA256=sha(ROOT/'firmware/releases/4.6.0/biotar-wide-aperture.bin'),
        baseCodeAndDataEnd=hex(end),extensionUsedBytes=len(extension),segments=segments,
        preserveRanges=[[0,0x5000],[0xa000,0x10000],[0x14000,0x20000]],
        requiredBlankBeforeFirstInstall=[0x10000,0x14000],
        profiles=included,omittedProfiles=omitted,defaultSlot=bank[15],
        inventorySHA256=sha(inventory),sources={f.name:sha(f) for f in sorted(src.iterdir()) if f.is_file()},
        buildRules={n:sha(out/n) for n in target['buildRules']},builderSHA256=sha(Path(__file__)),
        codecSHA256=sha(ROOT/'scripts/profile_bank.py'),
        installation='Not accepted by current updater. Requires fresh full backup, ownership checks and a gap-preserving installer.')
    published=ROOT/'firmware/releases/4.8.0'
    if not custom and (published/'manifest.json').exists():
        require(manifest==json.loads((published/'manifest.json').read_text()),'Published package changed; use a new version.')
        for segment in segments: require(sha(published/segment['file'])==segment['sha256'],'Published segment changed.')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('.'.join(map(str,version))+' sparse package; not upload-qualified. Build: '+str(out))


if __name__ == '__main__':
    main()

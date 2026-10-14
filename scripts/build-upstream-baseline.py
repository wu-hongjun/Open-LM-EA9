#!/usr/bin/env python3
"""Build the pinned upstream release, without our AF/protocol implementation."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT/'references/upstream/weiziqian/E-mount-impl-on-Techart-EA9'
OUT = ROOT/'firmware/upstream-baseline/build'
DEPS = ROOT/'tools/firmware-deps'
ARM = DEPS/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-'
COMMIT = 'd52ed06cc449918f938e0695fbf29a0c4141f2b2'
sha = lambda b: hashlib.sha256(b).hexdigest()
expected={}
prefix='upstream/weiziqian/E-mount-impl-on-Techart-EA9/'
for line in (ROOT/'references/checksums.sha256').read_text().splitlines():
    digest,name=line.split(maxsplit=1)
    if name.startswith(prefix):expected[name[len(prefix):]]=digest
if not expected:raise SystemExit('Missing pinned reference checksums.')
for name,digest in expected.items():
    path=REF/name
    if not path.is_file() or sha(path.read_bytes())!=digest:
        raise SystemExit('Materialize the pinned reference collection first: '+name)
if not Path(str(ARM)+'gcc').exists():raise SystemExit('Install the pinned dependencies in firmware/dependencies.json first.')
OUT.mkdir(parents=True,exist_ok=True)
sources='startup_samd21 system_samd21 board clock delay emount emount_packets em_uart em_eic motor abs_encoder servo focus_map focus_dist focus_pred vdd main'.split()

# Rescale the documented pupil-size row by the ratio of the encoded f-numbers.
original_row=bytes.fromhex('d1 d0 d5 e8 e9 ef')
v=((original_row[0]&15)<<8)|original_row[1];points=[v]
for b in original_row[2:]:points.append(points[-1]+(b-256 if b>127 else b))
ratio=2**((0x11c0-0x1100)/512)
scaled=[round(x*ratio) for x in points]
deltas=[scaled[i]-scaled[i-1] for i in range(1,5)]
if not 0<=scaled[0]<4096 or any(not -128<=x<=127 for x in deltas):raise SystemExit('Optical row cannot be encoded.')
row=bytes([(original_row[0]&0xf0)|(scaled[0]>>8),scaled[0]&255,*[x&255 for x in deltas]])
results={}
for label in ['reference','50f14']:
    work=OUT/label
    work.mkdir(exist_ok=True)
    # Only known snapshot files are overwritten; the immutable reference stays untouched.
    for name in expected:
        target=work/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((REF/name).read_bytes())
    edits={
      'src/startup_samd21.c':[('#include "samd21.h"','#include "sam.h"'),('.pfnNMI_Handler','.pfnNonMaskableInt_Handler'),('.pfnSVC_Handler','.pfnSVCall_Handler')],
      'src/system_samd21.c':[('#include "samd21.h"','#include "sam.h"')],
      'src/ea9.ld':[('LENGTH = 0x0001b000','LENGTH = 0x00005000')]}
    if label=='50f14':
        edits['src/emount.h']=[('0x59u','0x31u'),('0x11C0u','0x1100u'),
            ('{ 0xD1, 0xD0, 0xD5, 0xE8, 0xE9, 0xEF }','{ '+', '.join(f'0x{x:02X}' for x in row)+' }')]
        # Upstream duplicates its default f/1.8 as a literal in one test row.
        # Update only that configurable-lens fixture, not the conversion code.
        edits['tools/hosttest/test_emount.c']=[('{ 0x16, EM_APERTURE_NOW }','{ 0x10, EM_APERTURE_NOW }')]
    patches=[]
    for name,replacements in edits.items():
        path=work/name;before=path.read_text();after=before
        for old,new in replacements:
            if old not in after:raise SystemExit('Missing reviewed substitution: '+name+' '+old)
            after=after.replace(old,new)
        path.write_text(after)
        patches.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='upstream/'+name,tofile=label+'/'+name))
    (work/'changes.patch').write_text(''.join(patches))
    objects=[]
    flags=['-mthumb','-mcpu=cortex-m0plus','-O2','-DNDEBUG','-DEA9_NO_LOG','-D__SAMD21E17A__',
           '-ffunction-sections','-fdata-sections','-fno-common','-Wall','-Wextra','-std=gnu99','-g']
    inc=['-Isrc','-I'+str(DEPS/'samd21-dfp-2/samd21a/include'),'-I'+str(DEPS/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
    for name in sources:
        obj=work/(name+'.o');objects.append(str(obj))
        subprocess.run([str(ARM)+'gcc',*flags,*inc,'-c','src/'+name+'.c','-o',str(obj)],cwd=work,check=True)
    elf=work/'upstream.elf';binary=work/'upstream.bin'
    subprocess.run([str(ARM)+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld',
                    '-Wl,--gc-sections,-Map='+str(work/'upstream.map'),'--specs=nano.specs','--specs=nosys.specs','-o',str(elf)],cwd=work,check=True)
    symbols={}
    for line in subprocess.check_output([str(ARM)+'nm',str(elf)],text=True).splitlines():
        parts=line.split()
        if len(parts)==3:symbols[parts[2]]=int(parts[0],16)
    if any(n.startswith(('diag_','trail_','factory_servo_','ea9_af_','em_arb_')) for n in symbols):raise SystemExit('Unexpected custom controller/arbitration or flash logger linked.')
    if not {'servo_move_rel','motor_drive','em_poll'}<=symbols.keys():raise SystemExit('Upstream motor/controller/protocol missing.')
    end=symbols['_etext']+symbols['_erelocate']-symbols['_srelocate']
    if 0xa000-end<256 or symbols['_estack']-symbols['_sstack']!=8192:raise SystemExit('Insufficient release layout margin.')
    subprocess.run([str(ARM)+'objcopy','-O','binary','--gap-fill=0xff',str(elf),str(binary)],check=True)
    data=binary.read_bytes()
    if len(data)>0x5000:raise SystemExit('Application crosses the retained stock prefix.')
    padded=data+b'\xff'*(0x5000-len(data));(work/'bounded.bin').write_bytes(padded)
    sp=int.from_bytes(data[:4],'little');pc=int.from_bytes(data[4:8],'little')
    if sp!=symbols['_estack'] or not pc&1 or not 0x5000<=pc&~1<end:raise SystemExit('Invalid vectors.')
    with (work/'hosttests.log').open('w') as log:
        subprocess.run(['make','hosttest','HOSTCC=clang'],cwd=work,stdout=log,stderr=log,check=True)
    built={name:sha((work/name).read_bytes()) for name in expected if name.startswith('src/')}
    unchanged={name for name,h in built.items() if h==expected[name]}
    if any('src/'+s+'.c' not in unchanged for s in sources if s not in ['startup_samd21','system_samd21']):raise SystemExit('Behavior source was changed.')
    results[label]={'rawBytes':len(data),'boundedBytes':len(padded),'rawSHA256':sha(data),'imageSHA256':sha(padded),
                    'initializedFlashEnd':end,'flashMarginBytes':0xa000-end,'staticRAMBytes':symbols['_ezero']-0x20000000,
                    'reservedStackBytes':8192,'stackHighWaterMeasured':False,'sources':built,'changedFiles':sorted(set(built)-unchanged),
                    'patchSHA256':sha((work/'changes.patch').read_bytes()),'upstreamHostTestsPassed':True,
                    'protocolAndMotionCFilesUnchanged':True,'cameraQualified':False,'hardwareReportsSent':0}
resource=ROOT/'apps/macos/Sources/DeviceKit/Resources/ea9-af-upstream-baseline.bin'
resource.write_bytes((OUT/'50f14/bounded.bin').read_bytes())
(resource.parent.parent/'TrustedUpstreamBaseline.swift').write_text('// Generated by scripts/build-upstream-baseline.py; fixed upstream baseline 3.1.0.\nenum TrustedUpstreamBaseline { static let sha256 = "'+results['50f14']['imageSHA256']+'" }\n')
manifest={'status':'offline-upstream-baseline-not-camera-qualified','upstreamCommit':COMMIT,'upstreamURL':'https://github.com/weiziqian/E-mount-impl-on-Techart-EA9',
          'referenceChecksumCatalogSHA256':sha((ROOT/'references/checksums.sha256').read_bytes()),'sourceFiles':expected,
          'compiledSources':sources,'buildFlags':flags,'results':results,'loaderVersion':[3,1,0],'cameraVersionBCD':'0x31',
          'fixedFocalMM10':500,'fixedApertureAV':4352,'upstreamLensID':50496,'opticalRowScalingRatio':ratio,'pupilRow':list(row),
          'staticConfigurationOnly':True,'runtimeLensProfileSupported':False,'applicationEnd':0xa000,'hardwareReportsSent':0,
          'sourceChanges':'DFP header/vector spelling, capped linker ROM; for 50f14 only: version tag, documented aperture constants and correspondingly scaled pupil-size row. No C behavior/controller/protocol changes.'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'upstreamCommit':COMMIT,'images':{k:{n:v[n] for n in ['rawBytes','imageSHA256','flashMarginBytes','upstreamHostTestsPassed']} for k,v in results.items()},'hardwareReportsSent':0},indent=2))

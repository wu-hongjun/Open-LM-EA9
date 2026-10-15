#!/usr/bin/env python3
"""Bounded offline size control and release comparison, never device I/O."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=ROOT/'firmware/upstream-diagnostic/build';HARD=ROOT/'firmware/upstream-hardening';DEPS=ROOT/'tools/firmware-deps'
ARM=str(DEPS/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
APPS=['apply_frame.py','apply_tx.py','lanes/02-shutdown/apply.py','lanes/01-capture/apply.py','lanes/03-homing/apply.py','lanes/05-transport/apply.py','lanes/06-motion/apply.py','lanes/07-aperture/apply.py','lanes/08-diagnostics/apply.py']
UNITS='startup_samd21 system_samd21 board clock delay emount emount_packets em_uart em_eic motor abs_encoder servo focus_map focus_dist focus_pred vdd main startup_trace startup_trace_flash em_frame em_owner em_shutdown'.split()
def run(cmd,cwd=None,check=True):
    r=subprocess.run(list(map(str,cmd)),cwd=cwd,text=True,capture_output=True,timeout=30)
    if check: assert r.returncode==0,(cmd,r.stdout,r.stderr)
    return r

def build(work,control=False):
    flags=['-mthumb','-mcpu=cortex-m0plus','-O2','-DNDEBUG','-DEA9_NO_LOG','-D__SAMD21E17A__','-ffunction-sections','-fdata-sections','-fno-common','-Wall','-Wextra','-Werror','-std=gnu99','-g']
    inc=['-Isrc','-I'+str(DEPS/'samd21-dfp-2/samd21a/include'),'-I'+str(DEPS/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
    objects=[]
    for n in UNITS:
        obj=work/(n+'.o');objects.append(obj);run([ARM+'gcc',*flags,*(json.loads((HERE/'flags.json').read_text()).get(n,[]) if not control else []),*inc,'-c','src/'+n+'.c','-o',obj],work)
    cmd=[ARM+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld','-Wl,--gc-sections,-Map='+str(work/'size.map'),'--specs=nano.specs','--specs=nosys.specs','-o',work/'size.elf']
    link=run(cmd,work,check=False);(work/'link.txt').write_text(link.stderr)
    if control:
        assert link.returncode and 'overflowed' in link.stderr,link.stderr
        # Measure overflow control without modifying its memory map or making a
        # flashable image. GNU ld emits an analysis-only ELF despite the error.
        run(cmd+['-Wl,--noinhibit-exec'],work,check=False)
    else: assert link.returncode==0,link.stderr
    symbols={}
    for line in run([ARM+'nm',work/'size.elf']).stdout.splitlines():
        f=line.split()
        if len(f)==3:symbols[f[2]]=int(f[0],16)
    end=symbols['_etext']+symbols['_erelocate']-symbols['_srelocate']
    result=dict(codeAndDataEnd=end,margin=0x9c00-end,staticRAMBytes=symbols['_ezero']-0x20000000,linkExit=link.returncode)
    if not control:
        assert result['margin']>=256,result
        for name in ('park_to_infinity','em_set_park_handler','vdd_read_burst','em_pre','em_cap','em_norm_count','em_mode_count','em_id_log','em_body_offer','g_focus_ring'):assert name not in symbols,name
        for name in ('st_note','st_flush','st_write_page'):assert name in symbols,name
        run([ARM+'objcopy','-O','binary','--gap-fill=0xff',work/'size.elf',work/'raw.bin'])
        raw=(work/'raw.bin').read_bytes();assert len(raw)<=0x4c00
        image=raw+b'\xff'*(0x5000-len(raw));assert image[0x4c00:]==b'\xff'*1024
        (work/'analysis-only.bin').write_bytes(image)
        result['imageSHA256']=hashlib.sha256(image).hexdigest()
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--lane10',action='store_true');a=p.parse_args();out=a.output.resolve();out.mkdir(exist_ok=False)
    m=json.loads((BASE/'manifest.json').read_text())
    assert m==json.loads((ROOT/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.manifest.json').read_text())
    assert hashlib.sha256((ROOT/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.bin').read_bytes()).hexdigest()==m['imageSHA256']
    for n,h in m['sources'].items(): assert hashlib.sha256((BASE/n).read_bytes()).hexdigest()==h,n
    before=out/'before';shutil.copytree(BASE/'src',before/'src');shutil.copytree(BASE/'tools/hosttest',before/'tools/hosttest')
    apps=APPS+(['lanes/10-integration/apply.py'] if a.lane10 else [])
    for app in apps:runpy.run_path(str(HARD/app))['apply'](before)
    after=out/'after';shutil.copytree(before,after);runpy.run_path(str(HERE/'apply.py'))['apply'](after)
    rows={label:build(work,label=='before') for label,work in [('before',before),('after',after)]}
    rows['flashSaved']=rows['before']['codeAndDataEnd']-rows['after']['codeAndDataEnd'];rows['RAMSaved']=rows['before']['staticRAMBytes']-rows['after']['staticRAMBytes']
    rows['flagsByUnit']=json.loads((HERE/'flags.json').read_text())
    rows['applicators']=apps+['lanes/09-release/apply.py']
    rows['inputSHA256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*[HARD/x for x in apps],*[f for f in HERE.iterdir() if f.suffix in ('.py','.json','.c','.h') and f.name!='result.json']]}
    rows['preservedSourceSHA256']={n:hashlib.sha256((after/'src'/n).read_bytes()).hexdigest() for n in ['ea9.ld','emount_packets.c','emount_packets.h','vdd.c','motor.c','em_uart.c','startup_trace.c','startup_trace.h','startup_trace_flash.c']}
    for n in rows['preservedSourceSHA256']: assert (before/'src'/n).read_bytes()==(after/'src'/n).read_bytes(),n
    first=rows['after']['imageSHA256']; assert build(after)['imageSHA256']==first
    rows['repeatBuildIdentical']=True
    # Alternate bench instrumentation remains buildable. It is not a release
    # image and is never linked/packaged here; legacy park has no production
    # shutdown caller under lane02 even in this diagnostic configuration.
    for name in ('main','emount','servo'):
        run([ARM+'gcc','-mthumb','-mcpu=cortex-m0plus','-O2','-DNDEBUG','-D__SAMD21E17A__','-ffunction-sections','-fdata-sections','-fno-common','-Wall','-Wextra','-Werror','-std=gnu99','-Isrc','-I'+str(DEPS/'samd21-dfp-2/samd21a/include'),'-I'+str(DEPS/'CMSIS_5-5.9.0/CMSIS/Core/Include'),'-c','src/'+name+'.c','-o',after/(name+'-legacy-diagnostic.o')],after)
    rows['legacyDiagnosticCompile']=True
    (out/'result.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Offline production C journal/runtime tests, fault injection and failing controls."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from profile_bank import (make_bank, setting, load_setting, mailbox, plan_selection,
                          validate_bank, JOURNAL_BYTES)

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not __debug__: raise SystemExit('Run without optimization.')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); build=a.build.resolve(); out=a.output.resolve()
    assert out.is_relative_to(ROOT/'artifacts/private')
    out.mkdir(exist_ok=False)
    bank=(build/'bank.bin').read_bytes(); validate_bank(bank)
    journal=(build/'settings.bin').read_bytes(); active=load_setting(bank,journal)
    assert active['slot']==bank[15] and active['generation']==0
    # Host planning has no device API and never advertises a transport capability.
    meta=bytes(58)
    metadata_file=out/'metadata58.bin'; metadata_file.write_bytes(meta)
    proposal_file=out/'selection.json'
    command=['python3',str(ROOT/'scripts/plan-profile-selection.py'),'--package',str(build),
             '--journal',str(build/'settings.bin'),'--metadata',str(metadata_file),
             '--profile-id','contax-zeiss-50-f1-4','--output',str(proposal_file)]
    subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
    saved=proposal_file.read_bytes(); assert not json.loads(saved)['transmissionEnabled']
    refused=subprocess.run(command,capture_output=True,text=True)
    assert refused.returncode==2 and proposal_file.read_bytes()==saved
    foreign=out/'foreign.bin'; foreign.write_bytes(bytes(32)+b'x'*26)
    bad=command.copy(); bad[bad.index('--metadata')+1]=str(foreign)
    bad[bad.index('--output')+1]=str(out/'rejected.json')
    refused=subprocess.run(bad,capture_output=True,text=True)
    assert refused.returncode==2 and not (out/'rejected.json').exists()
    assert not plan_selection(bank,journal,meta,active['slot'])['needsWrite']
    proposal=plan_selection(bank,journal,meta,0)
    assert proposal['needsWrite'] and not proposal['transmissionEnabled']
    pending=bytes.fromhex(proposal['proposedMetadataHex'])
    assert pending[:32]==meta[:32] and len(pending)==58
    assert not plan_selection(bank,journal,pending,0)['needsWrite']
    cancel=plan_selection(bank,journal,pending,active['slot'])
    assert cancel['needsWrite'] and bytes.fromhex(cancel['proposedMetadataHex'])!=pending
    committed=setting(bank,0,2,1).ljust(JOURNAL_BYTES,b'\xff')
    assert not plan_selection(bank,committed,pending,0)['pendingApplication']
    for invalid in (bytes(57), bytes(59),bytes(32)+b'x'*26):
        try: plan_selection(bank,journal,invalid,0)
        except ValueError: pass
        else: raise AssertionError('Invalid/foreign metadata accepted.')
    exhausted=bytes(32)+mailbox(bank,0,0xffffffff)
    try: plan_selection(bank,journal,exhausted,1)
    except ValueError: pass
    else: raise AssertionError('Request generation wrapped.')
    inventory=json.loads((ROOT/'profiles/requested-lenses.json').read_text())
    generated,ids,omitted=make_bank(inventory)
    assert bank==generated and len(ids)==7 and len(omitted)==1
    for bad in (True,float('nan'),0,1001):
        invalid=json.loads(json.dumps(inventory)); invalid['lenses'][0]['focal_length_mm']=bad
        try: make_bank(invalid)
        except ValueError: pass
        else: raise AssertionError('Invalid focal input accepted.')
    invalid=json.loads(json.dumps(inventory)); invalid['lenses'][1]['id']=invalid['lenses'][0]['id']
    try: make_bank(invalid)
    except ValueError: pass
    else: raise AssertionError('Duplicate profile IDs accepted.')
    # A manually configured zoom can be added; never assume its current focal length.
    zoom=next(x for x in inventory['lenses'] if x['kind']=='zoom')
    zoom['active_focal_length_mm']=50
    zoom['display_name']='Contax Zeiss 28-70mm f/3.5'
    eight,_,_=make_bank(inventory); validate_bank(eight)
    assert eight[14]==8
    (out/'eight-bank.bin').write_bytes(eight)
    flags=['clang','-std=gnu99','-Os','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
           '-fno-sanitize-recover=all']
    results=[]
    for case in ('production','ignore-record-crc','erase-current-row'):
        src=out/case; shutil.copytree(build/'src',src)
        source=src/'profile_bank.c'; text=source.read_text()
        if case=='ignore-record-crc':
            old='pb_crc32(p,56)!=pb_u32(p+56)'
            assert text.count(old)==1; text=text.replace(old,'0')
        if case=='erase-current-row':
            old='unsigned next=(old.row+1u)%PB_JOURNAL_ROWS;'
            assert text.count(old)==1; text=text.replace(old,'unsigned next=old.row;')
        source.write_text(text)
        binary=out/(case+'.test')
        subprocess.run(flags+[f'-I{src}',str(ROOT/'firmware/hosttest/test_profile_bank.c'),
                              str(source),'-o',str(binary)],check=True)
        run=subprocess.run([str(binary),str(build/'bank.bin')],capture_output=True,text=True,timeout=60)
        if case=='production':
            assert run.returncode==0,(run.stdout,run.stderr)
            # Also exercise a user-expanded bank, including explicitly configured zoom.
            subprocess.run([str(binary),str(out/'eight-bank.bin')],check=True,stdout=subprocess.DEVNULL)
        else:
            assert run.returncode==2 and ('s.sequence<before.sequence' if case=='ignore-record-crc' else
                   'f.per_row[i]==20') in run.stderr,run.stderr
        results.append(dict(case=case,passed=True,expectedExit=run.returncode))
    host=out/'host'; shutil.copytree(build/'tools/hosttest',host)
    sam=host/'sam.h'; s=sam.read_text()
    sam.write_text(s.replace('static inline void __disable_irq(void) {}',
        'static inline unsigned __get_PRIMASK(void) { return 0; }\n'
        'static inline void __set_PRIMASK(unsigned key) { (void)key; }\n'
        'static inline void __disable_irq(void) {}'))
    src=build/'src'; binary=out/'runtime.test'
    subprocess.run(flags+['-DNDEBUG','-DEA9_NO_LOG',f'-I{host}',f'-I{src}',
        str(ROOT/'firmware/hosttest/test_banked_runtime.c'),str(host/'shim.c'),
        *(str(src/n) for n in ('emount.c','emount_packets.c','optical_file.c','reported_aperture.c',
                              'profile_bank.c','profile_runtime.c')),'-o',str(binary)],check=True)
    for i in range(eight[14]):
        subprocess.run([str(binary),str(out/'eight-bank.bin'),str(i)],check=True,stdout=subprocess.DEVNULL)
    # The new startup parameter must actually reach the production packet path.
    broken=out/'broken-reporting.c'
    text=(src/'reported_aperture.c').read_text()
    broken.write_text(text.replace('= em_startup_aperture_av;','= EM_APERTURE_NOW;'))
    command=flags+['-DNDEBUG','-DEA9_NO_LOG',f'-I{host}',f'-I{src}',
        str(ROOT/'firmware/hosttest/test_banked_runtime.c'),str(host/'shim.c'),str(broken),
        *(str(src/n) for n in ('emount.c','emount_packets.c','optical_file.c','profile_bank.c','profile_runtime.c')),
        '-o',str(out/'broken-runtime.test')]
    subprocess.run(command,check=True)
    run=subprocess.run([str(out/'broken-runtime.test'),str(out/'eight-bank.bin'),'1'],capture_output=True,text=True)
    assert run.returncode==2 and 'u16(em_msg_05+6)==pb_u16(r+16)' in run.stderr,run.stderr
    report=dict(hardwareAccess=False,portableC=results,productionProtocolProfiles=8,
                bankSingleBitCorruptions=32768,journalLatestRecordBitCorruptions=512,
                semanticInvalidBanksWithRecomputedChecksums=12,
                tornOperationBoundariesPerBank=322,banksTested=2,
                hostPlanner='no-op, pending/cancel, binding, foreign bytes, exhaustion; no transmission',
                startupFailingControl=True)
    report['cliControls']='offline proposal; existing output and foreign metadata refused'
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Profile bank, 16-row journal, power-cut models, production packet paths and three failing controls passed.')


if __name__=='__main__': main()

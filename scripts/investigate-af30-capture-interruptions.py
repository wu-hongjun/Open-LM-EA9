#!/usr/bin/env python3
"""Offline seeded factory interruption replay against pinned AF 3.0 source."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

if not __debug__:
    raise RuntimeError('Optimized Python disables oracle assertions; no output was created.')

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
out = p.parse_args().output.resolve()
sys.path.insert(0, str(ROOT / 'research/stock-1.8'))
from config import configure, FIRMWARE_SHA256
configure(ROOT / 'firmware/recovery/stock-1.8.0/application.bin', out, 'clang')
from oracle import Machine

sha = lambda b: hashlib.sha256(b).hexdigest()
manifest = json.loads((ROOT / 'docs/evidence/af-arbitrated-build-manifest-2026-10-13.json').read_text())
AF30_COMMIT = '62ebd177ad5b7cbc76fbf75ebdfb80db7e59bb85'
def frozen(name):
    return subprocess.run(['git','show',AF30_COMMIT+':'+name],cwd=ROOT,
                          capture_output=True,check=True).stdout
image = ROOT/'firmware/candidates/3.0.0/contax-zeiss-50-f1-4.bin'
assert sha(image.read_bytes()) == 'a2ec81cd87be9142da1d4caec3968afff810bfc51e25ebc214f5532b51783b03'
ids = [0x0a,0x0b,0x1b,0x28,0x19,0x34]
factory = []
for phase in [2,3,5,12,13]:
    for id in ids:
        for sequence in [0,0x71,0xff]:
            calls=[];sent=[]
            def schedule(m):
                a=m.calls[-1]['args'];calls.append([a[0],hex(a[1])]);return 0
            def send(m):
                a=m.calls[-1]['args'];sent.append(bytes(m.u.mem_read(a[0],a[1])));return 0
            m=Machine({0x91c4:0,0x91ac:0,0x51c8:0,0x9180:send,0x609c:schedule})
            m.u.mem_map(0x41004000,0x1000);m.u.mem_map(0x60000000,0x1000)
            m.u.mem_write(0x20000000,bytes(2048))
            frame=bytearray([0xf0,11,0,2,sequence,id,0,0x11,0,0,0x55])
            frame[-3:-1]=sum(frame[1:-3]).to_bytes(2,'little')
            for off,value in [(0x522,1),(0x51f,4),(0x520,phase),(0x51c,1)]:m.set(0x20000000+off,value,1)
            m.set(0x20000660,0x20000000);m.set(0x20000678,0x200001a8)
            m.set(0x41004420,4);m.run(0x53a4,4)
            m.u.mem_write(0x20000694,bytes(frame))
            m.set(0x41004420,0);m.run(0x53a4,0)
            assert m.get(0x2000051e,1)==1
            m.run(0x5120);assert m.get(0x2000051f,1)==5
            m.run(0x5260);assert sent==[bytes(frame)]
            m.run(0x5188);m.run(0x5280)
            assert m.get(0x2000051f,1)==1
            assert calls==[[10,'0x5261'],[100,'0x5281']]
            factory.append({'seededPhase':phase,'id':id,'sequence':sequence,
                            'VDSelectsMode5':True,'completeRawEchoExact':True,'releaseReturnsToInitMode1':True})

base=ROOT/'firmware/ea9';work=out/'sources';work.mkdir()
names=['hosttest/test_capture_interruption.c','hosttest/shim.c','src/emount.c',
       'src/em_arbitration.c','src/emount_packets.c','src/lens_profile.c','src/lens_aperture.c','src/io_guard.c']
tree=subprocess.run(['git','ls-tree','-r','--name-only',AF30_COMMIT,'firmware/ea9'],
                    cwd=ROOT,capture_output=True,text=True,check=True).stdout.splitlines()
frozen_names={n for n in tree if n.endswith('.h')}|{'firmware/ea9/'+n for n in names if n!='hosttest/test_capture_interruption.c'}
frozen_hashes={}
for name in sorted(frozen_names):
    data=frozen(name);frozen_hashes[name]=sha(data)
    if name in manifest['sources']:assert frozen_hashes[name]==manifest['sources'][name],name
    target=work/Path(name).relative_to('firmware/ea9');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
probe=base/'hosttest/test_capture_interruption.c'
(work/'hosttest/test_capture_interruption.c').write_bytes(probe.read_bytes())
shim=work/'hosttest/shim.c';text=shim.read_text();before='void delay_us(uint32_t us) { (void)us; }';assert text.count(before)==1
shim.write_text(text.replace(before,'void host_probe_delay_us(uint32_t us);\nvoid delay_us(uint32_t us) { host_probe_delay_us(us); }'))
exe=out/'af30-probe'
flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-Wno-over-aligned',
       '-fsanitize=address,undefined','-fno-sanitize-recover=all','-ffunction-sections','-fdata-sections',
       '-Wl,-dead_strip','-DEA9_NO_LOG','-DEA9_AF_BUILD','-Ihosttest','-Isrc']
subprocess.run(flags+[n for n in names if n!='src/emount.c']+['-o',str(exe)],cwd=work,check=True)
current=[]
for id in ids:
    result=subprocess.run([str(exe),str(id),str(image)],capture_output=True,text=True,check=True)
    row=json.loads(result.stdout)
    assert row['firstReplyRawEchoExact']==(id==0x0a)
    assert row['replyBeforeNextVD']==(id!=0x0a)
    current.append(row)
inputs={probe,Path(__file__).resolve(),ROOT/'research/stock-1.8/oracle.py',ROOT/'research/stock-1.8/config.py'}
evidence={'status':'finite-interrupted-control-exchange-divergence-confirmed-camera-cause-unproven',
          'dateLocal':'2026-10-14','timezone':'America/New_York','hardwareReportsSent':0,
          'productionFirmwareChanged':False,'newFirmwareBuilt':False,'ownerFreezeCauseProven':False,
          'sourceApplicationSHA256':FIRMWARE_SHA256,'customImageSHA256':sha(image.read_bytes()),
          'frozenAF30SourceGitCommit':AF30_COMMIT,'frozenProductionAndShimSHA256':frozen_hashes,
          'factoryOriginalInstructionCases':factory,'af30ActualResponderCases':current,
          'factoryCases':len(factory),'customCases':len(current),'matchingRawEchoCases':1,'divergingNon0ARequestIDs':5,
          'factoryContract':'Seeded connected mode 4, gate open, callbacks enabled and supplied interruption phase; actual CS/VD/raw echo/TX-release instructions. Lower DMA RX, UART and timer operations cut; callbacks explicitly invoked. Dummy registers and checksum-valid synthetic 11-byte init frames. No ordinary reachability or physical timing proof.',
          'customContract':'Exact frozen AF 3.0 sources from the pinned release commit; compiled production units match build-manifest digests. Actual responder with initialized synthetic session and real 50mm profile; supplied request during 300us status gap through host delay shim, immediate UART completion. No actual main/motor/IRQ timing or A7C II traffic.',
          'limitations':['An ID other than 0x0a is not sufficient by itself to select factory mode 5; the supplied phase/interlock causes the transition.',
                         'The 11-byte requests have valid framing/checksum; full request grammar and shutter traffic are not recovered.',
                         'The original full camera conversation, metadata, exposure, optical focus and hardware failure cause remain unproven.'],
          'sourceSHA256':{str(f.relative_to(ROOT)):sha(f.read_bytes()) for f in sorted(inputs)}}
(out/'results.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps({k:evidence[k] for k in ['status','factoryCases','customCases','divergingNon0ARequestIDs','hardwareReportsSent']},indent=2))

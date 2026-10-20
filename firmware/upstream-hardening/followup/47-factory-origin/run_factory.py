#!/usr/bin/env python3
"""Bounded original-instruction sensor/homing/origin probes; synthetic I/O only."""
import argparse,hashlib,json,sys
from pathlib import Path
if not __debug__:raise SystemExit('Assertions are required; optimized Python is unsupported')
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
assert out.parent==ROOT/'artifacts/private' and out.name.startswith('astra47-')
BASE=ROOT/'artifacts/private/readiness38-repeat';manifest=ROOT/'firmware/candidates/3.8.0/contax-zeiss-50-f1-4.manifest.json'
assert sha(manifest)=='be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0'
m=json.loads(manifest.read_text());assert m==json.loads((BASE/'manifest.json').read_text())
for n,h in m['sources'].items():assert sha(BASE/n)==h,n
pins={'research/stock-1.8/oracle.py':'ea53452f711c84d156e5bc665156fe2a48211014bcc6a59baa595811e2258d1e','research/stock-1.8/config.py':'07e8ec5648d7cd53a1ee03c1d1c540a8545c2f179b58910cb8d27eab6f2cc597'}
for n,h in pins.items():assert sha(ROOT/n)==h,n
sys.path.insert(0,str(ROOT/'research/stock-1.8'))
from config import configure,FIRMWARE_SHA256
cfg=configure(output=out)
from oracle import Machine
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_LR,UC_ARM_REG_SP,UC_ARM_REG_PC
import unicorn
assert unicorn.__version__=='2.1.4'
B=0x20000000

def machine(words=(20000,),status=0):
 x=Machine();x.u.mem_map(0x60000000,0x1000);x.u.mem_map(0x41004000,0x1000);x.u.mem_map(0x42002000,0x1000)
 x.u.mem_write(B,bytes(0xc00));x.events=[];x.words=list(words);x.busy=[];x.loop_instructions=0
 def assertion(q):assert q.calls[-1]['args'][0]==1;return 0
 def enable(q):q.events.append(['spi-enable',q.calls[-1]['args'][0],status]);return status
 def transfer(q):
  descriptor,transaction=q.calls[-1]['args'][:2];assert descriptor==B+0x868
  tx,rx,n=(q.get(transaction+i) for i in (0,4,8));assert n==2 and bytes(q.u.mem_read(tx,2))==b'\0\0'
  word=q.words.pop(0);q.u.mem_write(rx,word.to_bytes(2,'big'));q.events.append(['spi-transfer',word,status]);return status
 def code(u,pc,size,_):
  if pc==0x60cc:x.busy.append(u.reg_read(UC_ARM_REG_R0));x.events.append(['busy-enter',u.reg_read(UC_ARM_REG_R0)])
  if 0x60cc<=pc<=0x611c:x.loop_instructions+=1
  if pc==0x611c:x.events.append(['busy-return'])
 def write(u,access,addr,size,value,_):
  if addr in (0x60000014,0x60000018):x.events.append(['gpio',hex(addr),value])
  if 0x42002044<=addr<=0x42002050:x.events.append(['compare',hex(addr),value])
 x.stubs={0x7174:assertion,0x8008:enable,0x8040:transfer}
 x.u.hook_add(UC_HOOK_CODE,code);x.u.hook_add(UC_HOOK_MEM_WRITE,write)
 return x
sensor=[]
for selector in (1,0):
 for word in (0,3,0x1237,0xffff):
  x=machine([word],-7);result=x.run(0x89a4,selector);assert result==word>>2
  assert x.busy==[1,1] and x.loop_instructions==86
  kinds=[e[0] for e in x.events];assert kinds==['gpio','spi-enable','busy-enter','busy-return','spi-transfer','busy-enter','busy-return','gpio']
  assert x.events[0][2]==x.events[-1][2]==(0x80 if selector==1 else 0x800)
  sensor.append(dict(selector=selector,word=word,result=result,events=x.events,busyInstructions=x.loop_instructions))
loops=[]
for count in (0,1,2,40):
 x=machine([]);x.run(0x60cc,count);assert x.loop_instructions==5+38*count
 loops.append(dict(argument=count,instructions=x.loop_instructions))
# Gate supplied explicitly; this is not ordinary boot reachability. Motor pair
# drivers and compare setters execute, with SYNCBUSY inert and zero.
home=[]
for enabled in (0,1):
 for samples in ((5000,5000),(5000,6000),(16000,100),(100,16000)):
  x=machine([s<<2 for s in samples]);x.set(B+0x530,enabled,1);x.set(B+0x49c,4800,2)
  def delay(q):q.events.append(['delay-argument',q.calls[-1]['args'][0]]);return 0
  def persist(q):q.events.append(['persist-cut',q.get(B+0x49c,2)]);return 0
  x.stubs.update({0x66fc:delay,0x5da8:persist,0x5d68:persist})
  x.run(0x5e00)
  assert x.get(B+0x530,1)==0
  if enabled:
   assert x.get(B+0x49c,2)==samples[0]
   assert [e[1] for e in x.events if e[0]=='delay-argument']==[300,500]
   assert [e[1:] for e in x.events if e[0]=='compare']==[['0x42002044',0],['0x42002048',800],['0x4200204c',0],['0x42002050',800]]
   assert len([e for e in x.events if e[0]=='spi-transfer'])==2
  else:assert x.get(B+0x49c,2)==4800 and x.events==[]
  home.append(dict(gate=enabled,samples=samples,reference=x.get(B+0x49c,2),position=x.get(B+0x49a,2),events=x.events))
# Exact initialization/stop/restore sequence, through first foreground poll.
startup=[]
for saved_ref in (0,4800,16383,65535):
 x=machine([5000<<2]);saved=bytearray(44);saved[8:10]=saved_ref.to_bytes(2,'little');saved[6:8]=(2222).to_bytes(2,'little');saved[29]=1;saved[38:40]=(50).to_bytes(2,'little');x.u.mem_write(0x4100,bytes(saved))
 for addr in (0x5114,0x8b20,0x6080,0x904c,0x551c,0x6090,0x6dd4,0x6120):x.stubs[addr]=0
 checkpoints=[];done=[]
 def checkpoint(u,pc,size,_):
  if pc in (0x8c80,0x8e28,0x8ae4,0x8a8c,0x5dd4):checkpoints.append(dict(entry=hex(pc),reference=x.get(B+0x49c,2),armed=x.get(B+0x4b1,1),position=x.get(B+0x49a,2)))
  if pc==0x5dd4:done.append(True);u.emu_stop()
 x.u.hook_add(UC_HOOK_CODE,checkpoint);x.u.reg_write(UC_ARM_REG_SP,B+0x3e00);x.u.reg_write(UC_ARM_REG_LR,0x1001);x.u.emu_start(0x8b71,0x1000,count=100000)
 assert done==[True] and [q['entry'] for q in checkpoints]==['0x8c80','0x8e28','0x8ae4','0x8a8c','0x5dd4']
 assert checkpoints[2]['armed']==0 and checkpoints[3]['armed']==1 and checkpoints[3]['reference']==saved_ref
 assert x.get(B+0x530,1)==0
 startup.append(dict(savedReference=saved_ref,checkpoints=checkpoints,gate=x.get(B+0x530,1)))
controls={
 'sensor-has-no-setup-hold-loop':all(row['busyInstructions']==0 for row in sensor),
 'same-endian-is-byte-swap':all(row['result']==int.from_bytes(row['word'].to_bytes(2,'big'),'little')>>2 for row in sensor),
 'homing-is-unconditional':all(any(e[0]=='compare' for e in row['events']) for row in home),
 'homing-requires-equal-samples':all(row['reference']==4800 for row in home if row['gate'] and row['samples'][0]!=row['samples'][1]),
 'boot-initialized-origin-survives-restore':all(row['checkpoints'][3]['reference']==5000 for row in startup),
 'sensor-stop-guarantees-restored-disarmed':all(row['checkpoints'][3]['armed']==0 for row in startup)}
assert not any(controls.values())
ranges=[(0x60cc,0x611e),(0x89a4,0x8a2c),(0x6be4,0x6c60),(0x5e00,0x5fee),(0x8c64,0x8d94),(0x8e28,0x8fc8),(0x9070,0x90bc),(0x8b70,0x8bfc),(0x8ae4,0x8b20)]
result=dict(status='bounded-original-instruction-contracts-pass-no-homing-remedy',baseManifestSHA256=sha(manifest),baseImageSHA256=m['imageSHA256'],sources=m['sources'],stockApplicationSHA256=FIRMWARE_SHA256,oraclePins=pins,sensorCases=sensor,busyLoopCases=loops,conditionalHomeCases=home,startupCases=startup,rejectedWrongRules=list(controls),instructionRangeSHA256={f'{lo:04x}-{hi:04x}':hashlib.sha256(cfg.rom[lo-0x5000:hi-0x5000]).hexdigest() for lo,hi in ranges},runnerSHA256=sha(Path(__file__)),hardwareOperations=0,cameraQualified=False,limits=['Inert MMIO and supplied SPI bytes/statuses; no oscillator or peripheral timing model','100000 instructions per call, fixed delay arguments recorded without elapsed-time claim','HAL assertion/enable/transfer, board/timer init and NVM are cut; no physical origin validity','Gate explicitly supplied; prefix trace does not prove missing enabling writer throughout program'])
(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(sensorCases=len(sensor),busyLoopCases=len(loops),homeCases=len(home),startupCases=len(startup),negativeControls=len(controls))))

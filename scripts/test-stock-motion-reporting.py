#!/usr/bin/env python3
"""Offline original frame-sync/completion evidence; explicit synthetic state."""
from pathlib import Path
import argparse,sys,json,hashlib
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
out=parser.parse_args().output.resolve()
out.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(root/'research/stock-1.8'))
from config import configure,FIRMWARE_SHA256
configure(output=out/'stock-telemetry-instructions')
from oracle import Machine
sync=[]
for position in [4096,4144,4200,4800,5632,65535]:
 for completed in [0,1]:
  m=Machine()
  for off,value,width in [(0x51c,1,1),(0x51e,0,1),(0x49a,position,2),(0x4b8,completed,1),(6,0x4d,1),(7,0x9c,1),(0x1c4,0xd5,1)]:m.set(0x20000000+off,value,width)
  before_flags=(m.get(0x20000006,1),m.get(0x20000007,1),m.get(0x200001c4,1))
  m.run(0x5120)
  after_flags=(m.get(0x20000006,1),m.get(0x20000007,1),m.get(0x200001c4,1))
  a=m.get(0x20000008,2);b=m.get(0x2000001a,2)
  assert a==position and b==position and before_flags==after_flags
  sync.append({'sampledProtocolPosition':position,'completionFlag':completed,'positionAhead':a,'positionNow':b,'statusBytesUnchanged':True})
complete=[]
for flag in [0,1]:
 for delta in [-1,0,1]:
  for velocity in [-1000,0,1000]:
   m=Machine()
   for off,value,width in [(0x4a0,400+delta,4),(0x4a8,400,2),(0x4b0,1,1),(0x4b8,flag,1),(0x4a4,velocity,2)]:m.set(0x20000000+off,value,width)
   value=m.run(0x8d94)
   assert value==(1 if flag or delta>=0 else 0)
   complete.append({'completionFlag':flag,'position':400+delta,'target':400,'velocity':velocity,'returnedComplete':value})
report={'sourceApplicationSHA256':FIRMWARE_SHA256,'hardwareReportsSent':0,'frameSyncInstructionCases':sync,'completionInstructionCases':complete,'limits':['Original frame-sync gate seeded open; only this routine is asserted, not all possible firmware writers','Position extremes and velocity fields are synthetic fixtures','Unicorn executes stored instructions; no live UART/motor/camera/interrupt timing or ISA legality claim'],'scriptSHA256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Passed {len(sync)} original frame-sync cases and {len(complete)} original completion cases; hardware reports 0.')

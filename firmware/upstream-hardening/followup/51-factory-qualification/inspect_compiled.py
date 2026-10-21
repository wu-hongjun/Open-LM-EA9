#!/usr/bin/env python3
"""Collect pinned AF4.0 compiled evidence for manual policy review; NOT acceptance."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
TOOL=ROOT/'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-objdump'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
b=a.build.resolve();o=a.output.resolve();assert b.is_relative_to(ROOT/'artifacts/private') and o.is_relative_to(ROOT/'artifacts/private') and o.name.startswith('astra51-');o.mkdir(exist_ok=False)
m=json.loads((b/'manifest.json').read_text());assert m['loaderVersion']==[4,0,0]
for n,h in m['sources'].items():assert sha(b/n)==h,n
assert sha(b/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']
asm=subprocess.check_output([str(TOOL),'-d',str(b/'hardened.elf')],text=True);syms=subprocess.check_output([str(TOOL),'-t',str(b/'hardened.elf')],text=True)
(o/'disassembly.txt').write_text(asm);(o/'symbols.txt').write_text(syms)
heads=list(re.finditer(r'^([0-9a-f]+) <(.+)>:\n',asm,re.M));bodies={h[2]:asm[h.end():heads[i+1].start() if i+1<len(heads) else len(asm)] for i,h in enumerate(heads)}
indirect=[]
for name,body in bodies.items():
 for line in body.splitlines():
  z=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f]+\s+(blx|bx)\s+(\w+)',line)
  if z and z[3]!='lr':indirect.append(dict(caller=name,address=z[1],operation=z[2],register=z[3]))
selected={n:v for n,v in bodies.items() if n in ('main','servo_move_from','abs_encoder_home_reset','motor_emergency_release','motor_attach_pins','motor_drive','motor_brake','__libc_init_array') or 'detached' in n or 'release' in n}
(o/'review-functions.txt').write_text('\n'.join(n+'\n'+v for n,v in selected.items()))
r={'status':'EVIDENCE-ONLY-NOT-ACCEPTED','pins':{n:sha(b/n) for n in ('manifest.json','hardened.elf','hardened.map','raw.bin','contax-zeiss-50-f1-4.bin')},'objdumpSHA256':sha(TOOL),'indirectSites':indirect,'sourceCount':len(m['sources']),'codeAndDataEnd':m['codeAndDataEnd'],'staticRAMBytes':m['staticRAMBytes'],'hardwareOperations':0}
(o/'inventory.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

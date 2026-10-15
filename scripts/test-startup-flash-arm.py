#!/usr/bin/env python3
"""Execute a pinned compiled NVM writer's bounds in Unicorn, not on hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--build',type=Path,default=ROOT/'firmware/upstream-diagnostic/build')
parser.add_argument('--version',choices=['3.2.0','3.3.0'],default='3.2.0')
args=parser.parse_args()
b=args.build.resolve()
elf=b/('diagnostic.elf' if args.version=='3.2.0' else 'hardened.elf')
nm=ROOT/'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-nm'
symbols={}
for line in subprocess.check_output([str(nm),str(elf)],text=True).splitlines():
    q=line.split()
    if len(q)==3:symbols[q[2]]=int(q[0],16)
image=(b/('bounded.bin' if args.version=='3.2.0' else 'contax-zeiss-50-f1-4.bin')).read_bytes()
assert hashlib.sha256(image).hexdigest()==json.loads((b/'manifest.json').read_text())['imageSHA256']
assert image==(ROOT/'firmware/candidates'/args.version/'contax-zeiss-50-f1-4.bin').read_bytes()
results=[]
for name,address,occupied,error,expected in [
    ('first-page',0x9c00,False,False,1),('last-page',0x9fc0,False,False,1),
    ('below',0x9bc0,False,False,0),('misaligned',0x9c01,False,False,0),
    ('upper-bound',0xa000,False,False,0),('boot',0,False,False,0),
    ('user-row',0x804000,False,False,0),('occupied',0x9c00,True,False,0),
    ('nvm-error',0x9c00,False,True,0)]:
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
    u.mem_map(0,0x20000);u.mem_write(0,b'\xff'*0x20000);u.mem_write(0x5000,image)
    u.mem_map(0x20000000,0x4000);u.mem_map(0x30000000,0x1000);u.mem_map(0x41004000,0x1000)
    u.mem_write(0x41004014,b'\x01');u.mem_write(0x41004018,bytes([4 if error else 0,0]))
    payload=bytes(range(64));u.mem_write(0x20000000,payload)
    if occupied:u.mem_write(address,b'\x00')
    before=bytes(u.mem_read(0,0x20000));commands=[];stores=[];returned=[]
    def write(uc,access,a,size,value,unused):
        if a==0x41004000:
            command=value&0x7f;assert command in (0x44,4)
            assert int.from_bytes(uc.mem_read(0x4100401c,4),'little')==address//2
            commands.append(command)
        if a<0x20000:
            assert 0x9c00<=a<=0x9ffc and size==4
            stores.append(a)
    def code(uc,a,size,unused):
        if a==0x30000000:returned.append(True);uc.emu_stop()
    u.hook_add(UC_HOOK_MEM_WRITE,write);u.hook_add(UC_HOOK_CODE,code)
    u.reg_write(UC_ARM_REG_SP,0x20004000);u.reg_write(UC_ARM_REG_LR,0x30000001)
    u.reg_write(UC_ARM_REG_R0,address);u.reg_write(UC_ARM_REG_R1,0x20000000)
    u.emu_start(symbols['st_write_page']|1,0x30000002,count=1000000)
    actual=u.reg_read(UC_ARM_REG_R0);assert returned and actual==expected,(name,actual)
    after=bytes(u.mem_read(0,0x20000))
    assert before[:0x9c00]==after[:0x9c00] and before[0xa000:]==after[0xa000:]
    if expected:
        assert commands==[0x44,4] and stores==list(range(address,address+64,4))
        assert after[address:address+64]==payload
    else:assert not commands and not stores
    results.append({'case':name,'return':actual,'pageBufferStores':len(stores),
                    'NVMCommands':commands,'outsideDiagnosticRegionUnchanged':True})
e={'status':'passed-compiled-candidate-instruction-bounds','cases':results,
   'elfSHA256':hashlib.sha256(elf.read_bytes()).hexdigest(),
   'imageSHA256':hashlib.sha256(image).hexdigest(),'hardwareReportsSent':0,
   'limits':'NVM READY and flash-buffer memory are supplied. This checks compiled address/command/erased-page/error guards, not physical programming, voltage, cache coherence or write timing.'}
with args.output.open('x') as out:json.dump(e,out,indent=2);out.write('\n')
print(json.dumps({'passingARMCases':len(results),'hardwareReportsSent':0}))

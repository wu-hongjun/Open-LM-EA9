#!/usr/bin/env python3
"""Exact AF3.5 polling guards and pre-log emergency GPIO path in Unicorn.

All MMIO/interrupt behavior is supplied, no hardware is opened. Emulation stops
before st_note/NVM; physical programming and timing are outside this contract.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PRIMASK
root=Path(__file__).resolve().parents[4]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build',type=Path,default=root/'artifacts/private/absolute35a')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();b=args.build.resolve();out=args.output.resolve()
assert out.is_relative_to(root/'artifacts/private')
assert not out.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest_path=b/'manifest.json';manifest=json.loads(manifest_path.read_text())
assert sha(manifest_path)=='a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de'
image_path=b/'contax-zeiss-50-f1-4.bin';image=image_path.read_bytes()
assert sha(image_path)==manifest['imageSHA256']=='04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632'
assert image==(root/'firmware/candidates/3.5.0/contax-zeiss-50-f1-4.bin').read_bytes()
for name,digest in manifest['sources'].items():assert sha(b/name)==digest,name
prefix=root/'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-'
symbols={}
for line in subprocess.check_output([str(prefix)+'nm',str(b/'hardened.elf')],text=True).splitlines():
    s=line.split()
    if len(s)==3:symbols[s[2]]=int(s[0],16)
# Addresses are independently visible in the reviewed AF3.5 image/ELF.
expected_symbols={'clock_init':0x5250,'abs_encoder_set_reference':0x6ec0,
    'abs_encoder_init':0x6df4,'motor_drive':0x6da0,'em_uart_send':0x667c,
    'vdd_track_sample':0x79c4,'st_fail':0x8d9c,'st_note':0x8874,'_etext':0x95f8,
    '_erelocate':0x20000500,'_srelocate':0x20000000}
assert all(symbols[n]==a for n,a in expected_symbols.items())
rows=[]
cases=[('clock-stuck','clock_init',1,{},[],False),
       ('encoder-dre','abs_encoder_set_reference',2,{},[],False),
       ('encoder-rxc','abs_encoder_set_reference',2,{0x42000818:b'\x01'},[],False),
       ('encoder-reset','abs_encoder_init',2,{},[],False),
       ('motor-sync','motor_drive',4,{0x42002008:(0x100).to_bytes(4,'little')},[],False),
       ('uart-dre','em_uart_send',5,{},[],False),
       ('uart-txc','em_uart_send',5,{},[(0x668e,0x42000c18,0)],False),
       ('adc-result','vdd_track_sample',3,{},[(0x79ce,0x42004018,0)],False),
       ('encoder-ready','abs_encoder_set_reference',None,{0x42000818:b'\x05'},[],False),
       ('clock-ready','clock_init',None,{0x4000080c:b'\x10\0\0\0'},[],False),
       ('uart-ready','em_uart_send',None,{},[(0x668e,0x42000c18,3)],False),
       ('encoder-budget-removed','abs_encoder_set_reference',None,{},[],True)]
for name,entry,fault,setup,cuts,mutation in cases:
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
    for address,size in [(0,0x20000),(0x806000,0x1000),(0x20000000,0x4000),(0x30000000,0x1000),(0x40000000,0x10000),(0x41000000,0x10000),(0x42000000,0x10000),(0xe000e000,0x2000)]:u.mem_map(address,size)
    u.mem_write(0x5000,image)
    u.mem_write(0x20000000,image[0x95f8-0x5000:0x9af8-0x5000])
    for address,data in setup.items():u.mem_write(address,data)
    for pin in [8,9,18,19]:u.mem_write(0x41004440+pin,b'\x01')
    if mutation:
        assert bytes(u.mem_read(0x6dbe,2))==b'\x01\x3a'
        u.mem_write(0x6dbe,b'\xc0\x46')
    events=[];writes=[]
    def at_fail(uc,a,size,data):events.append(('fault',uc.reg_read(UC_ARM_REG_R0)))
    def at_note(uc,a,size,data):
        events.append(('note',uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1)))
        uc.emu_stop()
    def at_return(uc,a,size,data):events.append(('return',uc.reg_read(UC_ARM_REG_R0)));uc.emu_stop()
    def write(uc,access,address,size,value,data):writes.append((address,size,value))
    u.hook_add(UC_HOOK_CODE,at_fail,begin=symbols['st_fail'],end=symbols['st_fail'])
    u.hook_add(UC_HOOK_CODE,at_note,begin=symbols['st_note'],end=symbols['st_note'])
    u.hook_add(UC_HOOK_CODE,at_return,begin=0x30000000,end=0x30000000)
    u.hook_add(UC_HOOK_MEM_WRITE,write,begin=0x41004400,end=0x4100447f)
    for address,reg,value in cuts:
        def supply(uc,a,size,data,reg=reg,value=value):uc.mem_write(reg,bytes([value]))
        u.hook_add(UC_HOOK_CODE,supply,begin=address,end=address)
    u.reg_write(UC_ARM_REG_SP,0x20002c00);u.reg_write(UC_ARM_REG_LR,0x30000001)
    u.reg_write(UC_ARM_REG_R0,0x20000100 if entry=='em_uart_send' else 100)
    u.reg_write(UC_ARM_REG_R1,0 if name=='uart-txc' else 1)
    u.emu_start(symbols[entry]|1,0x30000002,count=40000000)
    if mutation:assert events==[],events
    elif fault:
        assert events==[('fault',fault),('note',6,fault)],(name,events)
        assert u.reg_read(UC_ARM_REG_PRIMASK)==1
        assert all(bytes(u.mem_read(0x41004440+pin,1))[0]&1==0 for pin in [8,9,18,19])
        assert (0x41004404,4,0xc0300) in writes and (0x41004418,4,0x80000) in writes
    else:
        assert len(events)==1 and events[0][0]=='return',(name,events)
        if name=='uart-ready':assert events[0][1]==1
    rows.append(dict(case=name,events=events,instructionBudget=40000000,mutation=mutation))
    print(json.dumps(rows[-1]),flush=True)
result=dict(status='passed-exact-35-compiled-peripheral-bounds',
    imageSHA256=manifest['imageSHA256'],manifestSHA256=sha(manifest_path),
    elfSHA256=sha(b/'hardened.elf'),sourceHashesVerified=len(manifest['sources']),
    symbols=expected_symbols,positiveCases=11,failingMutationControls=1,cases=rows,
    hardwareReportsSent=0,canonicalStateModified=False,
    limits=['Memory-backed MMIO with explicitly supplied readiness; no asynchronous IRQ or electrical model.',
            'All positive fault guards use the actual 4194304 iteration bound; the 40000000 instruction ceiling is an emulator stopping rule, not physical time.',
            'Execution stops at st_note after the actual interrupt-mask and GPIO stores; flash flush and terminal WFI are not executed here.',
            'The mutation removes only the first SPI DRE budget decrement in emulator memory, leaving published files unchanged.',
            'GPIO register stores are verified; bridge voltage, current, motor coast and physical latency remain unmeasured.'])
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')

#!/usr/bin/env python3
"""Execute compiled candidate startup/NVM port in a synthetic Cortex-M0 machine.

Only register/flash effects are modeled. No hardware, USB, analog timing, power
integrity, cache physics or camera stability is established by this test.
"""
import argparse
import json
from pathlib import Path
import subprocess
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from profile_bank import mailbox,load_setting

ROOT=Path(__file__).resolve().parents[1]
ARM=str(ROOT/'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
NVM=0x41004000


class Machine:
    def __init__(self,build):
        self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M0)
        self.u.mem_map(0,0x20000); self.u.mem_map(0x20000000,0x4000); self.u.mem_map(NVM,0x1000)
        self.symbols={}
        elf=build/'build/ea9-rebuild-release.elf'
        for line in subprocess.check_output([ARM+'nm',str(elf)],text=True).splitlines():
            f=line.split()
            if len(f)==3: self.symbols[f[2]]=int(f[0],16)
        for a,n in [(0x5000,'application.bin'),(0x10000,'extension.bin'),(0x12000,'bank.bin'),(0x13000,'settings.bin')]:
            self.u.mem_write(a,(build/n).read_bytes())
        start,end=self.symbols['_srelocate'],self.symbols['_erelocate']
        self.u.mem_write(start,bytes(self.u.mem_read(self.symbols['_etext'],end-start)))
        self.initial_ram=bytes(self.u.mem_read(0x20000000,0x4000))
        self.set(NVM+8,(3<<16)|2048); self.set(NVM+0x20,0xffff,2); self.set(NVM+0x14,1,1)
        self.commands=[]; self.busy=0; self.clear_status=False; self.command_error=False
        self.u.hook_add(UC_HOOK_MEM_WRITE,self.write); self.u.hook_add(UC_HOOK_CODE,self.code)

    def get(self,a,n=4): return int.from_bytes(self.u.mem_read(a,n),'little')
    def set(self,a,v,n=4): self.u.mem_write(a,v.to_bytes(n,'little'))
    def code(self,u,a,size,_):
        if self.clear_status:
            self.set(NVM+0x18,0,2); self.clear_status=False
        if self.busy:
            assert 0x20000000<=a<0x20004000,('flash execution during NVM operation',hex(a))
            self.busy-=1
            if not self.busy:
                self.set(NVM+0x14,1,1)
                if self.command_error: self.set(NVM+0x18,4,2)
    def write(self,u,access,a,size,value,_):
        if a<0x20000:
            assert 0x13000<=a and a+size<=0x14000,('unowned flash write',hex(a))
        if a==NVM+0x18: self.clear_status=True
        if a==NVM:
            assert value>>8==0xa5
            cmd=value&255; self.commands.append(cmd)
            target=self.get(NVM+0x1c)*2
            if cmd==2:
                assert target%256==0 and 0x13000<=target<=0x13f00
                self.u.mem_write(target,b'\xff'*256)
            if cmd in (2,4):
                if cmd==4: assert target%64==0 and 0x13000<=target<=0x13fc0
                self.set(NVM+0x14,0,1); self.busy=4
            else: assert cmd in (0x44,0x46)
    def run(self,name,*args,masked=0):
        address=self.symbols[name] if isinstance(name,str) else name
        for r in range(UC_ARM_REG_R0,UC_ARM_REG_R12+1): self.u.reg_write(r,0)
        for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args): self.u.reg_write(r,v)
        self.u.reg_write(UC_ARM_REG_PRIMASK,masked)
        self.u.reg_write(UC_ARM_REG_SP,0x20003f00); self.u.reg_write(UC_ARM_REG_LR,0x1f001)
        self.u.emu_start(address|1,0x1f000,count=20000000)
        assert self.u.reg_read(UC_ARM_REG_PC)==0x1f000,'Instruction budget exceeded.'
        assert self.u.reg_read(UC_ARM_REG_PRIMASK)==masked,'Interrupt state changed.'
        result=self.u.reg_read(UC_ARM_REG_R0)
        return result if result<0x80000000 else result-0x100000000


def main():
    if not __debug__: raise SystemExit('Assertions required.')
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    build=a.build.resolve(); out=a.output.resolve()
    assert out.is_relative_to(ROOT/'artifacts/private'); out.mkdir(exist_ok=False)
    m=Machine(build); bank=(build/'bank.bin').read_bytes()
    assert m.run('profile_runtime_init')==1 and not m.commands
    baseline=bytes(m.u.mem_read(0,0x20000))
    m.u.mem_write(0x4020,mailbox(bank,1,1))
    assert m.run('profile_runtime_init',masked=1)==1
    assert m.commands==[2,0x46,0x44,4,0x46],m.commands
    assert m.get(m.symbols['em_focal_mm10'],2)==350
    assert m.get(m.symbols['em_startup_aperture_av'],2)==4352
    assert load_setting(bank,bytes(m.u.mem_read(0x13000,4096)))['slot']==1
    after=bytes(m.u.mem_read(0,0x20000))
    assert baseline[:0x4020]==after[:0x4020] and baseline[0x403a:0x13000]==after[0x403a:0x13000]
    assert baseline[0x14000:]==after[0x14000:]
    m.u.mem_write(0x20000000,m.initial_ram); m.commands=[]
    assert m.run('profile_runtime_init')==1 and not m.commands
    assert m.get(m.symbols['em_focal_mm10'],2)==350
    io=m.run('pb_samd21_io'); write=m.get(io+8); erase=m.get(io+12)
    for offset in (1,64,4096,0xffffffff):
        assert m.run(erase,0,offset)==-1
    for offset in (0,1,64,4096,0xffffffff): assert m.run(write,0,offset,0x20003000)==-1
    assert not m.commands
    m.set(NVM+0x20,0,2)
    assert m.run('profile_runtime_init')==1,'Locked journal must remain readable.'
    assert m.run(erase,0,512)==-1 and not m.commands
    m.set(NVM+8,2048) # incorrect page size
    assert m.run('profile_runtime_init')==0 and not m.commands
    # Stuck initial READY: actual bounded RAM polling returns without issuing a command.
    n=Machine(build); n.set(NVM+0x14,0,1)
    assert n.run('profile_runtime_init')==0 and not n.commands
    # An NVM error leaves the old committed profile selected, no subsequent writes.
    n=Machine(build); n.u.mem_write(0x4020,mailbox(bank,1,1)); n.command_error=True
    assert n.run('profile_runtime_init')==1 and n.commands==[2]
    assert n.get(n.symbols['em_focal_mm10'],2)==580
    assert load_setting(bank,bytes(n.u.mem_read(0x13000,4096)))['generation']==0
    report=dict(hardwareAccess=False,compiledCandidate=True,
        tests=['unchanged boot makes no NVM commands','startup mailbox commits before metadata apply',
               'RAM execution while synthetic NVM busy','PRIMASK restored',
               'full flash outside journal/mailbox invariant','next boot consumes no extra writes',
               'out-of-range/unaligned operations rejected','locked journal readable but unwritable',
               'wrong NVM geometry rejected','initial READY timeout bounded',
               'NVM command error preserves committed selection and latches write fault'],
        limitations='Synthetic page buffer/register completion; no real power-loss, bus-stall, cache or camera qualification.')
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Compiled ARM startup and NVM guards passed with synthetic registers; no hardware access.')


if __name__=='__main__': main()

#!/usr/bin/env python3
"""Execute saved loader instructions with synthetic NVM/USB backends, never a device.

Requires the private pinned boot backup and the REA analysis Python environment.
No raw dump or identifiers are written to the public evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import *

ROOT=Path(__file__).resolve().parents[1]
BOOT_SHA='8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895'


class BootMachine:
    def __init__(self,boot):
        self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M0)
        self.u.mem_map(0,0x20000); self.u.mem_map(0x20000000,0x4000)
        self.u.mem_write(0,boot)
        # Pinned loader's .data load mapping; remaining low RAM starts zero.
        self.u.mem_write(0x20000000,boot[0x3670:0x3704])
        self.events=[]
        self.stubs={0x2534:self.record_write,0x29f0:self.receive,0x2a20:self.send}
        self.u.hook_add(UC_HOOK_CODE,self.code)
    def code(self,u,address,size,_):
        if address in self.stubs:
            result=self.stubs[address](self)
            if result is not None: u.reg_write(UC_ARM_REG_R0,result&0xffffffff)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def record_write(self,m):
        self.events.append(('write',m.u.reg_read(UC_ARM_REG_R0))); return -7
    def receive(self,m): self.events.append(('receive',)); return -7
    def send(self,m):
        self.events.append(('send',bytes(m.u.mem_read(m.u.reg_read(UC_ARM_REG_R0),m.u.reg_read(UC_ARM_REG_R1))))); return -7
    def get(self,a,n=4): return int.from_bytes(self.u.mem_read(a,n),'little')
    def run(self,address,*args):
        for r in range(UC_ARM_REG_R0,UC_ARM_REG_R12+1): self.u.reg_write(r,0)
        for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args): self.u.reg_write(r,v)
        self.u.reg_write(UC_ARM_REG_SP,0x20003e00); self.u.reg_write(UC_ARM_REG_LR,0x1f001)
        self.u.emu_start(address|1,0x1f000,count=100000)
        assert self.u.reg_read(UC_ARM_REG_PC)==0x1f000,'Instruction budget exceeded.'


def main():
    if not __debug__: raise SystemExit('Assertions required.')
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--boot-image',type=Path,default=ROOT/'references/private/usb-cap-followup-2026-10-10/full-flash-read1.bin')
    a=p.parse_args(); out=a.output.resolve()
    boot=a.boot_image.read_bytes()[:0x4000]
    assert len(boot)==0x4000 and hashlib.sha256(boot).hexdigest()==BOOT_SHA,'Wrong boot prefix.'
    assert out.is_relative_to(ROOT/'artifacts/private'); out.mkdir(exist_ok=False)
    operations=[]
    def args(m): return [m.u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
    row=BootMachine(boot)
    def read(m):
        _,address,destination,n=args(m)
        m.u.mem_write(destination,bytes(m.u.mem_read(address,n))); operations.append(('read',address,n))
    def erase(m):
        _,address,command,_=args(m); assert command==2 and address%256==0
        m.u.mem_write(address,b'\xff'*256); operations.append(('erase',address,256))
    def program(m):
        _,address,source,n=args(m); assert n==64
        m.u.mem_write(address,bytes(m.u.mem_read(source,n))); operations.append(('program',address,n))
    row.stubs.update({0xe2a:read,0xd18:erase,0xd38:program})
    before=bytes((i*29+7)%256 for i in range(0x20000))
    row.u.mem_write(0x4000,before[0x4000:])
    callback=BootMachine(boot); writes=[]
    def write(m):
        address,source,_,_=args(m); payload=bytes(m.u.mem_read(source,64))
        writes.append(address); row.u.mem_write(0x20002000,payload)
        row.run(0xe78,0x20000634,address,0x20002000,64)
        return 0
    callback.stubs[0x2534]=write
    request=bytes.fromhex('952768180101')+bytes((i*11+3)%256 for i in range(58))
    scratch=b'ABCDEF'
    callback.u.mem_write(0x2000056c,request+scratch)
    callback.run(0x257c,1)
    assert writes==[0x4000]
    assert callback.get(0x20000568,1)==2 and callback.get(0x20000004)==0x5000
    after=bytes(row.u.mem_read(0x4000,0x1c000))
    assert after[:64]==request[6:]+scratch
    assert after[64:]==before[0x4040:]
    assert operations==([('read',0x4000+i*64,64) for i in range(4)]+
                        [('erase',0x4000,256)]+[('program',0x4000+i*64,64) for i in range(4)])
    # The unsafe control: CHECK after START is a raw application page, not a query.
    callback.u.mem_write(0x2000056c,bytes.fromhex('952768180202')+bytes(58))
    callback.run(0x257c,1)
    assert writes==[0x4000,0x5000] and callback.get(0x20000004)==0x5040
    # A new machine stands for power-on reset; then CHECK reads metadata without writes.
    fresh=BootMachine(boot); fresh.u.mem_write(0x4000,after[:256])
    fresh.u.mem_write(0x2000056c,bytes.fromhex('952768180202')+bytes(58))
    fresh.run(0x257c,1)
    assert [e[0] for e in fresh.events]==['send','receive'] and fresh.get(0x20000568,1)==0
    report=dict(hardwareAccess=False,bootSHA256=hashlib.sha256(boot).hexdigest(),
        actualInstructionEntries=['0x257c dispatcher','0x0e78 row merge'],
        stubs='NVM page read/erase/program and USB send/rearm; no electrical or USB timing model',
        startOnly=dict(metadataBytes=58,scratchOverreadBytes=6,rowErases=1,pagePrograms=4,
                       logicalChangedRange=[0x4000,0x4040],applicationWrites=0,stateAfter=2),
        unsafeControl='CHECK while armed programmed 0x5000 and advanced pointer; detected',
        resetControl='Fresh initial RAM state admits read-only CHECK',
        fieldOwnership='Not established for every boot/application path; 0x4020..0x4039 remains experimental',
        transmissionEnabled=False,
        remainingQualification=['real zero-page START/reset behavior','metadata extension ownership',
            'full application/protected-data invariance after reconnect','ambiguous/lost ACK recovery',
            'new sparse-package installer and upper-region ownership'])
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Saved loader START/row-merge instructions: metadata-only logical write confirmed in model; unsafe follow-up control rejected.')


if __name__=='__main__': main()

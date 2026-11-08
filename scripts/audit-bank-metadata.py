#!/usr/bin/env python3
"""Offline metadata ownership audit of the exact saved loader, not live USB.

The scope is the normal pinned command dispatcher, startup branch and explicit
metadata-pointer references. USB/HAL initialization is stubbed, not emulated.
Original factory suffix contents are never printed or published.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR,UC_ARM_REG_SP,UC_ARM_REG_R0,UC_ARM_REG_R1

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('loader_test',ROOT/'scripts/test-metadata-only-loader.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


def main():
    if not __debug__: raise SystemExit('Assertions required.')
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--boot-image',type=Path,default=ROOT/'references/private/usb-cap-followup-2026-10-10/full-flash-read1.bin')
    a=p.parse_args(); boot=a.boot_image.read_bytes()[:0x4000]
    assert hashlib.sha256(boot).hexdigest()==module.BOOT_SHA
    assert int.from_bytes(boot[0x3670:0x3674],'little')==0x4000
    out=a.output.resolve(); assert out.is_relative_to(ROOT/'artifacts/private'); out.mkdir(exist_ok=False)
    m=module.BootMachine(boot); accesses=[]
    m.u.mem_write(0x4000,bytes((i*13+7)%256 for i in range(256)))
    m.u.hook_add(UC_HOOK_MEM_READ,lambda u,t,address,size,value,data: accesses.extend(range(address,address+size)),begin=0x4000,end=0x40ff)
    counts={'START':0,'CHECK':0,'READ':0,'ignored':0}
    for first in range(256):
        for second in range(256):
            request=bytes.fromhex('95276818')+bytes([first,second])+int(0x4020).to_bytes(4,'little')+bytes(54)
            m.u.mem_write(0x20000568,bytes([0])); m.u.mem_write(0x2000056c,request)
            m.events=[]; accesses.clear(); m.run(0x257c,1)
            if first==second==1:
                assert m.events[0]==('write',0x4000) and not accesses; counts['START']+=1
            elif first==second==2:
                assert set(accesses)==set(range(0x4000,0x4010)); counts['CHECK']+=1
            elif first==second==3:
                assert set(accesses)==set(range(0x4020,0x4060)); counts['READ']+=1
            else:
                assert m.events==[('receive',)] and not accesses; counts['ignored']+=1
    # The read tracer must catch a handler expanded to consume the proposed suffix.
    changed=bytearray(boot); assert changed[0x266e:0x2670]==bytes.fromhex('1022')
    changed[0x266e:0x2670]=bytes.fromhex('3a22')
    bad=module.BootMachine(bytes(changed)); reads=[]
    bad.u.hook_add(UC_HOOK_MEM_READ,lambda u,t,address,size,value,data: reads.extend(range(address,address+size)),begin=0x4000,end=0x40ff)
    bad.u.mem_write(0x2000056c,bytes.fromhex('952768180202')+bytes(58)); bad.run(0x257c,1)
    assert any(0x4020<=address<0x403a for address in reads)
    lock=module.BootMachine(boot); lock.u.mem_map(0x41004000,0x1000)
    lock.u.mem_write(0x20002010,(0x41004000).to_bytes(4,'little'))
    lock_cases=0
    for address in (0x4000,0x13000,0x1ffff):
        for bits in (0,1<<(address>>14)):
            lock.u.mem_write(0x41004020,bits.to_bytes(2,'little'))
            lock.run(0x1080,0x20002000,address)
            assert lock.u.reg_read(UC_ARM_REG_R0)==int(bits==0)
            lock_cases+=1
    branches=[]
    for cap in (False,True):
        start=module.BootMachine(boot); metadata_reads=[]; observed=[]
        start.u.mem_map(0x60000000,0x1000); start.u.mem_map(0x41004000,0x1000)
        start.u.mem_map(0xe000e000,0x1000)
        start.u.mem_write(0x41004420,(1<<23 if cap else 0).to_bytes(4,'little'))
        for address in (0x114,0x384,0x392,0x3380,0x31b0,0x2a50): start.stubs[address]=lambda m: 0
        registrations=[]
        def register(machine):
            assert machine.u.reg_read(UC_ARM_REG_R0)==0 and machine.u.reg_read(UC_ARM_REG_R1)==0x20000008
            registrations.append('RAM base+8 registration node'); return 0
        start.stubs[0x31b0]=register
        # Synthetic app vectors: execute the original 0x2510 jump and stop at
        # its reset destination. No camera/application firmware runs here.
        start.u.mem_write(0x5000,(0x20003f00).to_bytes(4,'little')+(0x18001).to_bytes(4,'little'))
        start.u.hook_add(UC_HOOK_CODE,lambda u,address,size,data: (observed.append('app vectors at 0x5000'),u.emu_stop()) if address==0x18000 else None)
        start.u.hook_add(UC_HOOK_CODE,lambda u,address,size,data: (observed.append('USB receive loop'),u.emu_stop()) if address==0x26f0 else None)
        start.u.hook_add(UC_HOOK_MEM_READ,lambda u,t,address,size,value,data: metadata_reads.append(address),begin=0x4000,end=0x403f)
        start.u.reg_write(UC_ARM_REG_SP,0x20003e00); start.u.reg_write(UC_ARM_REG_LR,0x1f001)
        start.u.emu_start(0x269d,0x1f000,count=10000)
        assert observed==(['USB receive loop'] if cap else ['app vectors at 0x5000']) and not metadata_reads
        assert len(registrations)==int(cap)
        if not cap: assert start.get(0xe000ed08)==0x5000 and start.u.reg_read(UC_ARM_REG_SP)==0x20003f00
        branches.append(dict(cap=cap,outcome=observed[0],metadataReads=0))
    report=dict(hardwareAccess=False,bootSHA256=module.BOOT_SHA,commandPairs=65536,counts=counts,
        interpretedMetadata='CHECK copies only 0x4000..0x400f; normal START has a fixed destination and does not interpret the old suffix',
        rawRead='READ may expose any address; this is opaque byte transport, not a settings-field interpretation',
        startupBranches=branches,negativeControl='CHECK copy length expanded to 58; suffix read detected',
        loaderLockCheck=dict(entry='0x1080',cases=lock_cases,index='address >> 14; host also checks actual 8 KiB regions'),
        pointerAudit=[{'pc':'0x12c','use':'initialize .data; first word points to metadata 0x4000'},
            {'pc':'0x25a2','use':'upload pointer at RAM base+4'},
            {'pc':'0x263a','use':'metadata pointer at RAM base+0, fixed 64-byte write'},
            {'pc':'0x266a','use':'metadata pointer, fixed 16-byte CHECK copy'},
            {'pc':'0x26d4','use':'USB registration node at RAM base+8, not the metadata pointer'}],
        ownershipDecision='Transfer bytes 0x4020..0x4039 to the pinned 4.8 application only during explicit full migration; preserve prefix 0x4003..0x401f and retain the entire original metadata in a unit-bound rollback backup.',
        limits=['specific boot hash only','USB/HAL initialization stubbed','no formal whole-program alias proof',
                'no analog flash or USB-reset qualification','no claim the vendor suffix was blank or unused by its old application'])
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Pinned-loader metadata audit passed: 65536 command pairs, both startup branches and suffix-read failing control. No hardware access.')


if __name__=='__main__': main()

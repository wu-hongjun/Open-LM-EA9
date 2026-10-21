#!/usr/bin/env python3
"""Offline bounded original boot RAM-write audit; inherits lane24 finite MMIO model."""
import importlib.util,json,hashlib
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[4]
p=ROOT/'firmware/upstream-hardening/followup/24-boot-entry/run.py'
spec=importlib.util.spec_from_file_location('boot24',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
boot=m.BOOT_PATH.read_bytes()[:0x4000]
assert hashlib.sha256(boot).hexdigest()=='8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895'
raw=(m.BUILD/'firmware.raw.bin').read_bytes() if (m.BUILD/'firmware.raw.bin').exists() else m.inputs()[2]
cases=[]
for calibration in (0,0xffffffff):
 machine=m.Machine(boot,raw,calibration=calibration)
 machine.put(0x40000438,0x20,1)
 machine.put(0x40000418,0x7f)
 machine.put(0x4000041c,0x7f)
 reads=[]
 writes=[]
 def write(u,access,a,n,value,_):
  if 0x20000000<=a<0x20004000:writes.append((a,n,u.reg_read(UC_ARM_REG_PC)))
 def stop(u,a,n,_):
  if a==0x5150:
   machine.termination="application_reset_entry";u.emu_stop()
 machine.u.hook_add(UC_HOOK_MEM_READ,lambda u,access,a,n,value,data: reads.append(a));machine.u.hook_add(UC_HOOK_MEM_WRITE,write);machine.u.hook_add(UC_HOOK_CODE,stop)
 machine.u.mem_write(0x20003f80,b'\xa5'*128)
 machine.run()
 assert machine.u.mem_read(0x20003f80,128)==b'\xa5'*128
 assert not any(a+n>0x20003f80 for a,n,pc in writes)
 cases.append(dict(calibration=hex(calibration),writes=len(writes),min_write=hex(min(a for a,n,pc in writes)),max_exclusive=hex(max(a+n for a,n,pc in writes)),retained_range=['0x20003f80','0x20004000'],sentinel_preserved=True,wdt_reset_cause_preserved=machine.get(0x40000438,1)==0x20,boot_reads_rcause=0x40000438 in reads,app_entry_apbamask=hex(machine.get(0x40000418)),app_entry_apbbmask=hex(machine.get(0x4000041c))))
print(json.dumps(dict(boot_sha256=hashlib.sha256(boot).hexdigest(),cases=cases,limitations='Ordinary PA23-low finite lane24 model. No timing, IRQ delivery, DMA, power or hardware validation. Stops at old application reset entry, before its CRT.'),indent=2))

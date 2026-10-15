#!/usr/bin/env python3
"""Offline, exact-input original reset-to-C3.5-main contract experiment.

No device, network, subprocess, updater, or application-state access. Run with
retained tools/rea-analysis/venv/bin/python. Only declared output is written.
MMIO is an explicit finite functional fixture, never physical execution.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from unicorn import (Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS,
                     UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
                     UC_PROT_READ, UC_PROT_EXEC)
from unicorn.arm_const import (UC_CPU_ARM_CORTEX_M0, UC_ARM_REG_CONTROL,
    UC_ARM_REG_PRIMASK, UC_ARM_REG_MSP, UC_ARM_REG_PSP, UC_ARM_REG_PC,
    UC_ARM_REG_LR, UC_ARM_REG_IPSR, UC_ARM_REG_SP, UC_ARM_REG_R0, UC_ARM_REG_R1)
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BOOT_PATH = ROOT/'references/private/usb-cap-followup-2026-10-10/full-flash-read1.bin'
BUILD = ROOT/'artifacts/private/absolute35a'
POLICY = HERE/'policy.json'

def sha(b): return hashlib.sha256(b).hexdigest()
def require(ok, why):
    if not ok: raise ValueError(why)
def word(b, o): return struct.unpack_from('<I', b, o)[0]

class Machine:
    """All original calls execute. Hardware-facing reads are explicit fixtures.

    No asynchronous interrupt delivery, exception stacking, timing, DMA, flash
    commands or electrical state. PPB words are a software model: NVIC W1S/W1C
    aliases are modeled; active state is IPSR=0 with no injected exception.
    Other peripherals are ordinary memory initialized zero, with readiness,
    calibration and PA23 overrides. This is sufficient for the traced paths,
    not a general SAMD21 emulator.
    """
    def __init__(self, boot, raw, control=0, primask=0, enabled=0, pending=0,
                 priority=0, calibration=0, strap=0, ready=0x1c, system_pending=0,
                 mutation=None):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB|UC_MODE_MCLASS)
        self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M0)
        for a,n in [(0,0x20000),(0x20000000,0x8000),(0x40000000,0x20000),
                    (0x41000000,0x10000),(0x42000000,0x10000),(0x60000000,0x1000),
                    (0xe000e000,0x2000),(0x806000,0x1000)]:
            self.u.mem_map(a,n)
        self.u.mem_write(0,boot)
        self.u.mem_write(0x5000,raw)
        # In-memory synthetic mutations; original files are never changed.
        if mutation == 'omit_msp': self.u.mem_write(0x2518,bytes.fromhex('00bf00bf'))
        if mutation == 'omit_vtor': self.u.mem_write(0x251e,bytes.fromhex('00bf'))
        if mutation == 'omit_primask_restore': self.u.mem_write(0x398,bytes.fromhex('00bf00bf'))
        if mutation == 'omit_nvm_enable': self.u.mem_write(0xdfc,bytes.fromhex('00bf'))
        if mutation == 'omit_nvm_pending_clear': self.u.mem_write(0xdfa,bytes.fromhex('00bf'))
        if mutation == 'enable_boot_tickint':
            # Change only the immediate of MOVS r2 at original 0x11c6.
            self.u.mem_write(0x11c6,bytes.fromhex('0722'))
        self.u.mem_protect(0,0x20000,UC_PROT_READ|UC_PROT_EXEC)
        self.put(0x806024,calibration)
        self.put(0x4000080c,ready) # oscillator/DFLL readiness fixture
        self.put(0x41004420,strap<<23) # PORT IN, DIR remains input in fixture
        self.enabled,self.pending = enabled,pending
        self.put(0xe000ed04,system_pending)
        self.u.mem_write(0xe000e400,bytes([priority])*32)
        self.u.mem_write(0xe000ed1c,bytes([priority])*8)
        self.u.reg_write(UC_ARM_REG_MSP,word(boot,0))
        self.u.reg_write(UC_ARM_REG_PSP,0x20006000)
        self.u.reg_write(UC_ARM_REG_CONTROL,control)
        self.u.reg_write(UC_ARM_REG_PRIMASK,primask)
        self.trace=[];self.core=[];self.special=[];self.states={};self.mmio=Counter()
        self.counts=Counter();self.termination=None;self.initializer_mode=False;self.synthetic_reads=[]
        self.decoder=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
        self.u.hook_add(UC_HOOK_CODE,self.code)
        self.u.hook_add(UC_HOOK_MEM_READ,self.read)
        self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
    def put(self,a,v,n=4): self.u.mem_write(a,v.to_bytes(n,'little'))
    def get(self,a,n=4): return int.from_bytes(self.u.mem_read(a,n),'little')
    def state(self):
        u=self.u
        return dict(control=u.reg_read(UC_ARM_REG_CONTROL),primask=u.reg_read(UC_ARM_REG_PRIMASK),
          msp=hex(u.reg_read(UC_ARM_REG_MSP)),psp=hex(u.reg_read(UC_ARM_REG_PSP)),
          sp=hex(u.reg_read(UC_ARM_REG_SP)),ipsr=u.reg_read(UC_ARM_REG_IPSR),
          vtor=hex(self.get(0xe000ed08)),nvic_enabled=hex(self.enabled),
          nvic_pending=hex(self.pending),system_pending=hex(self.get(0xe000ed04)),systick_ctrl=hex(self.get(0xe000e010)),
          systick_load=hex(self.get(0xe000e014)),nvm_inten=self.get(0x41004010),
          priorities_sha256=sha(bytes(u.mem_read(0xe000e400,32))+bytes(u.mem_read(0xe000ed1c,8))))
    def code(self,u,a,size,_):
        if a in [0x2510,0x251c,0x2520,0x5150,0x82b4,0x3380]:self.states[hex(a)]=self.state()
        if a in [0x82b4,0x3380] and not self.initializer_mode:
            self.termination='app_main' if a==0x82b4 else 'usb_branch_entry'
            u.emu_stop();return
        self.trace.append(a);self.counts[a]+=1
        if self.counts[a]>2000:
            self.termination='bounded_poll_stop';u.emu_stop();return
        ins=next(self.decoder.disasm(bytes(u.mem_read(a,size)),a,count=1))
        if ins.mnemonic in ['msr','mrs','cpsid','cpsie','dsb','isb','dmb']:
            self.special.append(dict(pc=hex(a),instruction=ins.mnemonic+' '+ins.op_str))
    def read(self,u,access,a,size,value,_):
        if a>=0x40000000:self.mmio[(a,size)]+=1
        if self.initializer_mode and a in [0x40001800,0x42000c00]:
            # EIC CTRL / SERCOM1 CTRLA SWRST completion, an explicit fixture.
            value=self.get(a,size)&~1
            self.put(a,value,size)
            self.synthetic_reads.append(dict(address=hex(a),width=size,value=hex(value)))
        aliases={0xe000e100:self.enabled,0xe000e180:self.enabled,
                 0xe000e200:self.pending,0xe000e280:self.pending}
        if a in aliases:self.put(a,aliases[a],size)
    def write(self,u,access,a,size,value,_):
        if a==0xe000e100:self.enabled|=value
        if a==0xe000e180:self.enabled&=~value
        if a==0xe000e200:self.pending|=value
        if a==0xe000e280:self.pending&=~value
        if 0xe000e000<=a<0xe0010000:
            self.core.append(dict(pc=hex(u.reg_read(UC_ARM_REG_PC)),address=hex(a),width=size,value=hex(value)))
        if a in [0x4100400c,0x41004010]:
            raise ValueError('unexpected NVM interrupt-enable register write')
    def call_initializer(self, address):
        self.initializer_mode=True
        self.u.reg_write(UC_ARM_REG_R0,0)
        self.u.reg_write(UC_ARM_REG_R1,0)
        self.u.reg_write(UC_ARM_REG_LR,0x1f001)
        self.u.emu_start(address|1,0x1f000,count=100000)
        require(self.u.reg_read(UC_ARM_REG_PC)==0x1f000,'initializer did not return')
        return self.state()
    def run(self):
        self.u.emu_start(0x12d,0x1f000,count=100000)
        require(self.termination is not None,'instruction budget without expected stop')
        return dict(termination=self.termination,instructions=len(self.trace),
          unique_instructions=len(set(self.trace)),trace_sha256=sha(b''.join(struct.pack('<I',a) for a in self.trace)),
          checkpoints=self.states,core_writes=self.core,special_instructions=self.special,
          final=self.state(),mmio_read_addresses=[dict(address=hex(a),width=s,count=n) for (a,s),n in sorted(self.mmio.items())])

def contract(r, initial):
    require(r['termination']=='app_main','normal path did not reach app main')
    e=r['checkpoints']['0x5150'];f=r['final']
    require(e['msp']=='0x20002c00','application MSP not loaded')
    require(e['vtor']=='0x5000','application VTOR not assigned before entry')
    require(e['control']==initial.get('control',0),'CONTROL changed')
    require(e['primask']==initial.get('primask',0),'PRIMASK not restored')
    require(int(e['nvic_enabled'],16)==initial.get('enabled',0)|0x20,'NVM IRQ enable contract')
    require(int(e['nvic_pending'],16)==initial.get('pending',0)&~0x20,'NVM pending clear contract')
    require(e['systick_ctrl']=='0x5' and e['systick_load']=='0xffffff','boot SysTick contract')
    require(e['system_pending']==hex(initial.get('system_pending',0)) and f['system_pending']==e['system_pending'],'system pending state changed')
    require(e['ipsr']==0 and f['ipsr']==0,'thread-only fixture changed mode')
    require(f['control']==e['control'] and f['primask']==e['primask'],'app reset normalized core state')
    require(f['nvic_enabled']==e['nvic_enabled'] and f['nvic_pending']==e['nvic_pending'],'app reset normalized NVIC state')
    require(e['priorities_sha256']==sha(bytes([initial.get('priority',0)])*40),'boot changed priorities')
    require(f['priorities_sha256']==e['priorities_sha256'],'app reset changed priorities')
    require(e['nvm_inten']==f['nvm_inten']==0,'fixture NVM interrupt enable changed')
    if initial.get('control',0)==0:
        require(e['sp']==e['msp'] and f['msp']=='0x20002bf0','MSP stack frame contract')
    else: require(e['sp']==e['psp'],'PSP selection not preserved')

def inputs():
    p=json.loads(POLICY.read_text());boot=BOOT_PATH.read_bytes()[:0x4000]
    require(sha(boot)==p['boot_sha256'],'boot pin mismatch')
    for name,digest in p['build_pins'].items():require(sha((BUILD/name).read_bytes())==digest,'build pin mismatch: '+name)
    manifest=json.loads((BUILD/'manifest.json').read_text())
    require(len(manifest['sources'])==46,'source count mismatch')
    for name,digest in manifest['sources'].items():require(sha((BUILD/name).read_bytes())==digest,'source pin mismatch: '+name)
    for name,digest in p['reference_pins'].items():require(sha((ROOT/name).read_bytes())==digest,'reference pin mismatch: '+name)
    raw=(BUILD/'raw.bin').read_bytes();elf=(BUILD/'hardened.elf').read_bytes()
    coverage=0
    for i in range(struct.unpack_from('<H',elf,44)[0]):
        off=word(elf,28)+i*struct.unpack_from('<H',elf,42)[0]
        kind,offset,_,load,size,_,_,_=struct.unpack_from('<8I',elf,off)
        if kind==1 and size:
            start=load-0x5000
            require(start==coverage and elf[offset:offset+size]==raw[start:start+size],'ELF/raw mismatch')
            coverage+=size
    require(coverage==len(raw),'ELF/raw coverage mismatch')
    require((BUILD/'contax-zeiss-50-f1-4.bin').read_bytes()[:len(raw)]==raw,'image/raw mismatch')
    require(word(raw,0)==0x20002c00 and word(raw,4)==0x5151,'app vector mismatch')
    require(word(raw,4*(16+5))==0x514d,'NVM vector not Dummy_Handler')
    # Bind every called application address to the pinned ELF symbol table.
    shoff=word(elf,32);shsize=struct.unpack_from('<H',elf,46)[0];shnum=struct.unpack_from('<H',elf,48)[0]
    sections=[struct.unpack_from('<10I',elf,shoff+i*shsize) for i in range(shnum)]
    symbols={}
    for section in sections:
        if section[1]!=2:continue
        strings=sections[section[6]];names=elf[strings[4]:strings[4]+strings[5]]
        for off in range(section[4],section[4]+section[5],section[9]):
            name,value,_,_,_,_=struct.unpack_from('<IIIBBH',elf,off)
            symbols[names[name:names.find(b'\0',name)].decode()]=value&~1
    for name,address in {'Reset_Handler':0x5150,'main':0x82b4,'Dummy_Handler':0x514c,
                         'delay_init':0x533c,'em_uart_init':0x6478,'em_eic_init':0x66f8}.items():
        require(symbols.get(name)==address,'ELF symbol mismatch: '+name)
    return p,boot,raw

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    p,boot,raw=inputs();cases=[];guards=[]
    configurations=[('reset_like',{}),('erased_synthetic_calibration',{'calibration':0xffffffff}),
      ('nonreset_masked',{'primask':1}),('nonreset_psp',{'control':2}),
      ('nonreset_nvic',{'enabled':0x400,'pending':0xa0,'priority':0xc0,'system_pending':0x14000000}),
      ('nonreset_combined',{'control':2,'primask':1,'enabled':0x410,'pending':0x420,'priority':0x80})]
    for name,config in configurations:
        r=Machine(boot,raw,**config).run();contract(r,config)
        require([i['pc'] for i in r['special_instructions']]==['0xdee','0xdf2','0x384','0x38a','0x38c','0x392','0x398','0x2518'],'unexpected special-register/interrupt instruction')
        require([w['pc'] for w in r['core_writes']]==['0x162','0xdec','0xdfa','0xdfc','0x11c4','0x11c8','0x251e','0x5192'],'unexpected PPB write path')
        cases.append(dict(name=name,synthetic_initial=config,result=r))
    r=Machine(boot,raw,strap=1).run()
    require(r['termination']=='usb_branch_entry' and '0x2510' not in r['checkpoints'],'strap-high branch control')
    cases.append(dict(name='strap_high_stops_before_usb_runtime',synthetic_initial={'strap':1},result=r))
    r=Machine(boot,raw,ready=0).run()
    require(r['termination']=='bounded_poll_stop' and '0x2510' not in r['checkpoints'],'missing-ready control')
    cases.append(dict(name='oscillator_not_ready_no_handoff',synthetic_initial={'ready':0},result=r))
    for mutation in ['omit_msp','omit_vtor','omit_primask_restore','omit_nvm_enable','omit_nvm_pending_clear','enable_boot_tickint']:
        config={'pending':0x20} if mutation=='omit_nvm_pending_clear' else {}
        r=Machine(boot,raw,mutation=mutation,**config).run()
        try:contract(r,config)
        except ValueError as e:guards.append(dict(mutation=mutation,rejected=True,reason=str(e)))
        else:raise ValueError('mutation survived: '+mutation)
    # Execute actual linked initialization routines separately after reset.
    # Foreground main, peripherals outside these routines and IRQ delivery are
    # not exercised by these three bounded leaf/API calls.
    initializer_cases=[]
    for priority in [0,0xc0]:
        m=Machine(boot,raw,priority=priority);m.run()
        stages=[]
        for name,address in [('delay_init',0x533c),('em_uart_init',0x6478),('em_eic_init',0x66f8)]:
            before=len(m.core);state=m.call_initializer(address)
            stages.append(dict(name=name,address=hex(address),state=state,core_writes=m.core[before:]))
        require(m.enabled==0x430,'application initializers must preserve IRQ5 and enable IRQ4/10')
        require(m.get(0xe000e010)==7 and m.get(0xe000e014)==47999,'application SysTick initialization')
        require(m.get(0xe000e404,1)==0x40,'EIC priority not explicitly set')
        require(m.get(0xe000e40a,1)==priority and m.get(0xe000ed23,1)==priority,'SERCOM1/SysTick priority unexpectedly normalized')
        initializer_cases.append(dict(initial_priority=priority,stages=stages,synthetic_reset_completion_reads=m.synthetic_reads))
    # These disprove an overbroad reset-like-entry assertion, not a reachable
    # defect under true processor reset. No NVIC exception is delivered here.
    for case,field,expected in [('nonreset_masked','primask',0),('nonreset_psp','control',0),('nonreset_nvic','nvic_pending','0x0')]:
        r=next(c['result'] for c in cases if c['name']==case)
        require(r['checkpoints']['0x5150'][field]!=expected,'sensitivity control failed')
        guards.append(dict(mutation='assume_reset_state_for_'+case,rejected=True,reason='injected non-reset state survives original handoff and application reset'))
    inputs() # Originals still exact after all mutations.
    report=dict(schema=1,runner_sha256=sha(Path(__file__).read_bytes()),policy_sha256=sha(POLICY.read_bytes()),
      source_manifest_hashes_verified=46,inputs=p,cases=cases,initializer_cases=initializer_cases,negative_controls=guards,
      result='pass',hardware_actions=0,limitations=p['limitations'])
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(result='pass',cases=len(cases),negative_controls=len(guards),output=str(args.output))))
if __name__=='__main__':main()

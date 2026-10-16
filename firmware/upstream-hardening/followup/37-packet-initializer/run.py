#!/usr/bin/env python3
"""Offline packet-storage audit: source pins, host fixtures, exact ARM reset.

Run with tools/rea-analysis/venv/bin/python. No device or application access.
--source is a private complete ARM build directory, not merely its src folder.
"""
import argparse, hashlib, json, re, runpy, shutil, struct, subprocess, tempfile
from collections import Counter
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_CPU_ARM_CORTEX_M0, UC_ARM_REG_MSP, UC_ARM_REG_PSP, UC_ARM_REG_CONTROL, UC_ARM_REG_PRIMASK, UC_ARM_REG_LR, UC_ARM_REG_PC
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE=ROOT/'artifacts/private/handoff36-repeat'; DEPS=ROOT/'tools/firmware-deps'
ARM=str(DEPS/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
NAMES=('emount_packets.c','emount_packets.h','startup_samd21.c')
def sha(b): return hashlib.sha256(b).hexdigest()
def need(ok,msg):
    if not ok: raise ValueError(msg)
def command(args,cwd): return subprocess.check_output(args,cwd=cwd,stderr=subprocess.STDOUT)
def c_tokens(s): return re.findall(r'\w+|[^\s]',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))
class ELF:
    def __init__(self,path):
        self.raw=path.read_bytes(); b=self.raw
        need(b[:6]==b'\x7fELF\x01\x01','little-endian ELF32 required')
        self.sections=[struct.unpack_from('<10I',b,struct.unpack_from('<I',b,32)[0]+i*40) for i in range(struct.unpack_from('<H',b,48)[0])]
        self.symbols={}
        for s in self.sections:
            if s[1]!=2: continue
            strings=self.sections[s[6]]; names=b[strings[4]:strings[4]+strings[5]]
            for off in range(s[4],s[4]+s[5],s[9]):
                name,value,size,info,other,index=struct.unpack_from('<IIIBBH',b,off)
                name=names[name:].split(b'\0',1)[0].decode()
                if name:self.symbols[name]=(value,size,index)
        self.loads=[]
        for i in range(struct.unpack_from('<H',b,44)[0]):
            p=struct.unpack_from('<8I',b,struct.unpack_from('<I',b,28)[0]+i*32)
            if p[0]==1 and p[4]:self.loads.append((p[3],b[p[1]:p[1]+p[4]]))
    def addr(self,n): return self.symbols[n][0]&~1 if n in ('Reset_Handler','ea9_packets_init','main') else self.symbols[n][0]
    def data(self,n):
        a,size,index=self.symbols[n];s=self.sections[index]
        need(s[1]!=8,'NOBITS symbol has no initializer: '+n)
        return self.raw[s[4]+a-s[3]:s[4]+a-s[3]+size]
    def end(self): return self.addr('_etext')+self.addr('_erelocate')-self.addr('_srelocate')

def build(work,manifest,only=None):
    units=manifest['units']+([] if 'motion_trace' in manifest['units'] else ['motion_trace'])
    flags=manifest['flags']; uf={**manifest['unitFlags'],'motion_trace':['-Os']}
    for unit in only or units:
        command([ARM+'gcc',*flags,*uf.get(unit,[]),'-Isrc','-I'+str(DEPS/'samd21-dfp-2/samd21a/include'),'-I'+str(DEPS/'CMSIS_5-5.9.0/CMSIS/Core/Include'),'-c','src/'+unit+'.c','-o',unit+'.o'],work)
    command([ARM+'gcc',*[u+'.o' for u in units],'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld','-Wl,--gc-sections','--specs=nano.specs','--specs=nosys.specs','-o','hardened.elf'],work)
    return ELF(work/'hardened.elf')

def execute(elf,expected,mutation=None,fill=0xa5,primask=0):
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M0)
    for a,n in [(0,0x20000),(0x20000000,0x8000),(0x40000000,0x20000),(0x41000000,0x10000),(0x42000000,0x10000),(0xe000e000,0x2000)]:u.mem_map(a,n)
    for a,b in elf.loads:u.mem_write(a,b)
    u.mem_write(0x20000000,bytes([fill])*0x8000)
    u.mem_write(0xe000ed08,struct.pack('<I',0x5000)) # boot has ALREADY selected app vectors
    u.reg_write(UC_ARM_REG_MSP,elf.addr('_estack'));u.reg_write(UC_ARM_REG_PSP,0x20006000)
    u.reg_write(UC_ARM_REG_CONTROL,0);u.reg_write(UC_ARM_REG_PRIMASK,primask)
    addr=elf.addr('ea9_data');start=elf.addr('ea9_packets_init');mask=elf.addr('packet_presence');values=elf.addr('packet_values')
    decoder=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
    reset=elf.addr('Reset_Handler'); rsize=elf.symbols['Reset_Handler'][1]
    calls=[i for i in decoder.disasm(bytes(u.mem_read(reset,rsize)),reset) if i.mnemonic=='bl' and int(i.op_str.lstrip('#'),16)==start]
    need(len(calls)==1,'exactly one reset initializer call required')
    if mutation=='missing_call':u.mem_write(calls[0].address,bytes.fromhex('00bf00bf'))
    if mutation=='bad_mask':
        byte=u.mem_read(mask+1,1)[0];u.mem_write(mask+1,bytes([byte^(byte&-byte)]))
    if mutation=='bad_value':u.mem_write(values,bytes([u.mem_read(values,1)[0]^1]))
    state={'active':False,'entered':0,'finished':0,'vtor':0,'main':False,'instructions':0,'init_instructions':0}; reads=Counter();read_offsets={'mask':[],'values':[]};writes=[]; minimum_sp=elf.addr('_estack');minimum_init_sp=minimum_sp;ret=None
    def code(uc,a,size,_):
        nonlocal ret,minimum_sp,minimum_init_sp
        state['instructions']+=1;minimum_sp=min(minimum_sp,uc.reg_read(UC_ARM_REG_MSP))
        if a==start:
            state['entered']+=1;state['active']=True;ret=uc.reg_read(UC_ARM_REG_LR)&~1
            need(bytes(uc.mem_read(elf.addr('_srelocate'),elf.addr('_erelocate')-elf.addr('_srelocate')))==bytes(uc.mem_read(elf.addr('_etext'),elf.addr('_erelocate')-elf.addr('_srelocate'))),'relocate segment differs before initializer')
            need(bytes(uc.mem_read(elf.addr('_szero'),elf.addr('_ezero')-elf.addr('_szero')))==bytes(elf.addr('_ezero')-elf.addr('_szero')),'BSS not zero before packet initializer')
        if state['active'] and a==ret:state['active']=False;state['finished']+=1
        if state['active']:
            state['init_instructions']+=1;minimum_init_sp=min(minimum_init_sp,uc.reg_read(UC_ARM_REG_MSP))
        if a==elf.addr('main'):
            need(bytes(uc.mem_read(addr,1272))==expected,'main packet bytes differ')
            state['main']=True;uc.emu_stop()
    def read(uc,access,a,size,value,_):
        if state['active']:
            if mask<=a<mask+159:need(a+size<=mask+159,'mask read overflow');reads['mask']+=size;read_offsets['mask'].extend(range(a-mask,a-mask+size))
            if values<=a<values+374:need(a+size<=values+374,'values read overflow');reads['values']+=size;read_offsets['values'].extend(range(a-values,a-values+size))
    def write(uc,access,a,size,value,_):
        if state['active'] and addr<=a<addr+1272:
            need(a+size<=addr+1272,'packet write overflow');writes.extend(range(a-addr,a-addr+size))
        if state['active']:need(addr<=a and a+size<=addr+1272 or elf.addr('_estack')-128<=a and a+size<=elf.addr('_estack'),'initializer write outside table/stack')
        if a==0xe000ed08:
            need(state['finished']==1 and writes==list(range(1272)),'VTOR rewrite precedes complete packet initializer')
            need(bytes(uc.mem_read(addr,1272))==expected,'VTOR packet bytes differ')
            state['vtor']+=1
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_READ,read);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.emu_start(reset|1,0x1f000,count=200000)
    need(state['main'] and state['vtor']==1 and state['entered']==state['finished']==1,'reset termination/order mismatch')
    # O2 constant-folds the first bitmap read to MOVS #0x3b.
    need(reads==Counter(mask=1271,values=374),'bounded read count mismatch')
    need(read_offsets['mask']==[i>>3 for i in range(1,1272)] and read_offsets['values']==list(range(374)),'array read offset/order mismatch')
    need(u.reg_read(UC_ARM_REG_PRIMASK)==primask,'unexpected PRIMASK change')
    return {**state,'reads':dict(reads),'written_bytes':len(writes),'packet_sha256':sha(bytes(u.mem_read(addr,1272))),'observed_reset_stack_bytes':elf.addr('_estack')-minimum_sp,'observed_reset_plus_initializer_stack_bytes':elf.addr('_estack')-minimum_init_sp,'incoming_primask':primask}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    source=a.source.resolve();need(source.is_relative_to(ROOT/'artifacts/private'),'private source required')
    m=json.loads((BASE/'manifest.json').read_text()); frozen=json.loads((ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json').read_text());need(m==frozen,'base manifest mismatch')
    for name,digest in m['sources'].items():need(sha((BASE/name).read_bytes())==digest,'base source pin '+name)
    original=ELF(BASE/'hardened.elf');expected=original.data('ea9_data');need(len(expected)==1272,'original ELF packet size')
    sourcepins={str(f.relative_to(source)):sha(f.read_bytes()) for f in sorted((source/'src').iterdir()) if f.suffix in ('.c','.h','.ld')}
    given=ELF(source/'hardened.elf'); initial_elf=sha(given.raw)
    candidate=json.loads((source/'manifest.json').read_text())
    need(candidate['sources']==sourcepins,'candidate manifest source pins differ')
    raw=(source/'raw.bin').read_bytes(); image=(source/'contax-zeiss-50-f1-4.bin').read_bytes()
    need(sha(image)==candidate['imageSHA256'] and image[:len(raw)]==raw,'candidate image pin differs')
    cursor=0
    for address,data in given.loads:
        need(address-0x5000==cursor and data==raw[cursor:cursor+len(data)],'candidate ELF/raw load mismatch');cursor+=len(data)
    need(cursor==len(raw),'candidate ELF/raw extent differs')
    with tempfile.TemporaryDirectory(prefix='packet37-audit-',dir=ROOT/'artifacts/private') as td:
        work=Path(td);shutil.copytree(source/'src',work/'src')
        check=work/'transform';(check/'src').mkdir(parents=True)
        for n in NAMES:shutil.copyfile(BASE/'src'/n,check/'src'/n)
        apply=runpy.run_path(str(HERE/'apply.py'))['apply'];apply(check)
        for n in NAMES:need(c_tokens((check/'src'/n).read_text())==c_tokens((source/'src'/n).read_text()),'generated source differs '+n)
        # Compile the original initializer independently; compare all bytes with its frozen ELF.
        host=work/'dump.c';host.write_text('#include <stdio.h>\n#include "emount_packets.h"\nint main(void){return fwrite(ea9_data,1,EA9_DATA_LEN,stdout)!=EA9_DATA_LEN;}\n')
        command(['cc','-std=c99','-I'+str(BASE/'src'),str(BASE/'src/emount_packets.c'),str(host),'-o',str(work/'dump')],work)
        need(command([str(work/'dump')],work)==expected,'original host initializer differs from frozen ARM ELF')
        # Explicit call models only packet reset initialization; poison first and repeat.
        host.write_text('#include <stdio.h>\n#include <string.h>\n#include "emount_packets.h"\nint main(void){for(int i=0;i<3;i++){memset(ea9_data,i?0xff:0xa5,EA9_DATA_LEN);ea9_packets_init();if(fwrite(ea9_data,1,EA9_DATA_LEN,stdout)!=EA9_DATA_LEN)return 1;}return 0;}\n')
        command(['cc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(work/'src'),str(work/'src/emount_packets.c'),str(host),'-o',str(work/'host')],work)
        need(command([str(work/'host')],work)==expected*3,'host poison/reinitialize fixture mismatch')
        rebuilt=build(work,m);need(rebuilt.loads==given.loads,'ARM rebuild load bytes differ')
        for n in ('ea9_packets','ea9_fixups'):need(given.data(n)==original.data(n),n+' descriptor/fixup differs')
        va,sz,idx=given.symbols['ea9_data'];need(sz==1272 and given.sections[idx][1]==8,'packet table must be NOBITS/BSS')
        mask=given.data('packet_presence');vals=given.data('packet_values');need(len(mask)==159 and len(vals)==374 and sum(x.bit_count() for x in mask)==374,'representation bounds')
        decoded=bytearray();j=0
        for i in range(1272):
            if mask[i//8]&(1<<(i%8)):decoded.append(vals[j]);j+=1
            else:decoded.append(0)
        need(bytes(decoded)==expected,'independent bitmap reconstruction mismatch')
        positive=[execute(given,expected,fill=fill,primask=pm) for fill,pm in [(0xa5,0),(0xff,1),(0,0)]]
        negative={}
        for name in ('missing_call','bad_mask','bad_value'):
            try:execute(given,expected,mutation=name)
            except ValueError as e:negative[name]=str(e)
            else:raise ValueError('negative control accepted: '+name)
        # Compile actual reordered startup: exact instruction execution must reject early VTOR.
        startup=work/'src/startup_samd21.c'; saved=startup.read_text(); bad=saved.replace('\tea9_packets_init();\n','');anchor='\tSCB->VTOR = ((uint32_t)pSrc & SCB_VTOR_TBLOFF_Msk);';need(bad.count(anchor)==1,'VTOR source anchor')
        startup.write_text(bad.replace(anchor,anchor+'\n\tea9_packets_init();'))
        early=build(work,m,['startup_samd21'])
        try:execute(early,expected)
        except ValueError as e:negative['early_vtor']=str(e)
        else:raise ValueError('early VTOR accepted')
        startup.write_text(saved)
        for n in NAMES:shutil.copyfile(BASE/'src'/n,check/'src'/n)
        packet=check/'src/emount_packets.c';packet.write_text(packet.read_text().replace('0xf0','0xf1',1))
        try:apply(check)
        except AssertionError as e:negative['bad_original_initializer_pin']=str(e)
        else:raise ValueError('changed original initializer accepted')
        # Whole-image measurement using identical flags and all other candidate sources.
        for n in NAMES:shutil.copyfile(BASE/'src'/n,work/'src'/n)
        uncompressed=build(work,m,['emount_packets','startup_samd21'])
        result={'status':'pass','source':str(source.relative_to(ROOT)),'sourceSHA256':sourcepins,'elfSHA256':initial_elf,'manifestSHA256':sha((source/'manifest.json').read_bytes()),'imageSHA256':candidate['imageSHA256'],'baseImageSHA256':m['imageSHA256'],'packetSHA256':sha(expected),'packetBytes':1272,'zeroBytes':expected.count(0),'nonzeroBytes':len(vals),'presenceBytes':len(mask),'allBytesIncludingPaddingEqual':True,'descriptorsAndFixupsEqual':True,'hostPoisonReinitializations':3,'hostSanitizers':'address,undefined','ARMRebuildLoadBytesEqual':True,'flags':m['flags'],'unitFlags':{**m['unitFlags'],'motion_trace':['-Os']},'positive':positive,'negativeControls':negative,'loadedEnd':given.end(),'marginBeforeDiagnostics':0x9c00-given.end(),'uncompressedLoadedEnd':uncompressed.end(),'loadedBytesSaved':uncompressed.end()-given.end(),'staticRAMBytes':given.addr('_ezero')-0x20000000,'uncompressedStaticRAMBytes':uncompressed.addr('_ezero')-0x20000000,'runnerSHA256':sha(Path(__file__).read_bytes()),'applicatorSHA256':sha((HERE/'apply.py').read_bytes()),'physicalIRQDeliveryModeled':False,'elapsedStartupTimeMeasured':False,'hardwareReportsSent':0,'wireParityClaimed':False,'factoryQualificationClaimed':False,'freezeRootCauseClaimed':False}
    need(sha((source/'hardened.elf').read_bytes())==initial_elf,'input ELF changed')
    for n,h in sourcepins.items():need(sha((source/n).read_bytes())==h,'input source changed: '+n)
    a.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps({k:v for k,v in result.items() if k not in ('sourceSHA256','flags','unitFlags')},indent=2))
if __name__=='__main__':main()

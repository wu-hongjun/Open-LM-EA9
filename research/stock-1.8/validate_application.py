#!/usr/bin/env python3
"""Finite app orchestration scenarios; original instructions + explicit I/O cuts."""
from validate_protocol import *
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_PC
protocol=json.loads((OUT/'protocol-validation.json').read_text())
lib.stock_restore.argtypes=[ctypes.POINTER(Model),ctypes.POINTER(ctypes.c_uint8)]
def io(address,index=0,constant=None):
 def f(machine):
  args=machine.calls[-1]['args'];v=args[index] if constant is None else constant
  original_events.append((address,v));return -7 # caller ignores status
 return f
m.stubs.update({0x609c:lambda mm:original_events.append((0x609c,(mm.calls[-1]['args'][1]<<16)|mm.calls[-1]['args'][0])),0x91c4:io(0x91c4,1),0x91ac:io(0x91ac,constant=0),0x66cc:0,0x66da:0,0x66fc:io(0x66fc),0x70d0:io(0x70d0),0x7a70:io(0x7a70),0x6a38:io(0x6a38,2),0x6918:io(0x6918,3),0x69b0:io(0x69b0,2),0x89a4:lambda mm:mm.raw})
def write_hook(u,kind,a,size,value,user):
 if a==0x60000014 and value==0x400:original_events.append((a,value))
 if a==0x60000018 and value==0x800000:original_events.append((a,value))
def wfi_hook(u,a,size,user):
 if a==0x5f7e:original_events.append((a,0));u.reg_write(UC_ARM_REG_PC,a+3)
m.u.hook_add(UC_HOOK_MEM_WRITE,write_hook);m.u.hook_add(UC_HOOK_CODE,wfi_hook)
def app_seed():
 b=proto_seed();setv(b,0x660,0x20000000);setv(b,0x654,105,1);setv(b,0x655,50,1);setv(b,0x695,27,1)
 return b
def app_check(a,arg,b):
 ctypes.memmove(ctypes.addressof(c),bytes(b),len(b));m.u.mem_write(0x20000000,bytes(b));m.calls.clear();events.clear();original_events.clear();m.raw=arg
 # DIR=0 means physical input selects IN. PA3 held low for shutdown scenarios.
 m.set(0x60000000,0);m.set(0x60000010,0);m.set(0x41004420,arg&4 if a==0x53a4 else 0)
 m.run(a,arg);actual=lib.stock_run(ctypes.byref(c),a,arg)
 after=bytes(m.u.mem_read(0x20000000,0x800));got=bytes(c.ram)
 assert after==got,(hex(a),[(hex(i),after[i],got[i]) for i in range(0x800) if after[i]!=got[i]][:20])
 assert events==original_events,(hex(a),events,original_events)
 assert actual==0,(hex(a),actual)
 # Persistence argument shapes observed at the original call sites.
 for call in m.calls:
  if call['address'] in ['0x6a38','0x69b0']:assert call['args'][:3]==[0x2000087c,0x4100,1]
  if call['address']=='0x6918':assert call['args']==[0x2000087c,0x4100,0x20000494,44]
 return bytearray(got)
counts=[]
entries=[0x5120,0x5188,0x51ac,0x5238,0x5260,0x5274,0x5280,0x52e8,0x53a4,0x54b8,0x54d8,0x5dd4,0x5d68,0x5da8]
for address in entries:
 for i in range(600):
  b=app_seed();setv(b,0x51c,i%3,1);setv(b,0x51f,[0,1,4,5,255][i%5],1);setv(b,0x520,(i//5)%15,1);setv(b,0x51e,(i//3)%2,1);setv(b,0x522,(i//7)%2,1)
  setv(b,0x523,i%3,1);setv(b,0x697,(i//2)%3,1);setv(b,0x699,[1,10,27,40,63,255][i%6],1)
  app_check(address,4*(i%2),b)
 counts.append({'entry':hex(address),'cases':600,'result':'pass'})
for i in range(600):
 b=app_seed();saved=rng.randbytes(44);m.u.mem_write(0x4100,saved);m.u.mem_write(0x20000000,bytes(b));m.run(0x8ae4)
 ctypes.memmove(ctypes.addressof(c),bytes(b),len(b));lib.stock_restore(ctypes.byref(c),(ctypes.c_uint8*44).from_buffer_copy(saved))
 assert bytes(c.ram)==bytes(m.u.mem_read(0x20000000,0x800))
counts.append({'entry':'0x8ae4','cases':600,'result':'pass'})
for i in range(1200):
 b=app_seed()
 for bit,offset in enumerate([0x52a,0x390,0x530,0x521,0x52c,0x604,0x51d,0x608,0x4bc,0x4b8]):setv(b,offset,(i>>bit)&1,1)
 setv(b,0x52d,[0,1,2,3,255][i%5],1);setv(b,0x674,[0,5,6,7,255][i%5],1)
 app_check(0x5e00,rng.randrange(16384),b)
counts.append({'entry':'0x5e00 bounded sensor/PA3-low/wake scenarios','cases':1200,'result':'pass'})
# Explicit connected handshake sequence, with caller-owned callback execution.
b=app_seed()
for a,v in [(0x522,1),(0x51f,4),(0x520,0),(0x51c,0),(0x51e,0),(0x697,0),(0x699,0),(0x51d,0)]:setv(b,a,v,1)
sequence=[(0x53a4,4),(0x53a4,0),(0x53a4,4),(0x53a4,0),(0x5120,0),(0x5238,0),(0x5280,0),(0x54d8,0),(0x5280,0)]
for address,arg in sequence:b=app_check(address,arg,b)
assert b[0x520]==6
counts.append({'sequence':'two RX edges, frame sync, status05, delayed status06','steps':len(sequence),'result':'pass'})
report={'input_sha256':hashlib.sha256(ROM).hexdigest(),'prior_cases_steps':protocol['combined_cases_steps'],'app_cases_steps':sum(x.get('cases',x.get('steps',0)) for x in counts),'combined_cases_steps':protocol['combined_cases_steps']+sum(x.get('cases',x.get('steps',0)) for x in counts),'results':counts,'external_contract':['Timer/DMA/NVM/delay/UART helpers are recorded stubs; NVM helpers return -7, ignored by caller','Critical-section helpers stubbed; no concurrency claim','Sensor fixed within each invocation; PA3 low at both shutdown samples','WFI explicitly skipped after recording event, representing a supplied wake','Original register pin reads use dummy RAM, no hardware','Settings restore uses independent synthetic44byte records'],'sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'stock_model.c',HERE/'stock_model.h',HERE/'validate_application.py']}}
(OUT/'application-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

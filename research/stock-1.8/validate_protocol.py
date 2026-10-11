#!/usr/bin/env python3
"""Additional original-byte oracle for protocol formatting and metadata."""
# Import intentionally reruns the core suite and preserves its fresh manifest.
from validate import *
core=json.loads((OUT/'validation.json').read_text())
lib.stock_frame.argtypes=[ctypes.POINTER(Model),ctypes.c_uint32,ctypes.c_uint32];lib.stock_frame.restype=ctypes.c_int
m.stubs[0x51c8]=lambda m:original_events.append((0x51c8,0))
m.stubs[0x9180]=lambda m:original_events.append((0x9180,m.calls[-1]['args'][1]))
slots={0x64c:0x38,0x650:0x64,0x65c:0xb4,0x664:0x188,0x68c:0x9c,0x670:0x90,0x658:0x19c,0x678:0x1a8}
def proto_seed():
 b=seed()
 for slot,offset in slots.items():setv(b,slot,0x20000000+offset)
 return b
def check(a,arg,b):
 ctypes.memmove(ctypes.addressof(c),bytes(b),len(b));m.u.mem_write(0x20000000,bytes(b));m.calls.clear();events.clear();original_events.clear()
 original_arg=0x20000000+arg if a==0x56cc else arg
 expected=m.run(a,original_arg);actual=lib.stock_run(ctypes.byref(c),a,arg)
 after=bytes(m.u.mem_read(0x20000000,0x800));got=bytes(c.ram)
 assert after==got,(hex(a),[(hex(i),after[i],got[i]) for i in range(0x800) if after[i]!=got[i]][:20])
 assert events==original_events,(hex(a),events,original_events)
 if a==0x66b8:assert actual==expected,(actual,expected)
 return got
counts=[]
for a in [0x66b8,0x567c,0x56cc,0x8a8c,0x5d2c,0x5510]:
 for i in range(600):
  b=proto_seed();arg=rng.randint(-2**31,2**31-1)
  if a==0x56cc:arg=0x350
  if a==0x5d2c:setv(b,0x527,i%2,1)
  if a==0x567c:setv(b,0x680,[0,15,16,23,24,34,35,49,50,69,70,65535][i%12],2)
  check(a,arg,b)
 counts.append({'entry':hex(a),'cases':600,'result':'pass'})
# Every command ID across pass/fail mode/class gates; malformed headers are
# intentional existing-memory inputs, not claims about transport acceptance.
for ident in range(256):
 for mode,klass in [(1,2),(0,2),(1,0),(4,2)]:
  b=proto_seed();setv(b,0x51f,mode,1);setv(b,0x697,klass,1);setv(b,0x699,ident,1);check(0x58a4,0,b)
counts.append({'entry':'0x58a4','cases':1024,'result':'pass'})
for hi in range(256):
 for lo in [0,0x55,0xaa,0xff]:
  b=proto_seed();setv(b,0x356,lo,1);setv(b,0x357,hi,1);check(0x56cc,0x350,b)
counts.append({'entry':'0x56cc full high-byte menu selectors','cases':1024,'result':'pass'})
for length in range(4,256):
 b=proto_seed();off=0x380
 ctypes.memmove(ctypes.addressof(c),bytes(b),len(b));m.u.mem_write(0x20000000,bytes(b));m.calls.clear();events.clear();original_events.clear()
 m.run(0x51d4,0x20000000+off,length);assert lib.stock_frame(ctypes.byref(c),off,length)==0
 assert bytes(c.ram)==bytes(m.u.mem_read(0x20000000,0x800)),length
 assert events==original_events
counts.append({'entry':'0x51d4','cases':252,'result':'pass'})
# Negative-control experiment: mutate only the immediate in an emulator copy,
# never the source file. A model retaining its data/address dependency must
# reproduce the collateral writes, while the unmodified model must disagree.
patched=Machine();patched.u.mem_write(0x8aa6,b'\x10')
b=proto_seed();check(0x8a8c,0,b);baseline=bytes(c.ram)
patched.u.mem_write(0x20000000,bytes(b));patched.run(0x8a8c);changed=bytes(patched.u.mem_read(0x20000000,0x800))
assert baseline!=changed
source=(HERE/'stock_model.c').read_text()
mut,n=re.subn(r'const unsigned descriptor = 0x18;', 'const unsigned descriptor = 0x10;',source);assert n==1
mp=OUT/'metadata-negative-control.c';mp.write_text(mut)
ml=compile_library(mp, 'metadata-negative-control')
mlib=ctypes.CDLL(str(ml));mlib.stock_run.argtypes=lib.stock_run.argtypes;mlib.stock_run.restype=ctypes.c_int32
ctypes.memmove(ctypes.addressof(c),bytes(b),len(b));mlib.stock_run(ctypes.byref(c),0x8a8c,0)
assert bytes(c.ram)==changed
mutation={'immediate_address':'0x8aa6','host_only_change':'0x18 to 0x10','unchanged_model':'mismatch detected','dependency_preserving_model':'matches patched-in-memory original instructions','changed_RAM_offsets':[hex(i) for i in range(0x800) if baseline[i]!=changed[i]]}
report={'input_sha256':hashlib.sha256(ROM).hexdigest(),'core_cases_steps':core['total_cases_steps'],'protocol_metadata_cases':sum(x['cases'] for x in counts),'combined_cases_steps':core['total_cases_steps']+sum(x['cases'] for x in counts),'results':counts,'metadata_mutation':mutation,'sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'stock_model.c',HERE/'stock_model.h',HERE/'validate.py',HERE/'validate_protocol.py']},'bounds':'Frame lengths4..255, valid SRAM pointers; host bounds failures are not stock validation','hardware':'No hardware; checksum pin/send helpers stubbed'}
(OUT/'protocol-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

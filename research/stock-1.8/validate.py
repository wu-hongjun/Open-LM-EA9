#!/usr/bin/env python3
"""Compare C state against immutable original Thumb instructions; host-only."""
from pathlib import Path
import sys,ctypes,random,json,hashlib,subprocess,re
from config import HERE, get_configuration, compile_library
from oracle import Machine,ROM,UC_HOOK_CODE
OUT=get_configuration().output
LIB=compile_library(HERE/'stock_model.c', 'stock_model')
Sink=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32)
class Model(ctypes.Structure):_fields_=[('ram',ctypes.c_uint8*0x800),('sink',Sink),('context',ctypes.c_void_p)]
lib=ctypes.CDLL(str(LIB));lib.stock_run.argtypes=[ctypes.POINTER(Model),ctypes.c_uint32,ctypes.c_int32];lib.stock_run.restype=ctypes.c_int32
rng=random.Random(0x180030)
events=[]
@Sink
def sink(ctx,a,v):events.append((a,v))
original_events=[]
def drive(address):
 def f(m):original_events.append((address,m.calls[-1]['args'][0]));return 0
 return f
m=Machine({a:drive(a) for a in [0x8e88,0x8ed8,0x8f28,0x8f78]})
# RAM-backed fake registers permit original 8e28 register writes to execute.
# No device access: values have no electrical/timing behavior.
m.u.mem_map(0x41004000,0x1000);m.u.mem_map(0x60000000,0x1000)
def hook(u,a,size,user):
 if a==0x8e28:original_events.append((a,0))
m.u.hook_add(UC_HOOK_CODE,hook)
c=Model();c.sink=sink
results=[];fixtures=[]
def setv(buf,a,v,n=4):buf[a:a+n]=(v&((1<<(8*n))-1)).to_bytes(n,'little')
def seed():
 b=bytearray(rng.randbytes(0x800))
 for a,v in [(0x4c0,500),(0x4c4,150),(0x4c8,300),(0x4e8,1280),(0x4ec,200),(0x4f0,200)]:setv(b,a,v)
 return b
def compare(a,arg,b):
 ctypes.memmove(ctypes.addressof(c),bytes(b),len(b));m.u.mem_write(0x20000000,bytes(b));m.calls.clear();events.clear();original_events.clear();m.raw=arg
 if a==0x8cc0:m.stubs[0x89a4]=lambda m:m.raw
 expected=m.run(a,*([0x200004c0,arg] if a==0x8bfc else [arg]));actual=lib.stock_run(ctypes.byref(c),a,arg)
 after=bytes(m.u.mem_read(0x20000000,0x800));got=bytes(c.ram)
 if after!=got:
  differences=[(hex(i),after[i],got[i]) for i in range(0x800) if after[i]!=got[i]]
  raise AssertionError((hex(a),arg,differences[:20]))
 assert events==original_events,(hex(a),events,original_events)
 if a in [0x8cc0,0x8d20,0x8bfc,0x8d94]:assert actual==expected,(hex(a),actual,expected)
 return bytearray(got)
for a in [0x8cc0,0x8dd4,0x8d20,0x8bfc,0x8d94,0x8e28,0x8fc8,0x8a2c,0x5308,0x5a94,0x5b98,0x5c08,0x5cc8,0x5a2c]:
 for i in range(600):
  b=seed();arg=rng.randint(-2**31,2**31-1)
  if a==0x8cc0:arg=rng.randrange(65536)
  if a in [0x8d20,0x8d94]:setv(b,0x4b0,[0,1,2,3,255][i%5],1);setv(b,0x4b8,i%3,1)
  if a==0x8a2c:setv(b,0x605,[0,9,10,11,255][i%5],1);setv(b,0x4b4,[0,299,300,301,65535][i%5],2)
  if a in [0x5308,0x5cc8]:setv(b,0x695,[0,22,23,27,36,255][i%6],1);setv(b,0x79f,[0,22,23,27,36,255][i%6],1)
  if a in [0x5a94,0x5b98,0x5c08,0x5cc8]:setv(b,0x52e,[0,1,2,3,4,5,6,10,255][i%9],1);setv(b,0x4b8,i%2,1);setv(b,0x52b,(i//2)%2,1);setv(b,0x526,(i//4)%2,1)
  if a==0x5a2c:arg=[0,0x1c,0x1d,0x24,255][i%5]
  compare(a,arg,b)
 results.append({'entry':hex(a),'random_boundary_cases':600,'result':'pass'})
# Explicit speed thresholds, sensor seam values and PID overflow histories.
edge_cases=0
for mode in [0,1,2,3,255]:
 for error in [-2147483648,-601,-600,-599,-301,-300,-299,-101,-100,-99,-1,0,1,99,100,101,299,300,301,599,600,601,2147483647]:
  b=seed();setv(b,0x4b0,mode,1);compare(0x8d20,error,b);edge_cases+=1
for ref in [0,8191,8192,16383,32768,65535]:
 for sample in [0,8191,8192,10000,10001,16383,32767,32768,65535]:
  b=seed();setv(b,0x49c,ref,2);compare(0x8cc0,sample,b);edge_cases+=1
for error,old,older,acc in [(2147483647,-2147483648,1,2147483647),(-2147483648,2147483647,-2147483648,-2147483648),(0,0,0,0),(1,0,0,0),(-1,0,0,0)]:
 b=seed()
 for address,value in [(0x4d0,old),(0x4d4,older),(0x4f4,acc)]:setv(b,address,value)
 compare(0x8bfc,error,b);edge_cases+=1
results.append({'sequence':'explicit thresholds, sensor seams and PID overflow','cases':edge_cases,'result':'pass'})
# Composed timeout/control sequence. Original routines run without function stubs
# except the four final motor drivers. Compare all modeled RAM on every step.
b=seed();setv(b,0x4a0,0);setv(b,0x605,0,1);setv(b,0x606,0,2);setv(b,0x638,0,2)
b=compare(0x8dd4,4144,b)
for i in range(302):b=compare(0x8a2c,0,b)
assert b[0x4b1]==0 and b[0x4b8]==1
results.append({'sequence':'retarget + 302 timer callbacks','steps':303,'result':'pass'})
# Scan first target uses limits, second uses retained target; completed injected as
# caller-owned input, not a claim of actual mechanics.
b=seed();setv(b,0xd,4144,2);setv(b,0xf,5632,2);setv(b,0x79f,36,1);setv(b,0x52e,0,1);setv(b,0x7a2,4000,2);setv(b,0x7a4,6000,2)
for i in range(5):
 if i in [2,3]:setv(b,0x4b8,1,1)
 b=compare(0x5a94,0,b);fixtures.append({'scan_step':i,'state':b[0x52e],'target_counts':int.from_bytes(b[0x4a8:0x4aa],'little',signed=True),'progress':b[0x1f]})
assert b[0x52e]==10
results.append({'sequence':'scan state progression with injected completion','steps':5,'result':'pass'})
# Deliberately wrong wrap constant must be caught by the same original-byte oracle.
mutated=OUT/'negative-control.c'
original_source=(HERE/'stock_model.c').read_text()
mutated_source,n=re.subn(r'16383\s*-\s*d', '16384 - d', original_source)
assert n==1, 'negative-control mutation must change exactly one expression'
mutated.write_text(mutated_source)
badlib=compile_library(mutated, 'negative-control')
bad=ctypes.CDLL(str(badlib));bad.stock_run.argtypes=lib.stock_run.argtypes;bad.stock_run.restype=ctypes.c_int32
b=seed();setv(b,0x49c,0,2);m.u.mem_write(0x20000000,bytes(b));m.raw=16383;m.run(0x8cc0)
ctypes.memmove(ctypes.addressof(c),bytes(b),len(b));bad.stock_run(ctypes.byref(c),0x8cc0,16383)
assert bytes(c.ram)!=bytes(m.u.mem_read(0x20000000,0x800)), 'negative control was not detected'
report={'negative_control':'16383→16384 unwrap mutation detected','input_sha256':hashlib.sha256(ROM).hexdigest(),'seed':0x180030,'results':results,'fixtures':fixtures,'total_cases_steps':8400+303+5+edge_cases,'oracle':'Original Thumb instructions, all 2048 modeled RAM bytes and driver events compared','limitations':['Unicorn Cortex-M0 selection accepts MOVW: no architecture legality proof','Motor drivers stubbed at final four entry points; stop register stores execute against dummy RAM pages','Synthetic random RAM, no per-unit calibration and no hardware timing','PID denominator fixed 200; zero denominator unsupported in C model'],'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'stock_model.c',HERE/'stock_model.h',HERE/'validate.py']}}
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

#!/usr/bin/env python3
"""Frozen-source field inventory for the reachable production defocus scale.
This complements manual call/alias review; it is not a general C analyzer.
"""
from pathlib import Path
import hashlib, json, re
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'firmware/upstream-hardening/build/final-33a'
manifest=json.loads((BASE/'manifest.json').read_text())
for name, digest in manifest['sources'].items():
    assert hashlib.sha256((BASE/name).read_bytes()).hexdigest()==digest
src=(BASE/'src/emount.c').read_text()
pack=(BASE/'src/emount_packets.c').read_text()
header=(BASE/'src/emount_packets.h').read_text()
constants={}
for text in (src,header,(BASE/'src/emount.h').read_text()):
    for name,value in re.findall(r'^#define\s+(\w+)\s+(0x[0-9a-fA-F]+|\d+)[uU]?\b',text,re.M):
        constants[name]=int(value,0)
array=pack.split('uint8_t ea9_data[EA9_DATA_LEN] = {',1)[1].split('};',1)[0]
values=[int(x,16) for x in re.findall(r'0x[0-9a-fA-F]+',array)]
assert len(values)==1272
assert constants['EA9_OFF_06']==0 and constants['EM06_DEFOCUS']==19
assert values[19:21]==[32,0]
# Only named production setter call is fixed-focal initialization.
all_c='\n'.join(p.read_text() for p in (BASE/'src').glob('*.c'))
calls=re.findall(r'em_set_focal_length\(([^)]*)\)',all_c)
assert sorted(calls)==['EM_FOCAL_MM10','uint16_t mm10'],calls
assert constants['EM_FOCAL_MM10']==500
focal=src.split('static uint8_t focal_step(',1)[1].split('\n}',1)[0]
ladder=[(int(a),int(b,16)) for a,b in re.findall(r'if \(mm >= (\d+)u\)\s*\{\s*return (0x[0-9A-Fa-f]+);',focal)]
assert next(value for threshold,value in ladder if 50>=threshold)==8

def address(expr,extra=None):
    names=constants | (extra or {})
    expr=re.sub(r'0x[0-9a-fA-F]+',lambda m:str(int(m[0],16)),expr)
    out=re.sub(r'\b[A-Za-z_]\w*\b',lambda m:str(names[m[0]]),expr)
    assert re.fullmatch(r'[\d\s+\-]+',out),out
    return eval(out,{'__builtins__':{}},{})

# Every direct store in emount.c. Dynamic tails and six-byte optical rows
# are enumerated over supersets of their reachable indexes.
assert constants['EM06_LEN_IDLE']==48 and constants['EM06_LEN_MAX']==56
assert constants['EM_ROW_BYTES']==6
direct={}
for expr in re.findall(r'ea9_data\[([^\]]+)\]\s*=',src):
    if expr in ('off','off + 1'):
        continue # put16, separately enumerated below
    offsets=set()
    for k in range(6):
        for length in range(48,65):
            offsets.add(address(expr,{'k':k,'len':length}))
    direct[expr]=sorted(offsets)
assert [expr for expr,offsets in direct.items() if 19 in offsets]==['EA9_OFF_06 + EM06_DEFOCUS']
assert all(20 not in offsets for offsets in direct.values())
put16_offsets=[]
for expr in re.findall(r'put16\(([^,]+),',src):
    if expr.startswith('uint16_t '):
        continue
    off=address(expr)
    put16_offsets += [off,off+1]
assert all(x not in (19,20) for x in put16_offsets)
assert constants['EM06_VEL_HIST']==38 and constants['EM06_VEL_HIST_N']==7
assert not {19,20}.intersection(range(38,45))
packets={int(i,16):int(off,16) for i,off in re.findall(r'\{ (0x[\da-f]+), (0x[\da-f]+),\s+\d+ \}',pack)}
fixups=[(int(i,16),int(off)) for i,off in re.findall(r'\{ (0x[\da-f]+),\s+(\d+), EA9_FIXUP_',pack)]
assert len(fixups)==8
fixup_offsets=[packets[i]+off for i,off in fixups]
assert all(x not in (19,20) for x in fixup_offsets)
transmit=src.split('static uint8_t em_transmit(',1)[1].split('\n}\n',1)[0]
assert not re.search(r'frame\[[^\]]+\]\s*=',transmit)
assert 'memcpy(snapshot, frame, len);' in transmit
assert re.findall(r'\bmem(?:cpy|move|set)\([^;]+;',transmit)==['memcpy(snapshot, frame, len);']
assert 65536+32768*8*4==1114112 < 2**31
print(json.dumps({'source_hashes_verified':len(manifest['sources']),
 'template_scale_bytes':values[19:21], 'post_init_scale_bytes':[8,0],
 'only_production_setter_argument':'EM_FOCAL_MM10=500',
 'direct_write_offsets':direct, 'put16_write_offsets':sorted(set(put16_offsets)),
 'fixup_write_offsets':fixup_offsets, 'velocity_alias_write_offsets':list(range(38,45)),
 'main_int32_defocus_abs_bound':1114112, 'main_int32_relative_abs_bound':196608,
 'result':'PASS: reachable production defocus scale remains 8'},indent=2))

#!/usr/bin/env python3
"""Compact RAM-only capture observation construction in a private staged tree."""
import argparse,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE_SHA='2e469f4a7f30e93ad4431bb2505ebc5ba5a0d1c66644a04c0dc34fcb49f5aa59'
def replace(s,old,new):
    assert s.count(old)==1,old
    return s.replace(old,new)
def apply(src):
    src=Path(src).resolve()
    assert src.is_relative_to(ROOT/'artifacts/private') and src.name=='src'
    assert src.parent.name!='handoff36-repeat'
    p=src/'emount.c';assert hashlib.sha256(p.read_bytes()).hexdigest()==BASE_SHA,'exact lane34 source required'
    assert 'void st_record(uint32_t ms, uint32_t identity, uint32_t payload);' in (src/'startup_trace.h').read_text()
    s=p.read_text()
    s=replace(s,'''    st_note(kind, (uint8_t)(identity >> 8), flags, (uint8_t)identity,
            (uint16_t)session, (uint16_t)(session >> 16), millis());
}''','''    st_record(millis(), (uint32_t)kind | (uint32_t)(identity & 0xff00u)
            | ((uint32_t)flags << 16) | ((uint32_t)(uint8_t)identity << 24), session);
}
static void em_trace_owner(uint8_t kind, const uint8_t *p, uint8_t flags,
                           uint32_t session)
{
    em_trace(kind, em_trace_identity(p), em_trace_flags() | flags, session);
}''')
    s=replace(s,'em_trace(ST_OWNER_OFFER, em_trace_identity(rx), em_trace_flags()\n\t\t    |','em_trace_owner(ST_OWNER_OFFER, rx,')
    s=replace(s,'em_trace(ST_OWNER_TAKE, em_trace_identity(request->bytes),\n                em_trace_flags() |','em_trace_owner(ST_OWNER_TAKE, request->bytes,')
    old='em_trace(ST_OWNER_COMPLETE, em_trace_identity(request->bytes),\n                    em_trace_flags() |'
    assert s.count(old)==2
    s=s.replace(old,'em_trace_owner(ST_OWNER_COMPLETE, request->bytes,')
    p.write_text(s)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);apply(p.parse_args().source)

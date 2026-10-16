"""Reviewed inverse of observation-only edits, compared with the frozen 3.6 C.

This is token equality after explicit transformations, not C equivalence or a
timing proof. It preserves original expressions, calls, and relative ordering.
"""
import re
import semantics as sem


def one(text, old, new):
    sem.require(text.count(old)==1, 'composition anchor missing/ambiguous: '+old[:60])
    return text.replace(old,new)


def remove_calls(text, names):
    """Remove standalone trace statements only; inspect balanced call syntax."""
    pattern=re.compile(r'(?m)^[ \t]*(?:'+names+r')\(')
    count=0
    while match:=pattern.search(text):
        depth=1;end=match.end()
        while end<len(text) and depth:
            if text[end]=='(':depth+=1
            if text[end]==')':depth-=1
            end+=1
        sem.require(depth==0 and text[end]==';','non-statement trace call')
        text=text[:match.start()]+text[end+1:];count+=1
    return text,count


def tokens(text):
    lexical=re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*.*?\*/|//[^\n]*|\w+|[^\s]',re.S)
    return [m[0] for m in lexical.finditer(text) if not m[0].startswith(('/*','//'))]


def control_inverse(name,text):
    text=one(text,'#include "motion_trace.h"','')
    if name=='main.c':
        text=one(text,'''    if (!focus_invalid()) {
        st_motion_completion(ST_MC_ATTEMPT, code | ((uint16_t)param << 8));
        em_post_event(code, param);
    } else st_motion_completion(ST_MC_SUPPRESSED, code | ((uint16_t)param << 8));''',
            '    if (!focus_invalid()) em_post_event(code, param);')
        text=one(text,'''\tif (focus_invalid()) { st_motion_completion(ST_MC_SUPPRESSED, 0); return SERVO_ABORTED; }
\treturn r.outcome;''','\treturn focus_invalid() ? SERVO_ABORTED : r.outcome;')
        branch='if (focus_invalid()) { st_motion_completion(ST_MC_SUPPRESSED, 0); return SERVO_ABORTED; }'
        sem.require(text.count(branch)==2,'focus invalid observation inventory')
        text=text.replace(branch,'if (focus_invalid()) return SERVO_ABORTED;')
        text,count=remove_calls(text,r'st_motion_\w+|st_terminal')
        sem.require(count==8,'main trace statement inventory')
    elif name=='servo.c':
        text,count=remove_calls(text,r'st_motion_\w+')
        sem.require(count==8,'servo trace statement inventory')
    elif name=='emount.c':
        begin=text.index('/* RAM-only ownership observations;')
        end=text.index('static const struct ea9_packet *find_packet',begin)
        text=text[:begin]+text[end:]
        text=one(text,'''\tuint32_t key, generation, trace_session;
\tuint16_t trace_identity;
\tuint8_t trace_flags;''','\tuint32_t key, generation;')
        begin=text.index('\t/* Capture once inside the existing admission mask.')
        end=text.index('\tPORT->Group[0].OUTSET.reg = (1u << EM_PIN_LENS_CS);',begin)
        text=text[:begin]+text[end:]
        text=one(text,'''\tif (level) em_trace(ST_OWNER_CS, 0,
\t    em_trace_flags() | (g_owner.capture ? ET_RAW : 0), g_session_generation);''','')
        text=one(text,'''\t\tint admitted = em_owner_offer(&g_owner, rx, view.length);
\t\tif (admitted && !g_owner.capture && rx[5] == EM_ID_SESSION) {''','''\t\tif (em_owner_offer(&g_owner, rx, view.length)
\t\t    && !g_owner.capture && rx[5] == EM_ID_SESSION) {''')
        text=one(text,'''\t\tif (ready) {
\t\t    g_status_due = 0;
\t\t    em_trace(ST_OWNER_PHASE, 0, ET_PHASE | ET_STATUS, g_session_generation);
\t\t}''','\t\tif (ready) g_status_due = 0;')
        text=one(text,'\t\tuint16_t trace_event = 0;','')
        text=one(text,'\t\t\ttrace_event = (uint16_t)(g_event_code[0] | ((uint16_t)g_event_param[0] << 8));','')
        text=one(text,'\t\tif (trace_event) st_motion_completion(ST_MC_TX_RETURN, trace_event);','')
        text,count=remove_calls(text,r'em_trace(?:_owner)?|st_motion_completion')
        sem.require(count==8,'capture trace statement inventory')
    else:
        raise ValueError('unreviewed control inverse: '+name)
    return text


def verify(build,base):
    output={}
    for name in ('main.c','servo.c','emount.c'):
        actual=control_inverse(name,(build/'src'/name).read_text())
        original=(base/'src'/name).read_text()
        sem.require(tokens(actual)==tokens(original),'non-observation control delta: '+name)
        output[name]=dict(originalTokens=len(tokens(original)),controlTokensEqual=True)
    return output

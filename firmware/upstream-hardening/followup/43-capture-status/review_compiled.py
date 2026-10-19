#!/usr/bin/env python3
"""Read-only callback binding check of private final ELF against pinned AF3.7."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
if not __debug__:raise RuntimeError('Assertions required')
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--candidate',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
base=ROOT/'artifacts/private/targeted37-repeat';candidate=a.candidate.resolve();out=a.output.resolve()
assert candidate.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private')
out.mkdir(exist_ok=False)
arm=ROOT/'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-'
def tool(suffix,*args):return subprocess.check_output([str(arm)+suffix,*map(str,args)],text=True,timeout=20)
def verify(build,tag):
    m=json.loads((build/'manifest.json').read_text())
    if tag=='baseline':assert m==json.loads((ROOT/'firmware/candidates/3.7.0/contax-zeiss-50-f1-4.manifest.json').read_text())
    for name,digest in m['sources'].items():assert sha(build/name)==digest,name
    assert sha(build/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']
    raw=out/(tag+'-elf.bin');tool('objcopy','-O','binary',build/'hardened.elf',raw)
    assert raw.read_bytes()==(build/'raw.bin').read_bytes()
    assert (build/'contax-zeiss-50-f1-4.bin').read_bytes()[:raw.stat().st_size]==raw.read_bytes()
    text=tool('objdump','-d',build/'hardened.elf');(out/(tag+'-linked.txt')).write_text(text)
    functions={};current=None;addresses={}
    for line in text.splitlines():
        match=re.match(r'^([0-9a-f]+) <([^>]+)>:$',line)
        if match:
            current=match[2];addresses[current]=int(match[1],16);functions[current]=[]
        elif current:functions[current].append(line)
    words={int(x,16):int(y,16) for x,y in re.findall(r'^\s*([0-9a-f]+):\s+[0-9a-f]+\s+\.word\s+0x([0-9a-f]+)',text,re.M)}
    mappings=[]
    for caller,callee,register,target in [('main','em_set_powerdown_handler','r0','powerdown_signal'),('main','em_set_shutdown_inhibit_handler','r0','motion_shutdown_inhibit'),('em_init','em_eic_init','r0','on_cs_edge'),('em_init','em_eic_init','r1','on_vd_edge')]:
        lines=functions[caller];calls=[i for i,line in enumerate(lines) if re.search(r'\bbl\s+[0-9a-f]+ <'+callee+'>',line)]
        assert len(calls)==1
        prefix=lines[:calls[0]]
        loads=[re.search(r'\bldr\s+'+register+r', \[pc, #[0-9]+\].*@ \(([0-9a-f]+) ',line) for line in prefix]
        loads=[x for x in loads if x];assert loads
        pointer=words[int(loads[-1][1],16)]
        assert pointer==addresses[target]|1,(caller,callee,register,target)
        mappings.append({'caller':caller,'setter':callee,'argument':register,'callback':target,'thumbPointerVerified':True})
    assert 'park_to_infinity' not in addresses
    maincalls=re.findall(r'\bbl\s+[0-9a-f]+ <([^>]+)>','\n'.join(functions['main']))
    return {'imageSHA256':m['imageSHA256'],'manifestSHA256':sha(build/'manifest.json'),'elfSHA256':sha(build/'hardened.elf'),'callbackMappings':mappings,'mainCallsQueryBeforePoll':any(x=='focus_answer_queries' and y=='em_poll' for x,y in zip(maincalls,maincalls[1:]))}
old=verify(base,'baseline');new=verify(candidate,'candidate')
# Same object code/relocations despite different debug source paths. The
# callbacks stored by em_init still flow through the unchanged EIC handler.
unchanged=[]
for unit in ['emount','em_eic']:
    outputs=[]
    for build in (base,candidate):
        text=tool('objdump','-dr',build/(unit+'.o'))
        outputs.append(text[text.index('Disassembly of section'):])
    if unit=='emount':
        # Version-byte initialization reuses r1 to derive the unchanged lens ID.
        changes=[('2137      \tmovs\tr1, #55\t@ 0x37','2138      \tmovs\tr1, #56\t@ 0x38'),
                 ('31b3      \tadds\tr1, #179\t@ 0xb3','31b2      \tadds\tr1, #178\t@ 0xb2')]
        normalized=outputs[0]
        for before,after in changes:
            assert normalized.count(before)==1 and outputs[1].count(after)==1
            normalized=normalized.replace(before,after)
        assert normalized==outputs[1],unit
    else:
        assert outputs[0]==outputs[1],unit
        unchanged.append(unit)
assert old['callbackMappings']==new['callbackMappings']
assert not old['mainCallsQueryBeforePoll'] and new['mainCallsQueryBeforePoll']
result={'status':'pass-static-compiled-callback-binding','runnerSHA256':sha(Path(__file__)),'baseline':old,'candidate':new,'identicalObjectDisassemblyAndRelocations':unchanged,'emountDifferences':'Only em_init version byte 55 to 56 and compensating addition 179 to 178; final lens ID remains 234. All remaining disassembly and relocations match.','legacyParkSymbolAbsent':True,'hardwareAccess':False,'limits':'Static pointer/relocation and loop-call placement checks, not IRQ timing or execution coverage.'}
(out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'callbackMappings':4,'unchangedObjects':unchanged,'queryBeforePollAdded':True}))

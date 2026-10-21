#!/usr/bin/env python3
"""Exact AF4.1 offline ELF/source/stack/reset/WDT audit; no device operations."""
import argparse,copy,hashlib,json,re,struct,subprocess
from pathlib import Path
if not __debug__: raise SystemExit('Ordinary Python required: assertions are audit gates.')
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--policy',type=Path,default=HERE/'compiled-policy.json');a=p.parse_args()
build=a.build.resolve();assert build.is_relative_to(ROOT/'artifacts/private') and a.output.resolve().is_relative_to(ROOT/'artifacts/private')
policy=json.loads(a.policy.read_text());review=json.loads((HERE/'stack-reproduction.json').read_text());reviewed=json.loads((HERE/'compiled-policy.json').read_text())
assert sha(HERE/'compiled-policy.json')==review['reviewedPolicySHA256']
compare=copy.deepcopy(policy)
for name in ('hardened.elf','hardened.map'):compare['pins'][name]=reviewed['pins'][name]
assert compare==reviewed,'Only container pins may change'
base=HERE.parent/'followup/38-exact37-review/audit.py';assert sha(base)==policy['baseAnalyzerSHA256']
original=base.read_text();assert original.count('== 3044,')==1 and original.count('staticRAMBytes=3044,')==1
adapted=original.replace('== 3044,','== 3048,').replace('staticRAMBytes=3044,','staticRAMBytes=3048,')
assert hashlib.sha256(adapted.encode()).hexdigest()==policy['adaptedAnalyzerSHA256']
module={'__file__':str(base),'__name__':'astra41_analyzer'};exec(compile(adapted,str(base),'exec'),module)
tool=str(module['TOOL']);assert sha(Path(tool))==review['objdumpSHA256']
outputs={}
for option,pin in review['normalizedOutputSHA256'].items():
 text=subprocess.check_output([tool,option,str(build/'hardened.elf')],text=True)
 outputs[option]=text
 assert hashlib.sha256(text.replace(str(build/'hardened.elf'),'<ELF>').encode()).hexdigest()==pin,option
for name in ('hardened.elf','hardened.map'):policy['pins'][name]=sha(build/name)
result=module['audit'](build,policy,8192)
m=json.loads((build/'manifest.json').read_text());raw=(build/'raw.bin').read_bytes();image=(build/'contax-zeiss-50-f1-4.bin').read_bytes()
assert m['loaderVersion']==[4,1,0] and m['codeAndDataEnd']==39412 and m['codeMarginBeforeDiagnostics']==524
assert m['staticRAMBytes']==3048 and m['diagnosticPages']==16 and m['reservedStackBytes']==8192
assert len(raw)==18932 and len(image)==20480 and image[:len(raw)]==raw and image[len(raw):]==b'\xff'*(len(image)-len(raw))
assert 0x5000+len(raw)<=0x9b00 and m['imageSHA256']==sha(build/'contax-zeiss-50-f1-4.bin')
base40=ROOT/'artifacts/private/reference40-repeat';bm=json.loads((base40/'manifest.json').read_text())
assert sha(base40/'manifest.json')==m['baseManifestSHA256']
assert sorted(n for n,v in m['sources'].items() if bm['sources'].get(n)!=v)==policy['sourceDeltaFrom40']
assert m['units']==bm['units'] and m['flags']==bm['flags']
flags=copy.deepcopy(bm['unitFlags']);flags['servo']=['-Os'];assert m['unitFlags']==flags
heads=list(re.finditer(r'^([0-9a-f]+) <(.+)>:\n',outputs['-d'],re.M));bodies={h[2]:outputs['-d'][h.end():heads[i+1].start() if i+1<len(heads) else len(outputs['-d'])].strip() for i,h in enumerate(heads)}
symbols={}
for line in outputs['-t'].splitlines():
 f=line.split()
 if len(f)>=5 and re.fullmatch('[0-9a-f]{8}',f[0]):symbols[f[-1]]=int(f[0],16)
word=lambda address:struct.unpack_from('<I',raw,address-0x5000)[0]
assert symbols['retained']==0x20003fc0 and symbols['_ezero']==0x20000be8 and symbols['_estack']==0x20002be8
assert symbols['_sstack']==symbols['_ezero'] and symbols['_estack']<symbols['retained']
# Independently inspect ELF32 section records; NOLOAD is NOBITS and has no load data.
elf=(build/'hardened.elf').read_bytes();shoff=struct.unpack_from('<I',elf,32)[0];shsize,shnum,shstr=struct.unpack_from('<HHH',elf,46)
sections=[struct.unpack_from('<10I',elf,shoff+i*shsize) for i in range(shnum)];strings=sections[shstr];names=elf[strings[4]:strings[4]+strings[5]]
section=lambda name:next(s for s in sections if names[s[0]:].split(b'\0',1)[0].decode()==name)
assert section('.noinit')[1:4]==(8,3,0x20003fc0) and section('.noinit')[5]==56
assert section('.stack')[5]==8192 and section('.bss')[3]+section('.bss')[5]==symbols['_ezero']
assert word(0x5000)==symbols['_estack'] and word(0x5004)==symbols['Reset_Handler']|1 and word(0x500c)==symbols['HardFault_Handler']|1
assert word(0x5048)==symbols['Dummy_Handler']|1 # WDT vector: EW disabled
assert symbols['__preinit_array_start']==symbols['__preinit_array_end']==symbols['__init_array_start']
assert symbols['__init_array_end']-symbols['__init_array_start']==4 and word(symbols['__init_array_start'])==symbols['frame_dummy']|1
for off,n in ((48,'pump'),(52,'focus_retarget'),(56,'focus_abort')):assert word(symbols['STOCK']+off)==symbols[n]|1
for n,pin in policy['reviewedFunctionDisassemblySHA256'].items():assert hashlib.sha256(bodies[n].encode()).hexdigest()==pin,n
# Exact instruction anchors supplemented by complete reviewed body pins above.
for name,fragments in {
 'HardFault_Handler':['cpsid\ti','dsb\tsy','str\tr1, [r0, #0]','e000ed0c','05fa0004'],
 'st_watchdog_start':['00002004','00010304','00004403','movs\tr2, #9'],
 'st_health':['cmp\tr3, #249','<st_checkpoint>','movs\tr3, #165','strb\tr3, [r4, #8]'],
 'st_crash_boot':['<motor_emergency_release>','<st_init>','<st_boot_record>','<st_halt>'],
 'servo_move_from':['ldr\tr3, [r4, #52]','ldr\tr3, [r4, #56]','ldr\tr3, [r4, #48]','<st_health>']}.items():
 for fragment in fragments:assert fragment in bodies[name],(name,fragment)
assert not re.search(r'\b(push|pop|sp)\b',bodies['HardFault_Handler'])
assert result['functionBounds']['HardFault_Handler']['frameBytes']==0
for name,sequence in {
 'main':['<st_crash_boot>','<board_init_pins>','<clock_init>','<delay_init>','<st_watchdog_start>','<motor_init>','<motor_release>','<em_init>','<abs_encoder_set_reference>','<st_watchdog_arm>','<st_health>'],
 'st_crash_boot':['<motor_emergency_release>','<st_init>','<st_boot_record>','<st_halt>'],
 'st_health':['<st_checkpoint>','strb\tr3, [r4, #8]']}.items():
 positions=[bodies[name].index(x) for x in sequence];assert positions==sorted(positions),name
# Current library machine stack operations remain the reviewed prior operations.
normal=lambda lines:[re.sub(r'^\s*[0-9a-f]+:\s+[0-9a-f]+\s+','',x).strip() for x in lines]
for name,old in policy['baselineLibraryStackInstructions'].items():
 new=[x.strip() for x in bodies[name].splitlines() if re.search(r'\b(push|pop)\b|\bsp\b',x)]
 assert normal(new)==normal(old),name
edges={(c['caller'],t) for c in result['calls'] for t in c['targets']}
callers=lambda n:sorted(c for c,t in edges if t==n)
expected={'st_flush':['powerdown_signal','st_fail'],'st_terminal':['powerdown_signal','st_fail'],'append':['st_boot_record','st_flush','st_terminal'],'st_write_page':['append'],'st_read_page':['append','st_init'],'st_health':['main','servo_move_from'],'st_checkpoint':['st_health'],'st_boot_record':['st_crash_boot'],'st_crash_boot':['main']}
for n,owners in expected.items():assert callers(n)==owners,(n,callers(n))
def descendants(n,seen=None):
 seen=set() if seen is None else seen
 if n in seen:return seen
 seen.add(n)
 for c,t in edges:
  if c==n:descendants(t,seen)
 return seen
for n in ('EIC_Handler','SERCOM1_Handler','SysTick_Handler','st_health','st_checkpoint','HardFault_Handler'):
 assert not descendants(n)&{'append','st_write_page','st_read_page','st_flush','st_terminal','st_fail'},n
controls=[]
for name,edit in [('unknown-indirect',lambda q:q['indirectCalls'].pop('72ec')),('unknown-library',lambda q:q['libraryFrames'].pop('memcpy')),('recursive-callback',lambda q:q['indirectCalls']['72ec'].__setitem__('targets',['servo_move_from'])),('wrong-image-pin',lambda q:q['pins'].__setitem__('contax-zeiss-50-f1-4.bin','0'*64))]:
 bad=copy.deepcopy(policy);edit(bad)
 try:module['audit'](build,bad,8192)
 except ValueError as e:controls.append(dict(case=name,rejected=True,reason=str(e)))
 else:raise AssertionError(name)
result.update(status='passed-conditional-final41-compiled',compiledNVMCallerGates={n:callers(n) for n in expected},negativeControls=controls,retainedAddress=hex(symbols['retained']),retainedBytes=56,staticPlusRetainedRAMBytes=3104,exactHardFaultVectorAndStacklessReset=True,watchdogNominalSeconds=4,healthRequires250AdvancedTicksAndNotBusy=True,healthForegroundOnly=True,sourceDeltaFrom40=policy['sourceDeltaFrom40'],servoOptimizationOnlyFlagDelta=True,reviewedPolicySHA256=sha(HERE/'compiled-policy.json'),auditRunnerSHA256=sha(Path(__file__)),reproductionContractSHA256=sha(HERE/'stack-reproduction.json'),hardwareReportsSent=0,cameraQualified=False)
with a.output.open('x') as out:json.dump(result,out,indent=2);out.write('\n')
print(json.dumps({k:result[k] for k in ('status','maximumAllVectorPriorityBytes','staticRAMBytes','sourceHashesVerified','unresolvedCompiledEdges','recursiveComponents')},indent=2))

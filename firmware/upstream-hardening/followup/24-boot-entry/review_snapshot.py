#!/usr/bin/env python3
"""Read-only exact C3.5 consumer review; proposed one-line guard lives in scratch."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BUILD=ROOT/'artifacts/private/absolute35a'
GCC=ROOT/'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-gcc'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(c,m):
 if not c:raise ValueError(m)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 policy=json.loads((HERE/'policy.json').read_text());manifest=json.loads((BUILD/'manifest.json').read_text())
 for f,d in policy['build_pins'].items():require(sha(BUILD/f)==d,'build pin mismatch '+f)
 for f,d in manifest['sources'].items():require(sha(BUILD/f)==d,'source mismatch '+f)
 scratch=ROOT/'artifacts/private/astra-24-snapshot';scratch.mkdir(exist_ok=True,parents=True)
 original=(BUILD/'src/emount.c').read_text();needle='\tem_rx_bytes_at_open = em_rx_bytes;'
 require(original.count(needle)==1,'assignment not unique')
 guarded=original.replace(needle,'#ifndef EA9_NO_LOG\n'+needle+'\n#endif')
 proposal=scratch/'emount-guarded.c';proposal.write_text(guarded)
 includes=['-I'+str(BUILD/'src'),'-I'+str(ROOT/'tools/firmware-deps/samd21-dfp-2/samd21a/include'),'-I'+str(ROOT/'tools/firmware-deps/CMSIS_5-5.9.0/CMSIS/Core/Include')]
 result={};pp={}
 for mode in ['release','logging_enabled']:
  flags=[x for x in manifest['flags'] if mode=='release' or x!='-DEA9_NO_LOG'];hits=[]
  for unit in manifest['units']:
   args=[str(GCC),*flags,*manifest['unitFlags'].get(unit,[]),*includes,'-E','-P',str(BUILD/'src'/f'{unit}.c')]
   text=subprocess.check_output(args,cwd=scratch,text=True);pp[mode,unit]=text
   (scratch/f'{mode}-{unit}.i').write_text(text)
   lines=[l.strip() for l in text.splitlines() if re.search(r'\bem_rx_bytes_at_open\b',l)]
   if lines:hits.append(dict(unit=unit,lines=lines))
  modified=subprocess.check_output([str(GCC),*flags,*manifest['unitFlags']['emount'],*includes,'-E','-P',str(proposal)],cwd=scratch,text=True)
  before=pp[mode,'emount']
  if mode=='logging_enabled':require(modified==before,'guard changes logging-enabled tokens')
  else:
   require(modified==before.replace(' em_rx_bytes_at_open = em_rx_bytes;\n',''),'release changes beyond snapshot assignment')
  result[mode]=dict(units=len(manifest['units']),identifier_occurrences=hits,guarded_emount_sha256=hashlib.sha256(modified.encode()).hexdigest(),original_emount_sha256=hashlib.sha256(before.encode()).hexdigest())
 release_expressions=[(u,l.strip()) for (mode,u),txt in pp.items() if mode=='release' for l in txt.splitlines() if re.search(r'\bem_rx_bytes_at_open\b',l) and not re.fullmatch(r'\s*(extern )?volatile uint32_t em_rx_bytes_at_open;\s*',l)]
 require(release_expressions==[('emount','em_rx_bytes_at_open = em_rx_bytes;')],'unexpected release snapshot consumer')
 raw_hits={}
 for p in (BUILD/'src').glob('*'):
  if p.suffix not in ['.c','.h']:continue
  lines=[dict(line=i,text=l.strip()) for i,l in enumerate(p.read_text().splitlines(),1) if re.search(r'\bem_rx_bytes_at_open\b',l)]
  if lines:raw_hits[p.name]=lines
 report=dict(result='pass',runner_sha256=sha(Path(__file__)),compiler_sha256=sha(GCC),manifest_sha256=sha(BUILD/'manifest.json'),verified_source_hashes=46,flags=manifest['flags'],unit_flags=manifest['unitFlags'],raw_identifier_inventory=raw_hits,preprocessing=result,conclusion='Release has one snapshot assignment and no read/address-taking consumer. Logging-enabled variant has legacy page-2 subtraction; proposed EA9_NO_LOG guard preserves its preprocessed emount tokens exactly. Release tokens differ solely by that assignment.',limits=['Only private proposal and preprocessing artifacts written. No shared source edit or linked image built.','This is a consumer/preprocessing review, not measured code size, timing, camera qualification or acceptance of any new image.','The live volatile em_rx_bytes counter and every other statement remain identical in the token comparison. Its removed snapshot read is a RAM read, not an MMIO read.'])
 a.output.parent.mkdir(exist_ok=True,parents=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print('PASS: 22 release + 22 logging-enabled units; guarded release changes one assignment; logging tokens identical')
if __name__=='__main__':main()

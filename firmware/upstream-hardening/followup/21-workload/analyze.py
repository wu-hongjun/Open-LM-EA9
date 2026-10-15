#!/usr/bin/env python3
"""Offline public-capture workload summary; never accesses device/private capture data."""
import argparse, collections, hashlib, importlib.util, json, re, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
SIZES={0x1c:1,0x1d:5,0x1f:14,0x3c:8,0x22:3,0x2e:3,0x2f:3,0x34:24,0x4a:12}
def validated(b):
    if len(b)<9 or b[0]!=0xf0:return False
    n=int.from_bytes(b[1:3],'little')
    return 9<=n<=len(b) and b[n-1]==0x55 and sum(b[1:n-3])%65536==int.from_bytes(b[n-3:n-1],'little')
def records(b):
    n=int.from_bytes(b[1:3],'little');i=19;tags=[]
    while i<n-3:
        tag=b[i];size=SIZES.get(tag,0)
        if not size or i+size>n-3:return tags,False
        tags.append(tag);i+=size
    return tags,i==n-3
def summary(rows):
    f4=[r for r in rows if r['b'][5]==4 and r['direction']=='body-to-lens']
    f6=[r for r in rows if r['b'][5]==6 and r['direction']=='lens-to-body']
    walks=[records(r['b']) for r in f4]
    return dict(validatedFrames=len(rows),body04=len(f4),lens06=len(f6),body04Lengths=dict(sorted(collections.Counter(len(r['b']) for r in f4).items())),lens06Lengths=dict(sorted(collections.Counter(len(r['b']) for r in f6).items())),recordTags=dict(sorted(collections.Counter(f"0x{t:02x}" for tags,_ in walks for t in tags).items())),queryRecords=sum(t in (0x22,0x2e) for tags,_ in walks for t in tags),queryBatchHistogram=dict(sorted(collections.Counter(sum(t in (0x22,0x2e) for t in tags) for tags,ok in walks if ok).items())),unknownOrTruncatedRecordWalks=sum(not ok for _,ok in walks))
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
    spec=importlib.util.spec_from_file_location('sampler',ROOT/'references/scripts/analyze_captures.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    entropy=[]
    for path in sorted((ROOT/'references/upstream/Entropy512/sigrok-dumps/lens_mounts/sony_emount').glob('*.sr')):
        rr,meta=mod.analyze(path);rows=[]
        for r in rr:
            if r.get('error') or r.get('uart_framing_errors'):continue
            b=bytes.fromhex(r['hex'])
            if validated(b):rows.append(dict(b=b[:int.from_bytes(b[1:3],'little')],direction=r['direction'],sample=r['cs_start_sample']))
        s=summary(rows);s.update(capture=path.name,sha256=meta['sha256'],durationSeconds=meta['samples']/6e6,extraction=meta['counts'])
        for typ,direction in [(4,'body-to-lens'),(6,'lens-to-body')]:
            times=[r['sample']/6e6 for r in rows if r['b'][5]==typ and r['direction']==direction]
            gaps=[b-a for a,b in zip(times,times[1:])]
            s[f'{typ:02x}ObservedCadence']=dict(intervals=len(gaps),medianMilliseconds=statistics.median(gaps)*1000,minMilliseconds=min(gaps)*1000,maxMilliseconds=max(gaps)*1000)
        entropy.append(s)
    lex=[]
    for path in sorted((ROOT/'references/upstream/LexOptical/E-Mount-Traffic-Samples').glob('*.txt')):
        text=path.read_text();rows=[];rejected=0;repaired=0;missing_sync=0
        # Bound each candidate by a direction marker. Never silently stitch two messages.
        matches=list(re.finditer(r'(Body->Lens|Lens->Body)',text))
        for ix,m in enumerate(matches):
            block=text[m.end():matches[ix+1].start() if ix+1<len(matches) else len(text)]
            cleaned=re.sub(r'\[[A-Za-z]:\d+\]','',block)
            match=re.search(r'F0[0-9A-Fa-f\s]*',cleaned)
            if not match:missing_sync+=1;continue
            digits=re.sub(r'\s','',match.group())
            if len(digits)<6:rejected+=1;continue
            n=int.from_bytes(bytes.fromhex(digits[2:6]),'little')
            if n<9 or len(digits)<n*2:rejected+=1;continue
            b=bytes.fromhex(digits[:n*2])
            if not validated(b):rejected+=1;continue
            if '[' in block:repaired+=1
            rows.append(dict(b=b,direction='body-to-lens' if m.group()=='Body->Lens' else 'lens-to-body'))
        s=summary(rows);s.update(capture=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),directionBlocks=len(matches),rejectedCandidates=rejected,blocksWithoutSync=missing_sync,clockAnnotatedBlocksAccepted=repaired)
        lex.append(s)
    report=dict(method='Fresh independent UART extraction of five public .sr files; length/checksum/terminator validated direction-bounded LexOptical candidates with clock annotations removed and whitespace joined. No timestamp or byte repair; no text-trace rate claim.',entropy512=entropy,lexOptical=lex,limits=['No query workload bound follows from absence in finite public recordings.','Directionless LexOptical snippets excluded; corrupt/interrupted candidates excluded.','0x06 lengths vary by lens; no universal status tail offset inferred.','No A7C II or EA9 camera capture used; no factory bytes included.'],hardwareReportsSent=0)
    (out/'capture-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()

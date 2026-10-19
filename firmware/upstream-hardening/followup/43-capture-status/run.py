#!/usr/bin/env python3
"""Offline source-bound AF3.7 capture/status replay; no device interfaces."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
if not __debug__:raise RuntimeError('Assertions required')
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
CASES=['normal','second-status-cut','raw-failed','raw-vd','raw-readiness','raw-session','raw-shutdown','raw-queued-control','readiness-failed','readiness-session','readiness-shutdown']
def command(args,cwd=None):
    r=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True,timeout=40)
    assert r.returncode==0,(r.returncode,r.stderr)
    return r.stdout

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    p.add_argument('--candidate',type=Path,help='Optional complete private candidate build; baseline remains verified')
    a=p.parse_args()
    base=ROOT/'artifacts/private/targeted37-repeat';out=a.output.resolve()
    assert out.is_relative_to(ROOT/'artifacts/private')
    m=json.loads((ROOT/'firmware/candidates/3.7.0/contax-zeiss-50-f1-4.manifest.json').read_text())
    assert sha(base/'manifest.json')==sha(ROOT/'firmware/candidates/3.7.0/contax-zeiss-50-f1-4.manifest.json')
    assert sha(base/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']
    for name,h in m['sources'].items():assert sha(base/name)==h,name
    assert sha(base/'tools/hosttest/shim.c')==m['hostTestShimSHA256']
    pins={
      'references/upstream/weiziqian/E-mount-impl-on-Techart-EA9/src/emount.c':'eb4a24fd7b63fa53a92f534642e3284f3bc339c155d7e2bdbe5e9fb704bdca2e',
      'firmware/upstream-hardening/next37/trace_compat.c':'1b5109712de1be33a9d329260a04de102e661a45fdf54756feb03c0dab7f699e',
      'firmware/upstream-hardening/next37/packet_test_init.c':'21c84f5f6f62970e37f1398a0bc45f6474d9045a01f22efd1d7bf1293dbe27a9'}
    for name,digest in pins.items():assert sha(ROOT/name)==digest,name
    baseline,baseline_manifest=base,m
    if a.candidate:
        base=a.candidate.resolve()
        assert base.is_relative_to(ROOT/'artifacts/private')
        m=json.loads((base/'manifest.json').read_text())
        for name,h in m['sources'].items():assert sha(base/name)==h,name
        assert sha(base/'tools/hosttest/shim.c')==m['hostTestShimSHA256']
        assert sha(base/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']
    out.mkdir(exist_ok=False)
    shim=(base/'tools/hosttest/shim.c').read_text()
    old='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{'
    assert shim.count(old)==1
    shim=shim.replace(old,'void host_probe_send(const uint8_t *,uint16_t);\nextern int host_tx_fail;\n'+old+'\n if(host_tx_fail)return 0;\n host_probe_send(buf,len);')
    (out/'shim.c').write_text(shim)
    rows={}
    variants={'frozen':None,'resume-status-mutant':('g_owner.status_enabled = 0;\n                    g_status_due = 0;','g_owner.status_enabled = 1;\n                    g_status_due = 0;'),'lost-rearm-mutant':('if (sent && id == 0x0au && session == g_session_generation && !em_shutdown_requested())', 'if (sent && id == 0x0au && session == g_session_generation && !em_shutdown_requested() && !em_handshake_done)'),'stuck-retry-mutant':('if (sent || session != g_session_generation) g_retry = 0;','if (session != g_session_generation) g_retry = 0;')}
    for variant,edit in variants.items():
        work=out/variant;shutil.copytree(base/'src',work/'src');src=work/'src'
        source=(src/'emount.c').read_text()
        if edit:
            old,new=edit;assert source.count(old)==(2 if variant=='stuck-retry-mutant' else 1)
            source=source.replace(old,new,1)
        source+='\nunsigned test_status(void){return g_owner.status_enabled;}\nunsigned test_retry(void){return g_retry!=0;}\nunsigned test_pending(void){return g_owner.pending;}\nunsigned test_raw(void){return g_owner.slot[g_owner.active^1u].raw;}\n'
        (src/'emount.c').write_text(source)
        flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),'-I'+str(base/'tools/hosttest')]
        command([*flags,HERE/'test_replay.c',out/'shim.c',ROOT/'firmware/upstream-hardening/next37/trace_compat.c',ROOT/'firmware/upstream-hardening/next37/packet_test_init.c',*[src/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown']],'-o',work/'probe'])
        rows[variant]=[]
        for case in CASES if variant=='frozen' else ['normal']:
            r=subprocess.run([str(work/'probe'),case],capture_output=True,text=True,timeout=10)
            assert r.returncode==(0 if variant=='frozen' else 1),(variant,case,r.returncode,r.stderr)
            assert 'AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr
            rows[variant].append(json.loads(r.stdout) if not r.returncode else {'case':case,'rejected':True,'assertion':r.stderr.strip()})
    for name,h in m['sources'].items():assert sha(base/name)==h,name
    for name,h in baseline_manifest['sources'].items():assert sha(baseline/name)==h,name
    report={'baseline37ImageSHA256':baseline_manifest['imageSHA256'],'candidateReplay':bool(a.candidate),'status':'offline-no-production-fix-justified','sourceDigestsVerified':len(m['sources']),'baseImageSHA256':m['imageSHA256'],'sourceHashes':m['sources'],'pinnedDependencies':pins,'testSHA256':sha(HERE/'test_replay.c'),'runnerSHA256':sha(Path(__file__)),'testedManifestSHA256':sha(base/'manifest.json'),'cases':rows,'productionTextDelta':0,'productionRAMDelta':0,'hardwareAccess':False,'cameraAcceptanceClaimed':False}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    if not a.candidate:(HERE/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':len(rows['frozen']),'mutantsRejected':3,'productionChange':False}))
if __name__=='__main__':main()

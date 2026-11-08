#!/usr/bin/env python3
"""Feed native Swift migration/selection bytes into the unchanged compiled 4.8 runtime."""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('arm_port',ROOT/'scripts/test-profile-nvm-arm.py')
arm=importlib.util.module_from_spec(spec); spec.loader.exec_module(arm)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--build',type=Path,required=True)
    p.add_argument('--native-vectors',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); out=a.output.resolve(); assert out.is_relative_to(ROOT/'artifacts/private'); out.mkdir(exist_ok=False)
    values=json.loads(a.native_vectors.read_text()); bank=(a.build/'bank.bin').read_bytes()
    assert hashlib.sha256(bank).hexdigest()==values['bankSHA256']
    m=arm.Machine(a.build)
    m.u.mem_write(0x4000,base64.b64decode(values['initialMetadata']))
    m.u.mem_write(0x13000,base64.b64decode(values['initialJournal']))
    assert m.run('profile_runtime_init')==1 and not m.commands
    assert m.get(m.symbols['em_focal_mm10'],2)==500
    assert m.get(m.symbols['em_startup_aperture_av'],2)==4352
    m.u.mem_write(0x4000,base64.b64decode(values['selectionMetadata']))
    assert m.run('profile_runtime_init')==1
    assert m.commands==[2,0x46,0x44,4,0x46]
    assert m.get(m.symbols['em_focal_mm10'],2)==350
    assert bytes(m.u.mem_read(0x13100,64))==base64.b64decode(values['expectedConsumedSetting'])
    m.commands=[]
    assert m.run('profile_runtime_init')==1 and not m.commands
    report=dict(hardwareAccess=False,nativeVectorsSHA256=hashlib.sha256(a.native_vectors.read_bytes()).hexdigest(),
        initialMigration='native seed/mailbox applied 50mm f/1.4 with zero NVM commands',
        selection='native metadata request applied 35mm f/1.4 and produced the exact native-decoder canonical journal record',
        replay='unchanged request emitted zero NVM commands',
        scope='Actual compiled 4.8 startup and NVM code, synthetic CPU/register/page-buffer model; no camera or real flash qualification')
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Native Swift migration/selection vectors passed unchanged compiled ARM 4.8 runtime and journal round-trip.')


if __name__=='__main__': main()

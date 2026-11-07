#!/usr/bin/env python3
"""Create a private offline metadata-only selection proposal. Cannot transmit USB."""
import argparse
import hashlib
import json
from pathlib import Path
from profile_bank import plan_selection, validate_bank

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,required=True)
    p.add_argument('--metadata',type=Path,required=True,help='Private 58-byte metadata file, excluding scratch.')
    p.add_argument('--journal',type=Path,required=True,help='Private 4096-byte settings region.')
    p.add_argument('--profile-id',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        manifest=json.loads((a.package/'manifest.json').read_text())
        if manifest.get('format')!='offline-sparse-package' or manifest.get('transmissionEnabled') is not False:
            raise ValueError('Expected the offline sparse-package manifest.')
        expected={'application.bin':(0x5000,20480),'extension.bin':(0x10000,8192),
                  'bank.bin':(0x12000,4096),'settings.bin':(0x13000,4096)}
        if len(manifest['segments'])!=4 or {s['file'] for s in manifest['segments']}!=set(expected):
            raise ValueError('Unexpected segment set.')
        for s in manifest['segments']:
            data=(a.package/s['file']).read_bytes()
            if ((s['address'],s['bytes'])!=expected[s['file']] or len(data)!=s['bytes'] or
                hashlib.sha256(data).hexdigest()!=s['sha256']):
                raise ValueError('Package segment does not match its manifest.')
        bank=(a.package/'bank.bin').read_bytes()
        validate_bank(bank)
        identities=[bank[64+256*i+24:64+256*i+104].split(b'\0',1)[0].decode('ascii') for i in range(bank[14])]
        if manifest['profiles']!=identities:
            raise ValueError('Manifest profile order does not match the bank.')
        slot=manifest['profiles'].index(a.profile_id)
        proposal=plan_selection(bank,a.journal.read_bytes(),a.metadata.read_bytes(),slot)
        proposal.update(profileID=a.profile_id,packageVersion=manifest['version'],
                        bankSHA256=hashlib.sha256(bank).hexdigest())
        out=a.output.resolve()
        if not out.is_relative_to(ROOT/'artifacts/private'):
            raise ValueError('Selection proposals contain metadata; save below artifacts/private.')
        with out.open('x') as f: json.dump(proposal,f,indent=2); f.write('\n')
    except (ValueError,KeyError,TypeError,OSError) as error: p.error(str(error))
    print('Saved offline proposal. USB transmission is disabled.')


if __name__=='__main__': main()

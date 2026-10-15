"""Synthetic offline registry/backup boundary tests, plus real frozen 3.2 pin."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import shutil
import struct
import subprocess
import sys
import unittest
import zlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=Path(sys.argv.pop(1))
spec=importlib.util.spec_from_file_location('ext',HERE/'decoder_extension.py');ext=importlib.util.module_from_spec(spec);spec.loader.exec_module(ext)
legacy=runpy.run_path(str(ROOT/'scripts/decode-startup-diagnostics.py'))['decode_pages']
sha=lambda b:hashlib.sha256(b).hexdigest()
work=OUT/'decoder-repository';(work/'scripts').mkdir(parents=True)
shutil.copyfile(ROOT/'scripts/decode-startup-diagnostics.py',work/'scripts/decode-startup-diagnostics.py')
runpy.run_path(str(HERE/'apply_decoder.py'))['apply'](work)
shutil.copytree(ROOT/'firmware/candidates/3.2.0',work/'firmware/candidates/3.2.0')
path=work/'firmware/candidates/3.3.0/contax-zeiss-50-f1-4.bin';path.parent.mkdir()
# Synthetic-only 3.3: does not represent an executable or published candidate.
image=bytearray((work/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.bin').read_bytes());image[256]^=1;image=bytes(image)
path.write_bytes(image)
manifest={'loaderVersion':[3,3,0],'imageSHA256':sha(image),'diagnosticRange':[0x9c00,0xa000],'syntheticTestOnly':True}
path.with_suffix('.manifest.json').write_text(json.dumps(manifest))
pin={'imageSHA256':sha(image),'manifestSHA256':sha(path.with_suffix('.manifest.json').read_bytes()),'immutablePrefixSHA256':sha(image[:0x4c00])}
registry={'format':ext.REGISTRY_FORMAT,'versions':{'3.3.0':pin}}
regpath=work/'firmware/candidates/diagnostic-registry.json';regpath.write_text(json.dumps(registry))

def dump(version='3.3.0'):
    data=bytearray(b'\xff'*0x20000)
    data[0x4000:0x4003]=bytes(int(v) for v in version.split('.'))
    data[0x5000:0xa000]=(work/'firmware/candidates'/version/path.name).read_bytes()
    if version=='3.3.0':data[0x9c00:0xa000]=(OUT/'proposed-fixture.bin').read_bytes()
    return data

def cli(data):
    f=OUT/'synthetic-flash.bin';f.write_bytes(data)
    r=subprocess.run(['python3',str(work/'scripts/decode-startup-diagnostics.py'),str(f)],capture_output=True,text=True)
    return r

class Tests(unittest.TestCase):
    def tearDown(self):
        regpath.write_text(json.dumps(registry));path.write_bytes(image)
        path.with_suffix('.manifest.json').write_text(json.dumps(manifest))
    def test_frozen_parser_compatibility(self):
        data=(OUT/'frozen32-fixture.bin').read_bytes()
        before=legacy(data);after=ext.decode_extended_pages(data,legacy,'3.2.0')
        self.assertEqual(before['validPages'],after['validPages'])
        for a,b in zip(before['pages'],after['pages']):
            for k,v in a.items():self.assertEqual(v,b[k])
        r=cli(dump('3.2.0'));self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['firmwareVersion'],'3.2.0')
    def test_pinned_synthetic33_cli(self):
        r=cli(dump());self.assertEqual(r.returncode,0,r.stderr)
        d=json.loads(r.stdout);self.assertEqual(d['validPages'],13)
        s=next(p['summary'] for p in d['pages'] if p.get('type')=='summary')
        self.assertTrue(s['shutdownUARTDisabledObserved']);self.assertEqual(s['droppedEvents'],53)
        self.assertFalse(d['installationVerificationPerformed'])
    def test_v2_rejected_for_legacy(self):
        self.assertEqual(ext.decode_extended_pages((OUT/'proposed-fixture.bin').read_bytes(),legacy,'3.2.0')['validPages'],0)
    def test_summary_survives_later_torn_events(self):
        data=bytearray((OUT/'proposed-fixture.bin').read_bytes());data[64+20]^=1
        d=ext.decode_extended_pages(data,legacy,'3.3.0');s=d['pages'][0]['summary']
        self.assertEqual(s['plannedEvents'],48);self.assertEqual(s['persistedEvents'],44)
        self.assertFalse(s['eventSnapshotComplete']);self.assertTrue(s['shutdownUARTDisabledObserved'])
    def test_registry_required(self):
        regpath.unlink();self.assertNotEqual(cli(dump()).returncode,0)
    def test_each_pin_required(self):
        for key in pin:
            reg=copy.deepcopy(registry);del reg['versions']['3.3.0'][key];regpath.write_text(json.dumps(reg))
            self.assertNotEqual(cli(dump()).returncode,0,key)
    def test_wrong_independent_pins(self):
        for key in pin:
            reg=copy.deepcopy(registry);reg['versions']['3.3.0'][key]='0'*64;regpath.write_text(json.dumps(reg))
            self.assertNotEqual(cli(dump()).returncode,0,key)
    def test_manifest_mutation(self):
        m=copy.deepcopy(manifest);m['syntheticTestOnly']=False;path.with_suffix('.manifest.json').write_text(json.dumps(m))
        self.assertNotEqual(cli(dump()).returncode,0)
    def test_candidate_tail_mutation_even_with_matching_manifest(self):
        bad=bytearray(image);bad[-1]=0;path.write_bytes(bad)
        m=copy.deepcopy(manifest);m['imageSHA256']=sha(bad);path.with_suffix('.manifest.json').write_text(json.dumps(m))
        self.assertNotEqual(cli(dump()).returncode,0)
    def test_exact_prefix_and_version(self):
        for offset in (0x4000,0x5000,0x9bff):
            data=dump();data[offset]^=1;self.assertNotEqual(cli(data).returncode,0)
    def test_flash_size(self):
        for data in (dump()[:-1],dump()+b'\xff'):
            self.assertNotEqual(cli(data).returncode,0)
    def test_torn_and_structural_pages(self):
        original=(OUT/'proposed-fixture.bin').read_bytes()
        for pos in (0,4,8,20,60):
            data=bytearray(original);data[pos]^=1
            self.assertEqual(ext.decode_extended_pages(data,legacy,'3.3.0')['invalidPages'],1)
        # A CRC-correct v2 summary with impossible serialization count is invalid.
        data=bytearray(original);off=0;data[off+47]=49
        data[off+60:off+64]=struct.pack('<I',zlib.crc32(data[off:off+60]))
        self.assertEqual(ext.decode_extended_pages(data,legacy,'3.3.0')['pages'][0]['state'],'invalid-or-torn')
    def test_frontier_holes(self):
        data=bytearray(b'\xff'*1024);data[15*64]=0
        d=ext.decode_extended_pages(data,legacy,'3.3.0')
        self.assertEqual(d['erasedPages'],15);self.assertFalse(d['storageFull'])
        self.assertTrue(d['appendExhausted']);self.assertEqual(d['strandedErasedPages'],15)
    def test_native_backup_manifest(self):
        native=OUT/'synthetic.ea9backup';native.mkdir(exist_ok=True)
        data=dump();(native/'flash.bin').write_bytes(data)
        m={'flashReadPasses':2,'auxiliaryReadPasses':2,'files':{'flash.bin':{'bytes':len(data),'sha256':sha(data)}}}
        for valid in (True,False):
            if not valid:m['files']['flash.bin']['sha256']='0'*64
            (native/'manifest.json').write_text(json.dumps(m))
            r=subprocess.run(['python3',str(work/'scripts/decode-startup-diagnostics.py'),str(native)],capture_output=True,text=True)
            self.assertEqual(r.returncode==0,valid,r.stderr)

if __name__=='__main__':unittest.main()

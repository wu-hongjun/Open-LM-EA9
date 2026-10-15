"""Decoder corruption tests use only the synthetic C trace fixture."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('startup_decoder',ROOT/'scripts/decode-startup-diagnostics.py')
decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
fixture=Path(sys.argv.pop(1)).read_bytes()


class DecoderTests(unittest.TestCase):
    def test_c_fixture_recovers_handshake_and_ids(self):
        d=decoder.decode_pages(fixture)
        self.assertGreater(d['validPages'],0);self.assertEqual(d['invalidPages'],0)
        self.assertTrue(any(p.get('summary',{}).get('handshakeFlag') for p in d['pages']))
        self.assertTrue(any(e['kind']=='rx-frame' and e['sequence']==7
                            for p in d['pages'] for e in p.get('events',[])))

    def test_torn_record_retained_as_invalid(self):
        p=bytearray(fixture);p[20]^=1
        self.assertEqual(decoder.decode_pages(p)['invalidPages'],1)

    def test_bad_count_with_valid_crc_rejected(self):
        p=bytearray(fixture);p[7]=255;p[60:64]=struct.pack('<I',zlib.crc32(p[:60]))
        self.assertEqual(decoder.decode_pages(p)['pages'][0]['state'],'invalid-or-torn')

    def test_wrong_slot_with_valid_crc_rejected(self):
        p=bytearray(fixture);p[8]=15;p[60:64]=struct.pack('<I',zlib.crc32(p[:60]))
        self.assertEqual(decoder.decode_pages(p)['pages'][0]['state'],'invalid-or-torn')

    def test_real_ff_capability_is_distinct_from_missing_value(self):
        p=bytearray(fixture)
        index=next(i for i in range(16) if p[64*i+5]==1)
        start=64*index;p[start+12+28]=255;p[start+12+32]=1
        p[start+60:start+64]=struct.pack('<I',zlib.crc32(p[start:start+60]))
        summary=decoder.decode_pages(p)['pages'][index]['summary']
        self.assertEqual(summary['message08CapabilityByte'],255)
        p[start+12+32]=0;p[start+60:start+64]=struct.pack('<I',zlib.crc32(p[start:start+60]))
        self.assertIsNone(decoder.decode_pages(p)['pages'][index]['summary']['message08CapabilityByte'])

    def test_erased_and_full_logs_are_distinct(self):
        d=decoder.decode_pages(b'\xff'*1024)
        self.assertEqual(d['erasedPages'],16);self.assertFalse(d['storageFull'])
        d=decoder.decode_pages(b'\0'*1024)
        self.assertEqual(d['invalidPages'],16);self.assertTrue(d['storageFull'])

    def test_truncated_or_oversized_region_rejected(self):
        for n in (0,1023,1025):
            with self.assertRaises(ValueError):decoder.decode_pages(b'\xff'*n)


if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Offline recovery acceptance/failure checks; requires the private archive key."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import warnings
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import recover_stock_backup as recovery

KEY_PATH = None


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='ea9-recovery-test-')
        self.root = Path(self.scratch.name)
        self.bundle = self.root / 'bundle'
        shutil.copytree(recovery.DEFAULT_BUNDLE, self.bundle)
        self.output = self.root / 'restored.ea9backup'
        self.key = KEY_PATH.read_bytes()

    def tearDown(self):
        self.scratch.cleanup()

    def update_ciphertext(self, sealed, archive=None):
        (self.bundle / 'original-unit-backup.aesgcm').write_bytes(sealed)
        manifest_path = self.bundle / 'recovery.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['files']['original-unit-backup.aesgcm'] = {'bytes': len(sealed), 'sha256': recovery.digest(sealed)}
        if archive is not None:
            manifest['archiveSHA256'] = recovery.digest(archive)
        manifest_path.write_text(json.dumps(manifest))

    def seal_malformed_archive(self, names):
        buffer = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(buffer, 'w') as package:
                for name in names:
                    package.writestr(name, b'x')
        archive = buffer.getvalue()
        nonce = bytes(range(12))
        self.update_ciphertext(recovery.MAGIC + nonce + AESGCM(self.key).encrypt(nonce, archive, recovery.AAD), archive)

    def test_committed_products_match_pins(self):
        manifest = recovery.verify_bundle(self.bundle)
        self.assertEqual(manifest['stockLoaderVersion'], '1.8.0')
        self.assertFalse(manifest['keyCommitted'])

    def test_original_backup_round_trip_and_private_permissions(self):
        result = recovery.unpack(self.bundle, KEY_PATH, self.output)
        self.assertEqual(result['flash_sha256'], recovery.FLASH_SHA256)
        self.assertEqual({p.name for p in self.output.iterdir()}, set(recovery.EXPECTED))
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        for path in self.output.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_wrong_key_publishes_nothing(self):
        wrong = self.root / 'wrong.key'; wrong.write_bytes(bytes(x ^ 0xff for x in self.key))
        with self.assertRaisesRegex(ValueError, 'authentication failed'):
            recovery.unpack(self.bundle, wrong, self.output)
        self.assertFalse(self.output.exists())

    def test_authenticated_tampering_publishes_nothing(self):
        sealed = bytearray((self.bundle / 'original-unit-backup.aesgcm').read_bytes())
        sealed[-1] ^= 1
        self.update_ciphertext(bytes(sealed))
        with self.assertRaisesRegex(ValueError, 'authentication failed'):
            recovery.unpack(self.bundle, KEY_PATH, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_destination_is_preserved(self):
        self.output.mkdir(); sentinel = self.output / 'sentinel'; sentinel.write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError, 'new output directory'):
            recovery.unpack(self.bundle, KEY_PATH, self.output)
        self.assertEqual(sentinel.read_bytes(), b'preserve')

    def test_path_traversal_is_rejected_before_publication(self):
        self.seal_malformed_archive(['../outside'])
        with self.assertRaisesRegex(ValueError, 'archive entries'):
            recovery.unpack(self.bundle, KEY_PATH, self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse((self.root / 'outside').exists())

    def test_duplicate_entries_are_rejected_before_publication(self):
        self.seal_malformed_archive(list(recovery.EXPECTED) + ['flash.bin'])
        with self.assertRaisesRegex(ValueError, 'archive entries'):
            recovery.unpack(self.bundle, KEY_PATH, self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key', type=Path, required=True)
    KEY_PATH = parser.parse_args().key
    unittest.main(argv=[__file__], verbosity=2)

#!/usr/bin/env python3
"""Verify committed stock recovery files or unpack the encrypted unit backup offline.

Never opens USB. The separately held 32-byte key is needed only for unpacking.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from verify_macos_backup import verify as verify_backup

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / 'firmware/recovery/stock-1.8.0'
APPLICATION_SHA256 = 'f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564'
FLASH_SHA256 = '1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01'
MAGIC = b'EA9REC01'
AAD = b'Open-LM-EA9 original stock backup v1\0' + bytes.fromhex(FLASH_SHA256)
EXPECTED = {'flash.bin': 131072, 'user-row.bin': 64, 'calibration.bin': 64,
            'device-id.bin': 64, 'nvm-status.bin': 64, 'manifest.json': None}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_bundle(bundle):
    manifest = json.loads((bundle / 'recovery.json').read_text())
    require(manifest['schemaVersion'] == 1 and manifest['stockLoaderVersion'] == '1.8.0', 'Unsupported recovery bundle')
    require(set(manifest['files']) == {'application.bin', 'original-unit-backup.aesgcm'}, 'Unexpected recovery files')
    for name, record in manifest['files'].items():
        path = bundle / name
        require(path.is_file() and not path.is_symlink(), 'Recovery input must be a regular file')
        require(path.stat().st_size == record['bytes'] and path.stat().st_size < 262144, 'Recovery file size mismatch')
        require(digest(path.read_bytes()) == record['sha256'], 'Recovery file checksum mismatch')
    application = (bundle / 'application.bin').read_bytes()
    require(len(application) == 20172 and digest(application) == APPLICATION_SHA256, 'Unrecognized original stock application')
    require(manifest['originalFullFlashSHA256'] == FLASH_SHA256, 'Unrecognized original flash snapshot')
    sealed = (bundle / 'original-unit-backup.aesgcm').read_bytes()
    require(sealed[:8] == MAGIC and len(sealed) >= 36, 'Invalid encrypted archive header')
    require(manifest['encryption'] == 'AES-256-GCM' and manifest['keyBytes'] == 32, 'Unsupported encryption format')
    return manifest


def verify_original_backup(folder):
    result = verify_backup(folder)
    manifest = json.loads((folder / 'manifest.json').read_text())
    flash = (folder / 'flash.bin').read_bytes()
    require(result['flash_sha256'] == FLASH_SHA256, 'Decrypted flash differs from original snapshot')
    require(manifest['reportedFirmwareVersion'] == '1.8.0' and flash[0x4000:0x4003] == bytes([1,8,0]), 'Decrypted backup version mismatch')
    require(manifest['device']['qualifiedDescriptor'] and bool(manifest['device']['serial']), 'Decrypted same-unit identity is missing')
    require(digest(flash[0x5000:0x5000+20172]) == APPLICATION_SHA256, 'Decrypted stock application mismatch')
    return result


def unpack(bundle, key_path, output):
    manifest = verify_bundle(bundle)
    require(not output.exists() and not output.is_symlink(), 'Choose a new output directory; existing data is preserved')
    key = key_path.read_bytes()
    require(len(key) == 32, 'Recovery key must contain exactly 32 raw bytes')
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as error:
        raise ValueError('Install tools/recovery-requirements.txt in a virtual environment before unpacking') from error
    sealed = (bundle / 'original-unit-backup.aesgcm').read_bytes()
    try:
        archive = AESGCM(key).decrypt(sealed[8:20], sealed[20:], AAD)
    except Exception as error:
        raise ValueError('Encrypted backup authentication failed; no output was published') from error
    require(len(archive) <= 196608 and digest(archive) == manifest['archiveSHA256'], 'Decrypted archive checksum/size mismatch')
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        entries = package.infolist()
        require(len(entries) == len(EXPECTED) and {x.filename for x in entries} == set(EXPECTED), 'Unexpected or duplicate archive entries')
        data = {}
        for entry in entries:
            size = EXPECTED[entry.filename]
            require(not entry.is_dir() and (entry.external_attr >> 16) & 0o170000 != 0o120000, 'Invalid archive entry type')
            require(entry.file_size == size if size is not None else 0 < entry.file_size <= 65536, 'Invalid archive entry size')
            data[entry.filename] = package.read(entry)
    require(output.parent.is_dir(), 'Output parent directory must already exist')
    with tempfile.TemporaryDirectory(prefix='.ea9-recovery-', dir=output.parent) as name:
        temporary = Path(name)
        temporary.chmod(0o700)
        for filename, contents in data.items():
            file = temporary / filename
            descriptor = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(contents); stream.flush(); os.fsync(stream.fileno())
        result = verify_original_backup(temporary)
        # mkdir is exclusive: never replace a destination created by another process.
        output.mkdir(mode=0o700)
        try:
            for filename in EXPECTED:
                shutil.move(str(temporary / filename), output / filename)
        except Exception:
            # Preserve partially published evidence; never overwrite or retry it.
            raise
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=DEFAULT_BUNDLE)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('verify')
    extract = commands.add_parser('unpack')
    extract.add_argument('--key', type=Path, required=True)
    extract.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'verify':
            verify_bundle(args.bundle)
            result = {'valid': True, 'stockLoaderVersion': '1.8.0', 'applicationSHA256': APPLICATION_SHA256,
                      'encryptedBackupChecksumValid': True, 'archiveDecrypted': False, 'usbReportsSent': 0}
        else:
            result = unpack(args.bundle, args.key, args.output)
            result.update(stockLoaderVersion='1.8.0', archiveDecrypted=True, usbReportsSent=0)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Recovery verification failed: {error}\n')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()

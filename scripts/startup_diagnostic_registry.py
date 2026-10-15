"""Offline v2 parser and strict published-candidate resolution.

The registry must pin the complete pristine image, complete published manifest,
and immutable prefix independently. Nothing here verifies an installed image:
only the diagnostic read permits the append-only log tail to differ.
"""
import hashlib
import json
from pathlib import Path
import zlib

FROZEN32 = 'e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df'
REGISTRY_FORMAT = 'EA9 diagnostic candidate pins v1'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def bounded_json(path):
    if path.stat().st_size > 65536:
        raise ValueError('Manifest/registry exceeds 64 KiB.')
    return json.loads(path.read_text())

def resolve_candidate(root, version):
    if version not in ('3.2.0', '3.3.0', '3.4.0'):
        raise ValueError('Unsupported diagnostic firmware version.')
    path = root/'firmware/candidates'/version/'contax-zeiss-50-f1-4.bin'
    descriptor = bounded_json(path.with_suffix('.manifest.json'))
    expected = path.read_bytes()
    if version == '3.2.0':
        # Fixed legacy image pin, independent of any mutable registry/manifest.
        pin = {'imageSHA256': FROZEN32, 'immutablePrefixSHA256': sha(expected[:0x4c00])}
    else:
        registry = bounded_json(root/'firmware/candidates/diagnostic-registry.json')
        if registry['format'] != REGISTRY_FORMAT:
            raise ValueError('Unsupported diagnostic registry.')
        pin = registry['versions'][version]
        if pin['manifestSHA256'] != sha(path.with_suffix('.manifest.json').read_bytes()):
            raise ValueError('Published candidate manifest pin mismatch.')
        if descriptor.get('diagnosticRange') != [0x9c00, 0xa000]:
            raise ValueError('Unexpected diagnostic range.')
    if (len(expected) != 0x5000 or expected[0x4c00:] != b'\xff'*1024
        or descriptor['loaderVersion'] != [int(v) for v in version.split('.')]
        or descriptor['imageSHA256'] != pin['imageSHA256']
        or sha(expected) != pin['imageSHA256']
        or sha(expected[:0x4c00]) != pin['immutablePrefixSHA256']):
        raise ValueError('Pristine candidate full-image/prefix pins do not match.')
    return expected, pin

def decode_extended_pages(data, decode_v1, version):
    if len(data) != 1024:
        raise ValueError('Expected exactly 1024 diagnostic bytes.')
    translated = bytearray(data)
    for index in range(16):
        p = data[index*64:(index+1)*64]
        if p[4] == 2 and version in ('3.3.0', '3.4.0'):
            # Verify original CRC before adapting the stable legacy fields.
            if zlib.crc32(p[:60]) != int.from_bytes(p[60:64], 'little'):
                continue
            if p[5] == 1 and (p[45] != 1 or p[46] > 48 or p[47] > p[46] or p[48] > 1):
                continue
            start = 64*index
            translated[start+4] = 1
            translated[start+60:start+64] = zlib.crc32(translated[start:start+60]).to_bytes(4, 'little')
    result = decode_v1(translated)
    for entry in result['pages']:
        if entry['state'] != 'valid':
            continue
        p = data[64*entry['slot']:64*(entry['slot']+1)]
        entry['recordVersion'] = p[4]
        if p[4] == 2 and entry['type'] == 'summary':
            entry['summary'].update({
                'retention': 'first-24-and-last-24',
                'bufferedEvents': p[46], 'plannedEvents': p[47],
                'shutdownUARTDisabledObserved': bool(p[48]),
                'droppedEventsMeaning': 'Saturating RAM evictions plus budget omissions. Additional torn/missing event pages are reported separately; not a wire traffic count.',
            })
            summary=entry['summary']
            summary['observedMessage08CapabilityByte']=summary.pop('message08CapabilityByte')
            summary['capabilityMeaning']='Last complete message08 payload observed; not proof of committed negotiation.'
            fault=int.from_bytes(p[14:16], 'little')
            reasons={10:'uart-rx-drain-fault',11:'home-failed',12:'motor-poll-budget',13:'servo-poll-budget',14:'servo-runaway',15:'servo-wrong-way',16:'encoder-overflow'}
            if fault in reasons:summary['fault']=reasons[fault]
            if fault==16 and version=='3.4.0':summary['fault']='encoder-coordinate-capacity'
            summary['persistedEvents']=sum(len(e.get('events', [])) for e in result['pages'] if e.get('boot')==entry['boot'] and e['slot']>entry['slot'])
            summary['eventSnapshotComplete']=summary['persistedEvents']==summary['plannedEvents']
        if p[4]==2:
            for event in entry.get('events', []):
                if event['kind']=='unknown-10':event['kind']='observed-capability-byte'
    occupied = [p['slot'] for p in result['pages'] if p['state'] != 'erased']
    frontier = max(occupied, default=-1)+1
    result.update({
        'format': 'EA9 startup trace v1/v2' if version in ('3.3.0', '3.4.0') else 'EA9 startup trace v1',
        'appendFrontierSlot': frontier,
        'appendablePages': 16-frontier,
        'strandedErasedPages': sum(p['state'] == 'erased' and p['slot'] < frontier for p in result['pages']),
        'appendExhausted': frontier == 16,
        'bootMeaning': 'Append starting slot plus one; not a physical boot counter.',
        'missingRecordsMeaning': 'No persisted record does not prove no boot, capture, fault or shutdown. RAM is lost on battery removal; full storage, failed/torn programming and power loss can omit records.',
    })
    return result

def main(root, decode_v1):
    import argparse
    parser = argparse.ArgumentParser(description='Decode pinned 3.2/3.3/3.4 diagnostics offline; no device access.')
    parser.add_argument('backup', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = args.backup
    manifest = None
    if source.is_dir():
        manifest = bounded_json(source/'manifest.json')
        source = source/'flash.bin'
    if source.stat().st_size != 0x20000:
        raise ValueError('Expected exactly 128 KiB flash.bin.')
    data = source.read_bytes()
    if len(data) != 0x20000:
        raise ValueError('Expected exactly 128 KiB flash.bin.')
    version = '.'.join(str(v) for v in data[0x4000:0x4003])
    expected, pin = resolve_candidate(root, version)
    if data[0x5000:0x9c00] != expected[:0x4c00]:
        raise ValueError('Immutable diagnostic firmware prefix does not match the pinned candidate.')
    if manifest is not None:
        file = manifest['files']['flash.bin']
        if (manifest['flashReadPasses'] != 2 or manifest['auxiliaryReadPasses'] != 2
            or file['bytes'] != len(data) or file['sha256'] != sha(data)):
            raise ValueError('Native flash backup manifest does not match.')
    result = decode_extended_pages(data[0x9c00:0xa000], decode_v1, version)
    result.update({'immutableCodePrefixMatches': True, 'firmwareVersion': version,
                   'candidateImageSHA256': pin['imageSHA256'],
                   'immutablePrefixSHA256': pin['immutablePrefixSHA256'],
                   'flashSHA256': sha(data), 'backupFlashManifestMatched': manifest is not None,
                   'installationVerificationPerformed': False,
                   'cameraAcceptanceProven': False, 'hardwareReportsSent': 0})
    encoded = json.dumps(result, indent=2)+'\n'
    if args.output:
        with args.output.open('x') as handle:
            handle.write(encoded)
    else:
        print(encoded, end='')

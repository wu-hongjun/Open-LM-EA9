"""Offline profile-bank codec and metadata-mailbox planner. No device transport."""
import math
import struct
import zlib

BANK_ADDRESS, JOURNAL_ADDRESS = 0x12000, 0x13000
BANK_BYTES, JOURNAL_BYTES = 4096, 4096


def crc(data):
    return zlib.crc32(data) & 0xffffffff


def av(number):
    if type(number) not in (int, float) or not math.isfinite(number) or number <= 0:
        raise ValueError('Aperture must be a finite positive number.')
    return 4096 + round(16 * math.log2(number)) * 32


def record(lens, focal):
    nominal = av(lens.get('nominal_maximum_aperture', lens.get('reported_nominal_maximum_aperture')))
    name, identity = lens['display_name'].encode('ascii'), lens['id'].encode('ascii')
    if not (0 < len(name) < 64 and 0 < len(identity) < 80 and 10 <= focal <= 10000 and
            4224 <= nominal <= 6400):
        raise ValueError('Lens cannot be represented safely: ' + lens['id'])
    data = bytearray(256)
    struct.pack_into('<8s6HI', data, 0, b'EA9LENS1', 1, 256, focal, nominal, nominal, 234, 1)
    data[24:104], data[104:168] = identity.ljust(80, b'\0'), name.ljust(64, b'\0')
    struct.pack_into('<I', data, 252, crc(data[:252]))
    return bytes(data)


def make_bank(inventory, default='zeiss-jena-biotar-55-f2'):
    records, included, omitted = [], [], []
    for lens in inventory['lenses']:
        focal = lens.get('focal_length_mm', lens.get('active_focal_length_mm'))
        if focal is None:
            omitted.append(dict(profileID=lens['id'], reason='Choose the actual zoom focal length first.'))
            continue
        if type(focal) not in (int,float) or not math.isfinite(focal) or not 1 <= focal <= 1000:
            raise ValueError('Focal length must be 1–1000mm: ' + lens['id'])
        records.append(record(lens, round(focal * 10)))
        included.append(lens['id'])
    if not 1 <= len(records) <= 15 or len(set(included)) != len(included):
        raise ValueError('Bank requires 1–15 unique profiles.')
    payload = b''.join(records).ljust(BANK_BYTES - 64, b'\xff')
    header = bytearray(64)
    struct.pack_into('<8s3H2B2I', header, 0, b'OLABANK1', 1, 64, 256, len(records),
                     included.index(default), BANK_BYTES, crc(payload))
    struct.pack_into('<I', header, 60, crc(header[:60]))
    return bytes(header) + payload, included, omitted


def fingerprint(bank):
    validate_bank(bank)
    return struct.unpack_from('<I', bank, 20)[0]


def validate_bank(b):
    if len(b) != 4096 or b[:8] != b'OLABANK1':
        raise ValueError('Invalid bank length/magic.')
    if (struct.unpack_from('<3H', b, 8) != (1, 64, 256) or not 1 <= b[14] <= 15 or
        b[15] >= b[14] or struct.unpack_from('<I', b, 16)[0] != 4096 or b[24:60] != bytes(36) or
        crc(b[:60]) != struct.unpack_from('<I', b, 60)[0] or
        crc(b[64:]) != struct.unpack_from('<I', b, 20)[0]):
        raise ValueError('Invalid bank header/checksum.')
    identities = set()
    for i in range(b[14]):
        r = b[64+256*i:320+256*i]
        focal, nominal, boot, marker, revision = struct.unpack_from('<4HI', r, 12)
        def text(field):
            head, separator, tail = field.partition(b'\0')
            if not head or not separator or any(tail) or any(x < 32 or x > 126 for x in head):
                raise ValueError('Invalid profile text.')
            return head
        identity = text(r[24:104]); text(r[104:168])
        if (r[:8] != b'EA9LENS1' or struct.unpack_from('<2H', r, 8) != (1, 256) or
            not 10 <= focal <= 10000 or not 4096 <= nominal <= 6400 or nominal % 32 or
            not max(4224, nominal) <= boot <= 6400 or boot % 32 or marker != 234 or
            not 1 <= revision <= 1000000 or r[168:252] != bytes(84) or
            crc(r[:252]) != struct.unpack_from('<I', r, 252)[0] or identity in identities):
            raise ValueError('Invalid or duplicate lens record.')
        identities.add(identity)
    if b[64+256*b[14]:] != b'\xff' * (4032-256*b[14]):
        raise ValueError('Noncanonical bank padding.')


def setting(bank, slot, sequence=1, generation=0):
    if not 0 <= slot < bank[14] or not 1 <= sequence <= 0xffffffff or not 0 <= generation <= 0xffffffff:
        raise ValueError('Invalid setting.')
    b = bytearray(64)
    struct.pack_into('<8s2H3IB', b, 0, b'OLASET1!', 1, 64, fingerprint(bank), sequence, generation, slot)
    struct.pack_into('<I4s', b, 56, crc(b[:56]), b'DONE')
    return bytes(b)


def load_setting(bank, journal):
    if len(journal) != JOURNAL_BYTES:
        raise ValueError('Invalid journal length.')
    candidates = []
    for i in range(16):
        p = journal[i*256:i*256+64]
        seq, gen, slot = struct.unpack_from('<2IB', p, 16)
        if not seq or slot >= bank[14]:
            continue
        if p == setting(bank, slot, seq, gen):
            candidates.append((seq, gen, slot, i, p))
    if not candidates:
        raise ValueError('No committed setting; refuse implicit initialization.')
    newest = max(candidates)
    if any(p[0] == newest[0] and p[4] != newest[4] for p in candidates):
        raise ValueError('Conflicting committed settings.')
    return dict(sequence=newest[0], generation=newest[1], slot=newest[2], row=newest[3])


def mailbox(bank, slot, generation):
    if not 0 <= slot < bank[14] or not 1 <= generation <= 0xffffffff:
        raise ValueError('Invalid request; sequence exhaustion requires an explicit migration.')
    m = bytearray(26)
    struct.pack_into('<4sBBH3I', m, 0, b'OLAC', 1, slot, 0, fingerprint(bank), generation, 0)
    struct.pack_into('<I2s', m, 20, crc(m[:20]), b'OK')
    return bytes(m)


def decode_mailbox(bank, metadata):
    if len(metadata) != 58:
        raise ValueError('Exactly 58 owned metadata bytes are required; scratch is excluded.')
    m = metadata[32:58]
    if m == bytes(26) or m == b'\xff'*26:
        return None
    gen = struct.unpack_from('<I', m, 12)[0]
    if m[5] >= bank[14] or not gen or m != mailbox(bank, m[5], gen):
        raise ValueError('Foreign/invalid metadata extension; do not overwrite it.')
    return dict(slot=m[5], generation=gen)


def plan_selection(bank, journal, metadata, slot):
    """A proposal only: never sends START. Bank identity is checked by the caller's pin.

    The effective configured slot includes a request waiting for camera-side boot;
    selecting the old active slot must cancel that request with a newer generation.
    """
    validate_bank(bank)
    if not 0 <= slot < bank[14]:
        raise ValueError('Profile is outside this bank.')
    active, pending = load_setting(bank, journal), decode_mailbox(bank, metadata)
    effective = pending if pending and pending['generation'] > active['generation'] else active
    if effective['slot'] == slot:
        return dict(transmissionEnabled=False, needsWrite=False, active=active,
                    configuredSlot=slot, pendingApplication=effective is not active)
    generation = max(active['generation'], pending['generation'] if pending else 0) + 1
    proposed = metadata[:32] + mailbox(bank, slot, generation)
    return dict(transmissionEnabled=False, needsWrite=True, active=active, configuredSlot=slot,
                pendingApplication=True, proposedMetadataHex=proposed.hex(),
                requiredNextAction='Qualification required; no transport is implemented.',
                constraints=['one START, zero application pages', 'no retry or further reports',
                             'physical reconnect before full-flash invariance verification',
                             'application applies and journals the request on camera power-on'])

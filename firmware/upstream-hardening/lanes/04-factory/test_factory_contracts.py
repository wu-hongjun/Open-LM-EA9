#!/usr/bin/env python3
"""Bounded original-instruction evidence; synthetic RAM, no device APIs.

Requires research/stock-1.8/requirements.txt. Never writes the vendor image.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

if not __debug__:
    raise RuntimeError('Optimized Python disables assertions; refusing output')
ROOT = Path(__file__).resolve().parents[4]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
sys.path.insert(0, str(ROOT / 'research/stock-1.8'))
from config import configure, FIRMWARE_SHA256
cfg = configure(output=args.output)
from oracle import Machine
BASE, RX = 0x20000000, 0x20000694

def frame(ident=0x34, sequence=0x71):
    b = bytearray([0xf0, 11, 0, 2, sequence, ident, 0, 0x11, 0, 0, 0x55])
    b[-3:-1] = sum(b[1:-3]).to_bytes(2, 'little')
    return bytes(b)

def machine():
    sent, scheduled = [], []
    def send(m):
        a = m.calls[-1]['args']
        sent.append(bytes(m.u.mem_read(a[0], a[1])))
        return 0
    def schedule(m):
        a = m.calls[-1]['args']
        scheduled.append(a[:2])
        return 0
    cuts = {a: 0 for a in [0x91c4, 0x91ac, 0x51c8, 0x66cc, 0x66da,
                           0x66fc, 0x70d0, 0x7a70, 0x6a38, 0x6918, 0x69b0,
                           0x8e88, 0x8ed8, 0x8f28, 0x8f78]}
    cuts.update({0x9180: send, 0x609c: schedule, 0x89a4: lambda m: 5000})
    m = Machine(cuts)
    m.u.mem_map(0x41004000, 0x1000)
    m.u.mem_map(0x60000000, 0x1000)
    m.u.mem_write(BASE, bytes(0x800))
    m.set(BASE + 0x660, BASE)
    m.set(BASE + 0x678, BASE + 0x1a8)
    for off, value in [(0x522, 1), (0x51f, 4), (0x51c, 1), (0x52a, 1), (0x654, 105), (0x655, 50)]:
        m.set(BASE + off, value, 1)
    m.sent, m.scheduled = sent, scheduled
    return m

def cs(m, high):
    m.set(0x41004420, 4 if high else 0)
    m.run(0x53a4, 4 if high else 0)

def receive(m, b):
    cs(m, True)
    m.u.mem_write(RX, b)
    cs(m, False)

rows = []
# Explicit phase/gate controls; mode4 itself is caller supplied.
for phase in [0, 2, 3, 5, 6, 9, 12, 13]:
    for ident in [0x0a, 0x34]:
        for enabled in [0, 1]:
            m = machine()
            m.set(BASE + 0x520, phase, 1)
            m.set(BASE + 0x522, enabled, 1)
            receive(m, frame(ident))
            interlock = m.get(BASE + 0x51e, 1)
            expect = bool(enabled and (ident == 0x0a or phase in [2, 3, 5, 12, 13]))
            assert bool(interlock) == expect, (phase, ident, enabled, interlock)
            m.run(0x5120)
            assert (m.get(BASE + 0x51f, 1) == 5) == expect
            rows.append({'phase': phase, 'id': ident, 'callbacksEnabled': enabled,
                         'mode5': expect})
# Connected conditional path reaches 2/3/5/6 from phase0 with explicit callbacks.
m = machine()
m.set(BASE + 0x51c, 0, 1)
for _ in range(2):
    receive(m, frame())
assert m.get(BASE + 0x520, 1) == 12
m.run(0x5120)
assert m.get(BASE + 0x520, 1) == 13
m.run(0x5238)
assert m.get(BASE + 0x520, 1) == 2
m.run(0x5280)
assert m.get(BASE + 0x520, 1) == 3
m.run(0x54d8)
assert m.get(BASE + 0x520, 1) == 5
m.run(0x5280)
assert m.get(BASE + 0x520, 1) == 6

# New bounded dependency: the scheduled capture echo reads live RX at callback.
echoes = []
for replace in [False, True]:
    m = machine()
    m.set(BASE + 0x520, 3, 1)
    first, second = frame(0x34, 0x71), frame(0x19, 0x88)
    receive(m, first)
    m.run(0x5120)
    assert m.scheduled == [[10, 0x5261]]
    assert not m.sent
    if replace:
        # Supplied memory change, deliberately no claim a DMA race is reachable.
        m.u.mem_write(RX, second)
    m.run(0x5260)
    assert m.sent == [second if replace else first]
    echoes.append({'rxChangedBeforeCallback': replace,
                   'sentOriginalSnapshot': m.sent[0] == first,
                   'sentCurrentReceiveBuffer': m.sent[0] == (second if replace else first)})
    m.run(0x5188)
    m.run(0x5280)
    assert m.get(BASE + 0x51f, 1) == 1
    assert m.scheduled == [[10, 0x5261], [100, 0x5281]]
assert echoes[1]['sentOriginalSnapshot'] is False # wrong immutable-factory model rejected
# Formatter normalizes malformed checksum/terminator at this cut; not RX admission.
m = machine()
b = bytearray(frame())
b[-3:] = b'\x00\x00\x00'
m.u.mem_write(RX, bytes(b))
m.run(0x5260)
assert m.sent == [frame()] and m.sent[0] != bytes(b)

# Shutdown request dispatch requires mode1 + class2 and restarts state0 on repeats.
shutdown = []
for mode in [1, 4, 5]:
    for klass in [0, 2]:
        m = machine()
        m.set(BASE + 0x51f, mode, 1)
        m.u.mem_write(RX, frame(0x16))
        m.set(BASE + 0x697, klass, 1)
        m.set(BASE + 0x52d, 2, 1)
        m.run(0x58a4)
        accepted = mode == 1 and klass == 2
        assert bool(m.get(BASE + 0x52c, 1)) == accepted
        assert m.get(BASE + 0x52d, 1) == (0 if accepted else 2)
        shutdown.append({'mode': mode, 'class': klass, 'requestLatched': accepted})
# Ordinary dispatch retains template sequence; seq+1 only affects status pointers.
ordinary = []
for mode, phase in [(1, 0), (4, 0), (4, 6)]:
    for sequence in [0, 0x71, 0xff]:
        m = machine()
        m.set(BASE + 0x51f, mode, 1)
        m.set(BASE + 0x520, phase, 1)
        m.set(BASE + 0x30c, 0xa5, 1) # supplied ID34 template sequence
        receive(m, frame(0x34, sequence))
        m.run(0x58a4)
        assert len(m.sent) == (1 if mode == 1 else 0)
        if m.sent:
            assert m.sent[0][4] == 0xa5
        ordinary.append({'mode':mode, 'phase':phase, 'requestSequence':sequence,
                         'sent':bool(m.sent), 'replySequence':m.sent[0][4] if m.sent else None})

# State0 optional active park, state1 requires completion even with park disabled.
park = []
for option in [0, 1]:
    for completion in [0, 1]:
        m = machine()
        for off, value, width in [(0x52c, 1, 1), (0x52d, 0, 1),
                                  (0x4bc, option, 1), (0x4b8, completion, 1),
                                  (0x49c, 4800, 2), (0xd, 4144, 2)]:
            m.set(BASE + off, value, width)
        m.run(0x5e00)
        assert m.get(BASE + 0x52d, 1) == 1
        assert m.get(BASE + 0x4b1, 1) == option
        assert m.get(BASE + 0x49c, 2) == 4800
        if option:
            assert m.get(BASE + 0x4a8, 2) == 192
        m.run(0x5e00)
        expect = 2 if completion and not option else 1
        assert m.get(BASE + 0x52d, 1) == expect
        park.append({'parkOption': option, 'initialCompletion': completion,
                     'armedAfterState0': option, 'stateAfterTwoPolls': expect})
# The apparent READY completion may originate from the timeout, not sensing.
m = machine()
m.set(BASE + 0x4b1, 1, 1)
m.set(BASE + 0x4b4, 300, 2)
m.run(0x8a2c)
assert m.get(BASE + 0x4b8, 1) == 1 and m.get(BASE + 0x4b1, 1) == 0

origins = []
for sample, reference, expected in [(5000,4800,4146), (100,16000,4216),
                                     (16000,100,4216), (8191,8192,8191)]:
    m = machine()
    m.stubs[0x89a4] = lambda _m, s=sample: s
    m.set(BASE + 0x49c, reference, 2)
    m.run(0x8cc0)
    actual = m.get(BASE + 0x49a, 2)
    assert actual == expected, (sample, reference, actual)
    origins.append({'sample': sample, 'reference': reference, 'position': actual})
assert origins[-1]['position'] != 4096 + int((8191-8192)/4) # naive linear oracle rejected

inputs = [Path(__file__).resolve(), ROOT/'research/stock-1.8/oracle.py',
          ROOT/'research/stock-1.8/config.py']
result = {'status':'pass-bounded-original-instruction-contracts',
          'stockApplicationSHA256': FIRMWARE_SHA256,
          'phaseGateCases': rows, 'connectedConditionalStatusPath':'12,13,2,3,5,6',
          'echoOwnershipCases': echoes, 'rawEchoFormatterNormalizes':'checksum and terminator',
          'shutdownDispatchCases': shutdown, 'parkCases': park,
          'ordinaryTemplateSequenceCases': ordinary,
          'timeoutCanPublishCompletion': True, 'originCases': origins,
          'negativeControls': ['ID-only capture rule fails phase0 ID34 control',
              'phase-only capture rule fails disabled callback gate control',
              'immutable factory echo model fails changed-RX callback control',
              'verbatim malformed echo model fails formatter control',
              'unconditional park model fails disabled-option control',
              'linear signed origin model fails seam control',
              'ordinary seq+1 rule fails template-sequence control'],
          'cuts': {'CS':'RX start/stop 0x91c4/0x91ac; dummy PORT registers',
                   'TX':'0x51c8 and UART send 0x9180; bytes recorded synchronously',
                   'timers':'0x609c records requests; callbacks explicitly invoked',
                   'main':'critical sections, delays, NVM, UART disable, sleep preparation and final motor drivers stubbed; shutdown sleep tail not invoked',
                   'sensor':'0x89a4 returns caller supplied synthetic sample'},
          'limits':['No hardware, actual IRQ/DMA/peripheral timing or ordinary boot-to-connected reachability',
                    'RX mutation is a supplied dependency probe, not proof a live overwrite race is reachable',
                    'No homing enabling writer discovered; do not force gate or import synthetic origin',
                    'No full camera grammar, optics, physical travel, or factory equivalence claim'],
          'sourceSHA256': {str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs}}
assert hashlib.sha256(cfg.firmware.read_bytes()).hexdigest() == FIRMWARE_SHA256
(cfg.output/'results.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'status':result['status'],'phaseGateCases':len(rows),
                  'newFact':'delayed capture echo uses callback-time RX contents',
                  'negativeControls':len(result['negativeControls'])}))

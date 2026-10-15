#!/usr/bin/env python3
"""Offline original-Thumb shutdown-tail probes; only synthetic RAM/MMIO.

No hardware APIs. Original input is immutable. Output contains no ROM payload.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

if not __debug__:
    raise RuntimeError('Optimized Python disables assertions')
ROOT = Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(ROOT / 'research/stock-1.8'))
from config import configure, FIRMWARE_SHA256
cfg = configure(output=args.output)
from oracle import Machine
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, __version__
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_PC,
                               UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PRIMASK,
                               UC_ARM_REG_CONTROL, UC_ARM_REG_IPSR)

B = 0x20000000
RX = B + 0x694
UART = 0x42001000  # Deliberately synthetic valid descriptor register pointer.
SCR = 0xe000ed10
PM_SLEEP = 0x40000401
IN = 0x41004420
OUT = 0x60000010
DIR = 0x60000000


def packet(bad=False):
    result = bytearray([0xf0, 11, 0, 2, 0x71, 0x16, 0, 0, 0, 0, 0x55])
    result[-3:-1] = sum(result[1:-3]).to_bytes(2, 'little')
    if bad:
        result[-3:] = b'\xa5\xa5\x00'
    return bytes(result)


class Tail:
    def __init__(self, *, primask=0, state=2, completion=1, armed=0, park=0,
                 pins=(0, 0), direction=0, output=0, sync=(0,), bad=False,
                 tx_result=0, wake=False, pending_sample=False, initial_scr=0xa5):
        self.events = []
        self.reads = []
        self.writes = []
        self.pin_index = self.sync_index = 0
        self.pins, self.sync = pins, sync
        self.wake, self.pending_sample = wake, pending_sample
        self.stop_reason = None
        self.preformat = self.uart_frame = None
        self.critical_entries = []
        self.critical_exits = []

        def delay(m):
            self.events.append(['delay', m.u.reg_read(UC_ARM_REG_R0)])
            return -7  # Ignored return; no wall-clock timing implied.

        def tx(m):
            ptr, count = (m.u.reg_read(r) for r in [UC_ARM_REG_R0, UC_ARM_REG_R1])
            self.uart_frame = bytes(m.u.mem_read(ptr, count))
            self.events.append(['uart-send', count, tx_result])
            return tx_result

        # Original formatter, GPIO handoff, assertion, critical helpers, UART
        # disable and sleep setup all execute. DMA stop/TX/delay are cuts.
        self.m = Machine({0x66fc: delay, 0x9180: tx, 0x91ac: -7})
        for address, size in [(0x40000000, 0x2000), (0x41004000, 0x1000),
                              (0x42001000, 0x1000), (0x60000000, 0x1000),
                              (0xe000e000, 0x1000)]:
            self.m.u.mem_map(address, size)
        self.m.u.mem_write(B, bytes(0xc00))
        for offset, value in [(0x52a, 1), (0x52c, 1), (0x52d, state),
                              (0x4b8, completion), (0x4b1, armed),
                              (0x4bc, park), (0x604, int(pending_sample))]:
            self.m.set(B + offset, value, 1)
        self.m.u.mem_write(RX, packet(bad))
        self.m.set(B + 0x8b8, UART)  # descriptor+8 device, device+0x18 hw
        self.m.set(UART, 0xa5a50003)
        self.m.set(SCR, initial_scr)
        self.m.set(PM_SLEEP, 0x5a, 1)
        self.m.set(DIR, direction)
        self.m.set(OUT, output)
        self.m.u.reg_write(UC_ARM_REG_PRIMASK, primask)
        self.m.u.reg_write(UC_ARM_REG_CONTROL, 0)
        self.m.u.hook_add(UC_HOOK_CODE, self.code)
        self.m.u.hook_add(UC_HOOK_MEM_READ, self.read)
        self.m.u.hook_add(UC_HOOK_MEM_WRITE, self.write)

    def code(self, u, address, size, _):
        if address == 0x51c8:
            self.preformat = bytes(u.mem_read(RX, 11))
            self.events.append(['gpio-preformat'])
        elif address == 0x70d0:
            self.events.append(['uart-disable-entry'])
        elif address == 0x66cc:
            self.critical_entries.append(u.reg_read(UC_ARM_REG_PRIMASK))
        elif address == 0x66e4:
            self.critical_exits.append(u.reg_read(UC_ARM_REG_PRIMASK))
        elif address == 0x7a70:
            self.events.append(['sleep-setup', u.reg_read(UC_ARM_REG_R0)])
        elif address == 0x5f7e:
            self.events.append(['wfi-boundary', u.reg_read(UC_ARM_REG_PRIMASK)])
            if self.wake:
                # Deliberately skip the hint: supplied wake, not real sleep.
                u.reg_write(UC_ARM_REG_PC, address + 3)
            else:
                self.stop_reason = 'at-wfi-before-execution'
                u.emu_stop()
        elif address == 0x8cc0:
            assert self.wake and self.pending_sample
            self.events.append(['post-wake-sensor-entry'])
            self.stop_reason = 'post-wake-sensor-entry-cut'
            u.emu_stop()
        elif address in (0x8e28, 0x8dd4, 0x8e88, 0x8ed8, 0x8f28, 0x8f78):
            raise AssertionError('unexpected motor helper in isolated tail: ' + hex(address))

    def read(self, u, access, address, size, value, _):
        if address == IN:
            value = self.pins[min(self.pin_index, len(self.pins)-1)]
            self.pin_index += 1
            self.m.set(IN, value)
            mask = u.reg_read(UC_ARM_REG_PRIMASK)
            self.reads.append({'address': hex(address), 'value': value, 'primask': mask})
        elif address == UART + 0x1c:
            value = self.sync[min(self.sync_index, len(self.sync)-1)]
            self.sync_index += 1
            self.m.set(address, value)
            if self.sync_index <= 8:
                self.reads.append({'address': hex(address), 'value': value})

    def write(self, u, access, address, size, value, _):
        if address >= 0x40000000:
            self.writes.append({'address': hex(address), 'size': size, 'value': value})
            if address == UART:
                self.events.append(['uart-enable-bit-clear', value])
            elif address == 0x60000018 and value == 0x800000:
                self.events.append(['gpio-pa23-set'])

    def run(self, budget=20000):
        u = self.m.u
        u.reg_write(UC_ARM_REG_SP, B + 0x3e00)
        u.reg_write(UC_ARM_REG_LR, 0x1001)
        u.emu_start(0x5e01, 0x1000, count=budget)
        if not self.stop_reason:
            self.stop_reason = 'returned' if u.reg_read(UC_ARM_REG_PC) == 0x1000 else 'instruction-budget'
        return self

    def result(self):
        return {'stop': self.stop_reason, 'pc': hex(self.m.u.reg_read(UC_ARM_REG_PC)),
                'events': self.events[:24], 'eventCount': len(self.events),
                'registerWrites': self.writes,
                'inputReads': self.reads[:12], 'inputReadCount': len(self.reads),
                'pinSamples': self.pin_index,
                'uartSyncReads': self.sync_index,
                'criticalEntries': self.critical_entries[:12],
                'criticalRestores': self.critical_exits[:12],
                'criticalEntryCount': len(self.critical_entries),
                'finalPrimask': self.m.u.reg_read(UC_ARM_REG_PRIMASK),
                'requestFlag': self.m.get(B + 0x52c, 1),
                'shutdownState': self.m.get(B + 0x52d, 1),
                'completion': self.m.get(B + 0x4b8, 1),
                'armed': self.m.get(B + 0x4b1, 1),
                'preformatEqualsValid': self.preformat == packet(),
                'uartEqualsValid': self.uart_frame == packet()}


rows = []
def save(name, probe, **inputs):
    rows.append({'name': name, 'inputs': inputs, **probe.result()})


expected_events = ['gpio-preformat', 'uart-send', 'delay', 'uart-disable-entry',
                   'uart-enable-bit-clear', 'delay', 'delay', 'gpio-pa23-set',
                   'delay', 'sleep-setup', 'wfi-boundary']

for mask in [0, 1]:
    for completion in [0, 1]:
        for armed in [0, 1]:
            for park in [0, 1]:
                t = Tail(primask=mask, completion=completion, armed=armed, park=park).run()
                r = t.result()
                assert r['stop'] == 'at-wfi-before-execution'
                assert [e[0] for e in t.events] == expected_events
                assert [e[1] for e in t.events if e[0] == 'delay'] == [50, 1, 1, 100]
                assert r['completion'] == completion and r['armed'] == armed
                assert r['requestFlag'] == 0 and r['shutdownState'] == 2
                assert r['criticalEntries'] == r['criticalRestores'] == [mask, mask]
                assert r['finalPrimask'] == mask
                assert all(x['primask'] == 1 for x in t.reads if x['address'] == hex(IN))
                assert t.m.get(UART) == 0xa5a50001
                assert t.m.get(SCR) == 0xa1 and t.m.get(PM_SLEEP, 1) == 2
                assert [x['address'] for x in t.writes] == [
                    '0x60000018', hex(UART), '0x60000018', hex(SCR), hex(PM_SLEEP)]
                assert t.m.u.reg_read(UC_ARM_REG_CONTROL) == 0 and t.m.u.reg_read(UC_ARM_REG_IPSR) == 0
                assert r['uartEqualsValid']
                save('terminal-flags-mask', t, primask=mask, completion=completion, armed=armed, park=park)

# Only the dependency into the terminal tail: do not repeat state0 park behavior.
t = Tail(state=1, completion=0, armed=1).run()
assert t.stop_reason == 'returned' and not t.events and t.m.get(B+0x52d, 1) == 1
save('state1-not-complete', t)
t = Tail(state=1, completion=1, armed=1).run()
assert t.stop_reason == 'returned' and not t.events and t.m.get(B+0x52d, 1) == 2
save('state1-complete-only-advances', t)
t.m.set(B+0x4b8, 0, 1)  # Supplied state change between foreground calls.
t.stop_reason = None
t.run()
assert t.stop_reason == 'at-wfi-before-execution' and t.m.get(B+0x4b1, 1) == 1
save('completion-cleared-after-state2-still-enters-tail', t)

for name, pins, expected_samples in [('initial-high', (8, 8, 0, 0), 4),
                                     ('second-sample-high', (0, 8, 0, 0), 4)]:
    t = Tail(pins=pins).run()
    assert t.stop_reason == 'at-wfi-before-execution' and t.pin_index == expected_samples
    assert len(t.critical_entries) == expected_samples
    save(name, t, pins=pins)
t = Tail(pins=(8,)).run(budget=4000)
assert t.stop_reason == 'instruction-budget' and t.pin_index > 2
assert not any(e[0] in ['sleep-setup', 'wfi-boundary', 'gpio-pa23-set'] for e in t.events)
save('held-high-input-no-finite-tail', t)

# DIR selects IN for an input bit, OUT for an output bit.
t = Tail(pins=(8,), direction=8, output=0).run()
assert t.stop_reason == 'at-wfi-before-execution' and t.pin_index == 2
save('output-configured-pin-selects-out-low', t)
t = Tail(pins=(0,), direction=8, output=8).run(budget=4000)
assert t.stop_reason == 'instruction-budget'
save('output-configured-pin-selects-out-high', t)

t = Tail(sync=(2, 2, 0)).run()
assert t.stop_reason == 'at-wfi-before-execution' and t.sync_index == 3
save('uart-sync-eventually-clears', t)
t = Tail(sync=(2,)).run(budget=4000)
assert t.stop_reason == 'instruction-budget' and t.sync_index > 2 and t.pin_index == 0
assert not any(e[0] in ['sleep-setup', 'wfi-boundary'] for e in t.events)
save('uart-sync-held-no-finite-tail', t)
t = Tail(sync=(1,)).run(budget=4000)
assert t.stop_reason == 'instruction-budget' and t.pin_index == 0
save('uart-sync-bit0-also-blocks', t)
t = Tail(sync=(4,)).run()
assert t.stop_reason == 'at-wfi-before-execution' and t.sync_index == 1
save('uart-sync-bit2-does-not-block', t)

for tx_result in [0, -7]:
    t = Tail(bad=True, tx_result=tx_result).run()
    assert t.stop_reason == 'at-wfi-before-execution'
    assert t.preformat == packet(True) and t.uart_frame == packet()
    save('preformat-is-not-uart', t, suppliedTxReturn=tx_result,
         bypassesRxAdmission=True)

for scr in [0, 4, 0xffffffff]:
    t = Tail(initial_scr=scr).run()
    assert t.m.get(SCR) == scr & ~4
    assert t.m.get(PM_SLEEP, 1) == 2
    save('sleep-mode2-clears-deep-bit', t, suppliedSCR=scr)

t = Tail(wake=True).run()
assert t.stop_reason == 'returned'
save('supplied-wake-returns', t)
t = Tail(wake=True, pending_sample=True).run()
assert t.stop_reason == 'post-wake-sensor-entry-cut'
assert t.m.get(B+0x604, 1) == 0
save('supplied-wake-enters-pending-sample', t)

# Contrasting fixture controls: each incorrect interpretation is evaluated
# against actual traces, and MUST disagree rather than merely being described.
def named(name):
    return next(r for r in rows if r['name'] == name)

wrong = {
    'preformat GPIO handoff is the wire buffer': named('preformat-is-not-uart')['preformatEqualsValid'] == named('preformat-is-not-uart')['uartEqualsValid'],
    'state2 rechecks completion and refuses sleep if zero': rows[0]['stop'] != 'at-wfi-before-execution',
    'tail always clears motor armed': next(r for r in rows if r['name']=='terminal-flags-mask' and r['inputs']['armed']==1)['armed'] == 0,
    'tail always enables interrupts before WFI': next(r for r in rows if r['name']=='terminal-flags-mask' and r['inputs']['primask']==1)['finalPrimask'] == 0,
    'first low sample alone permits sleep': named('second-sample-high')['pinSamples'] == 1,
    'PA3 wait has a finite local timeout': named('held-high-input-no-finite-tail')['stop'] == 'at-wfi-before-execution',
    'UART disable ignores synchronization': named('uart-sync-held-no-finite-tail')['pinSamples'] > 0,
    'WFI is a terminal return with no pending foreground work': named('supplied-wake-enters-pending-sample')['stop'] == 'returned',
    'sleep argument2 selects deep sleep': any(w['address'] == hex(SCR) and w['value'] & 4 for w in rows[0]['registerWrites']),
}
assert all(not value for value in wrong.values()), wrong

sources = [Path(__file__), ROOT/'research/stock-1.8/oracle.py', ROOT/'research/stock-1.8/config.py']
record = {
    'status': 'pass-bounded-original-tail', 'stockApplicationSHA256': FIRMWARE_SHA256,
    'unicornVersion': __version__, 'caseCount': len(rows), 'cases': rows,
    'traceTruncation': 'Events capped at 24, input reads and critical masks at 12 per case; full counts retained. Only budget-exhaustion traces exceed these caps.',
    'wrongInterpretationsRejected': list(wrong),
    'cuts': {'delay0x66fc': 'recorded call, returns -7; no time passes',
             'dmaStop0x91ac': 'returns -7, no DMA model',
             'uartSend0x9180': 'records complete formatted synthetic frame and supplies return; no physical TX completion',
             'wfi0x5f7e': 'stop before execution, or explicit PC skip as supplied wake',
             'sensor0x8cc0': 'stop at entry only in pending-work supplied-wake case'},
    'executedBoundaries': ['0x51d4 formatter', '0x51c8 GPIO handoff',
                          '0x70d0/0x7d56 UART disable', '0x7174 valid-descriptor assertion',
                          '0x66cc/0x66da PRIMASK save/disable/restore', '0x7a70 sleep preparation'],
    'limits': ['Supplied state1/state2, synthetic RX, Thread mode CONTROL=0, no asynchronous exceptions',
               'MMIO is inert RAM with caller-scripted PA3 and UART sync inputs; UART descriptor hardware pointer supplied',
               'No physical sleep/wake, pending IRQ eligibility, latency, oscillator, motor cancellation or travel proof',
               'Budget exhaustion plus inspected back-edge establishes no local software timeout, not a physical hang',
               'No ordinary boot-to-shutdown reachability, complete firmware equivalence or camera acceptance'],
    'sourceSHA256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    'originalRangeSHA256': {f'{lo:#x}-{hi-1:#x}': hashlib.sha256(cfg.rom[lo-0x5000:hi-0x5000]).hexdigest()
                           for lo, hi in [(0x5e00,0x6060),(0x51c8,0x5238),(0x66cc,0x66e6),
                                          (0x70d0,0x70fc),(0x7d56,0x7d68),(0x7a70,0x7aa8)]}}
assert hashlib.sha256(cfg.firmware.read_bytes()).hexdigest() == FIRMWARE_SHA256
(cfg.output/'results.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({'status': record['status'], 'cases': len(rows), 'wrongInterpretationsRejected': len(wrong)}))

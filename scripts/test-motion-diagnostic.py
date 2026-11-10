#!/usr/bin/env python3
"""Run compiled 4.8.1 homing/AF hooks and the trace NVM path in synthetic ARM."""
import argparse
from pathlib import Path
import runpy
import struct
import tempfile

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_INVALID
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'test-profile-nvm-arm.py'))
DECODER = runpy.run_path(str(HERE / 'decode-motion-diagnostic.py'))
TRACE_START, TRACE_END = DECODER['TRACE_START'], DECODER['TRACE_END']
SLOT_BYTES = DECODER['SLOT_BYTES']
decode = DECODER['decode']
NVM = BASE['NVM']
SCRATCH = 0x20003d00


class Machine(BASE['Machine']):
    def __init__(self, build):
        super().__init__(build)
        self.u.mem_map(0x40000000, 0x1000)  # PM reset cause read by the homing routine
        self.u.mem_map(0xe000e000, 0x1000)  # SysTick value read by focus reporting
        self.u.mem_write(TRACE_START, b'\xff' * (TRACE_END - TRACE_START))
        self.trace_pages = []
        self.now, self.raw, self.duty = 0, 1600, 0
        self.hard_stop, self.duty_divisor = 1200, 60
        self.inject = False
        self.stubs = {self.symbols[name]: handler for name, handler in {
            'millis': self.tick, 'abs_encoder_raw': lambda _: self.raw,
            'motor_drive': self.motor_drive, 'motor_brake': lambda _: self.motor_drive(0),
            'motor_attach_pins': lambda _: 0, 'vdd_read_burst': lambda _: 0,
            'vdd_track_reset': lambda _: 0, 'vdd_track_result': lambda _: 0,
            'pump': lambda _: 0,
        }.items()}
        self.u.hook_add(UC_HOOK_CODE, self.hardware)
        self.u.hook_add(UC_HOOK_MEM_INVALID, self.unexpected_memory)

    def unexpected_memory(self, u, access, addr, size, value, data):
        print(f'Unmodeled memory at {addr:#x} from {u.reg_read(UC_ARM_REG_PC):#x}', flush=True)
        return False

    def write(self, u, access, addr, size, value, data):
        if TRACE_START <= addr < TRACE_END:
            assert addr + size <= TRACE_END
            return
        if addr == NVM and TRACE_START <= self.get(NVM + 0x1c) * 2 < TRACE_END:
            assert value in (0xa504, 0xa544, 0xa546), 'Trace path issued a non-program command.'
            if value == 0xa504:
                target = self.get(NVM + 0x1c) * 2
                assert target % 64 == 0 and target not in self.trace_pages
                self.trace_pages.append(target)
                self.set(NVM + 0x14, 0, 1)
                self.busy = 4
            self.commands.append(value & 255)
            return
        super().write(u, access, addr, size, value, data)

    def hardware(self, u, addr, size, data):
        if addr in self.stubs:
            value = self.stubs[addr](u.reg_read(UC_ARM_REG_R0))
            u.reg_write(UC_ARM_REG_R0, value & 0xffffffff)
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))

    def motor_drive(self, duty):
        self.duty = (duty & 0xffff) if duty & 0x8000 == 0 else (duty & 0xffff) - 65536
        return 0

    def tick(self, _):
        self.now += 1
        step = abs(self.duty) // self.duty_divisor
        self.raw = min(7000, max(self.hard_stop, self.raw + step * ((self.duty > 0) - (self.duty < 0))))
        if self.inject and self.raw >= 1450:
            self.queue_move(4164)  # 80 counts, behind the current leg.
            self.inject = False
        return self.now

    def queue_move(self, operand):
        self.u.mem_write(self.symbols['g_cmd'], struct.pack('<BBH', 1, 0, operand) + bytes(16))
        self.set(self.symbols['em_focus_pending'], 1, 1)

    def save(self):
        return self.run('mt_save', TRACE_START, self.symbols['mt_samd21_write_page'] | 1)

    def trace(self, slot=0):
        return bytes(self.u.mem_read(TRACE_START + slot * SLOT_BYTES, SLOT_BYTES))


def exercise(build):
    m = Machine(build)
    assert m.run('profile_runtime_init') == 1
    before = bytes(m.u.mem_read(0, 0x20000))
    m.run('abs_encoder_track_reset')
    m.run('motor_home')
    assert m.get(m.symbols['g_homed']) == 1 and m.raw == 1200
    m.queue_move(4269)  # 500 counts
    assert m.run('em_take_focus_cmd', SCRATCH) == 1
    assert m.run('em_take_focus_cmd', SCRATCH) == 0
    m.set(m.symbols['g_last_op'], 1, 1)
    m.inject = True
    assert m.run('focus_run', 500, 4269, m.symbols['STOCK']) == 0
    assert not m.commands and m.trace() == before[TRACE_START:TRACE_START + SLOT_BYTES]
    assert m.save() == 1
    assert m.trace_pages[-1] == TRACE_START
    assert m.commands == [0x44, 4, 0x46] * len(m.trace_pages)
    assert m.save() == 0
    after = bytes(m.u.mem_read(0, 0x20000))
    assert after[:TRACE_START] == before[:TRACE_START] and after[TRACE_END:] == before[TRACE_END:]

    result = decode(m.trace())
    assert result['status'] == 'complete' and result['afEventsDropped'] == 0
    phases = [e for e in result['homing'] if e['event'] == 'home-phase']
    assert [e['phase'] for e in phases] == ['drive-start', 'drive-still', 'settle-start', 'settle-still', 'origin']
    assert phases[0]['raw'] == 1600
    assert phases[-1]['raw'] == 1200 and phases[-1]['trackedCounts'] == 0
    assert any(e['event'] == 'home-sample' and 1200 < e['raw'] < 1600 for e in result['homing'])
    events = result['autofocus']
    assert [e['operand'] for e in events if e['event'] == 'command'] == [4269, 4164]
    assert any(e['event'] == 'retarget' and e['targetCounts'] == 80 and e['reversal'] for e in events)
    assert any(e['event'] == 'servo-sample' and e['duty'] < 0 for e in events)
    assert events[-1]['event'] == 'leg-end' and events[-1]['targetCounts'] == 80
    assert abs(events[-1]['actualCounts'] - 80) <= 40
    assert all(a['ms'] <= b['ms'] for a, b in zip(events, events[1:]))

    for offset in (63, 64, DECODER['AF_OFFSET']):
        broken = bytearray(m.trace())
        broken[offset] ^= 1
        try:
            decode(broken)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Corrupt trace at {offset} accepted.')
    partial = bytearray(m.trace())
    partial[:64] = b'\xff' * 64
    assert decode(partial)['status'] == 'incomplete'

    # A fresh boot saves the second session without rewriting the first.
    m.u.mem_write(0x20000000, m.initial_ram)
    m.run('mt_home_phase', 1, 7, 1200, 0)
    assert m.save() == 1 and m.trace_pages[-1] == TRACE_START + SLOT_BYTES
    assert decode(m.trace(1))['autofocus'] == []
    assert decode(m.trace()) == result
    m.u.mem_write(0x20000000, m.initial_ram)
    m.run('mt_home_phase', 1, 7, 1200, 0)
    pages = m.trace_pages[:]
    assert m.save() == 0 and m.trace_pages == pages
    assert decode(m.trace()) == result


def storage_controls(build):
    m = Machine(build)
    assert decode(m.trace()) == {'status': 'empty'}
    m.run('mt_home_phase', 1, 7, 1200, 0)
    for i in range(205):
        m.run('mt_record', i + 2, 3, 1, 0)  # extra two arguments zero in mapped stack
    assert m.save() == 1
    snapshot = decode(m.trace())
    assert snapshot['afEventsDropped'] == 13
    assert [e['ms'] for e in snapshot['autofocus']] == list(range(15, 207))
    for off, page in [(0, 0), (1, SCRATCH), (8192, SCRATCH), (0xffffffff, SCRATCH), (64, SCRATCH)]:
        assert m.run('mt_samd21_write_page', off, page) == -1
    assert len(m.commands) == 3 * len(m.trace_pages)

    for failure in ('foreign', 'locked', 'not-ready', 'command-error'):
        n = Machine(build)
        n.run('mt_home_phase', 1, 7, 1200, 0)
        if failure == 'foreign':
            n.u.mem_write(TRACE_START + SLOT_BYTES - 1, b'\x00')
            n.u.mem_write(TRACE_END - 1, b'\x00')
        elif failure == 'locked':
            n.set(NVM + 0x20, 0xffff ^ (1 << (TRACE_START // 8192)), 2)
        elif failure == 'not-ready':
            n.set(NVM + 0x14, 0, 1)
        else:
            n.command_error = True
        assert n.save() == 0
        assert n.trace()[:64] == b'\xff' * 64
        assert n.commands == ([0x44, 4] if failure == 'command-error' else [])
        commands = n.commands[:]
        assert n.save() == 0 and n.commands == commands

    m = Machine(build)
    m.u.mem_write(TRACE_START + 64, b'\x00')
    m.run('mt_home_phase', 1, 7, 1200, 0)
    assert m.save() == 1 and m.trace_pages[-1] == TRACE_START + SLOT_BYTES
    assert decode(m.trace())['status'] == 'incomplete'


def homing_controls(build):
    for limit, divisor, reason in [(1600, 60, 'drive-still'), (1200, 800, 'drive-cap')]:
        m = Machine(build)
        m.hard_stop, m.duty_divisor = limit, divisor
        m.run('abs_encoder_track_reset')
        m.run('motor_home')
        assert not m.commands and m.save() == 1
        phases = [e for e in decode(m.trace())['homing'] if e['event'] == 'home-phase']
        assert phases[1]['phase'] == reason
        assert phases[-1]['phase'] == 'origin' and phases[-1]['trackedCounts'] == 0
        assert phases[-1]['raw'] == m.raw
        if reason == 'drive-cap':
            assert limit < m.raw < phases[0]['raw']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    build = p.parse_args().build.resolve()
    if not __debug__:
        raise SystemExit('Run without Python optimization.')
    with tempfile.TemporaryDirectory(prefix='ola-motion-test-') as temp:
        assembled = Path(temp)
        for name in ('application.bin', 'extension.bin'):
            (assembled / name).symlink_to(build / name)
        for name in ('bank.bin', 'settings.bin', 'build'):
            (assembled / name).symlink_to(build / 'work' / name)
        exercise(assembled)
        storage_controls(assembled)
        homing_controls(assembled)
    print('Compiled ARM homing, AF retarget/reversal, trace persistence and failing controls passed.')


if __name__ == '__main__':
    main()

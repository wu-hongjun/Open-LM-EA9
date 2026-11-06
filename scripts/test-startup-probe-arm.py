#!/usr/bin/env python3
"""Exercise the linked probe instructions with supplied SAMD21 register behavior."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from unicorn import (Uc, UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB,
                     UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE)
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

ROOT = Path(__file__).resolve().parents[1]
NM = ROOT / ('tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/'
             'bin/arm-none-eabi-nm')
PORT = 0x41004400
NVM = 0x41004000
EIC = 0x40001800
UART = 0x42000c00
BODY, LENS = 1 << 2, 1 << 10
BUF, REQUEST, RET = 0x20003000, 0x20003200, 0x30000000
PADS = (8, 9, 18, 19)
ACTUATORS = (0x42000800, 0x42002000, 0x42002400, 0x42003000, 0x42004000)


class Target:
    def __init__(self, image, symbols):
        self.symbols = symbols
        self.writes = []
        self.fifo = []
        self.tx = []
        self.stop_on_eic_enable = False
        self.countdown = 47999
        self.overlap = None
        self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        for address, length in [(0, 0x20000), (0x20000000, 0x4000), (RET, 0x1000),
                                (0x00806000, 0x1000), (0x40000000, 0x2000),
                                (NVM, 0x1000), (0x42000000, 0x5000), (0xe000e000, 0x1000)]:
            self.u.mem_map(address, length)
        self.u.mem_write(0, b'\xff' * 0x20000)
        self.u.mem_write(0x5000, image)
        self.set(0x4000080c, 1 << 4, 4)  # DFLL ready
        self.set(NVM + 0x14, 1, 1)
        self.set(0xe000e014, 47999, 4)
        self.u.hook_add(UC_HOOK_MEM_READ, self.read)
        self.u.hook_add(UC_HOOK_MEM_WRITE, self.write)
        self.u.hook_add(UC_HOOK_CODE, self.code)

    def set(self, address, value, size=1):
        self.u.mem_write(address, value.to_bytes(size, 'little'))

    def get(self, address, size=1):
        return int.from_bytes(self.u.mem_read(address, size), 'little')

    def read(self, _, access, address, size, value, user):
        if address in (EIC, UART) and self.get(address, size) == 1:
            self.set(address, 0, size)  # hardware clears SWRST
        elif address == UART + 0x18:
            self.set(address, 3 | (4 if self.fifo else 0), size)
        elif address == UART + 0x28:
            self.set(address, self.fifo.pop(0), size)
        elif address == 0xe000e018:
            if self.overlap == 'hold':
                self.set(PORT + 0x20, BODY, 4)
            self.countdown = (self.countdown - 240) % 48000
            self.set(address, self.countdown, size)

    def write(self, _, access, address, size, value, user):
        value &= (1 << (8 * size)) - 1
        if address >= 0x40000000 or address < 0x20000:
            self.writes.append((address, size, value))
        if address == UART + 0x28:
            self.tx.append(value)
            if self.overlap == 'data':
                self.set(PORT + 0x20, BODY, 4)
        if self.stop_on_eic_enable and address == 0xe000e100 and value == 1 << 4:
            self.finished = True
            self.u.emu_stop()

    def code(self, _, address, size, user):
        if address == RET:
            self.finished = True
            self.u.emu_stop()

    def call(self, symbol, *args, limit=200000):
        self.finished = False
        for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2), args):
            self.u.reg_write(register, value)
        self.u.reg_write(UC_ARM_REG_SP, 0x20004000)
        self.u.reg_write(UC_ARM_REG_LR, RET | 1)
        self.u.emu_start(self.symbols[symbol] | 1, RET + 2, count=limit)
        assert self.finished, symbol
        return self.u.reg_read(UC_ARM_REG_R0)

    def body_edge(self, high):
        self.set(PORT + 0x20, BODY if high else 0, 4)
        self.set(EIC + 0x10, BODY, 4)
        self.call('EIC_Handler')
        self.set(EIC + 0x10, 0, 4)

    def feed(self, data):
        for byte in data:
            self.fifo.append(byte)
            self.call('SERCOM1_Handler')

    def never_drives_motor(self):
        motor_mask = sum(1 << i for i in PADS)
        assert not any(value & motor_mask for addr, _, value in self.writes if addr == PORT + 8)
        assert not any(value for addr, _, value in self.writes if addr in {PORT + 0x40 + i for i in PADS})
        assert not any(base <= addr < base + 0x400 for addr, _, _ in self.writes for base in ACTUATORS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    args = parser.parse_args()
    build = args.build.resolve()
    image = (build / 'startup-probe.bin').read_bytes()
    assert hashlib.sha256(image).hexdigest() == json.loads((build / 'manifest.json').read_text())['imageSHA256']
    assert image == (ROOT / 'firmware/candidates/4.3.0/startup-probe.bin').read_bytes()
    symbols = {}
    for line in subprocess.check_output([str(NM), str(build / 'probe.elf')], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)

    t = Target(image, symbols)
    t.stop_on_eic_enable = True
    t.call('main')
    assert t.writes[0] == (PORT + 4, 4, sum(1 << i for i in PADS))
    assert [event for event in t.writes if event[0] == UART + 0xc] == [(UART + 0xc, 2, 0xc000)], t.writes
    assert all(t.get(PORT + 0x40 + i) == 0 for i in PADS)
    assert not any(addr == NVM for addr, _, _ in t.writes)
    t.never_drives_motor()

    opener = bytearray([0xf0, 41, 0, 2, 0x7e, 1] + [0] * 32 + [0, 0, 0x55])
    opener[-3:-1] = sum(opener[1:-3]).to_bytes(2, 'little')
    for early in (0, 2, len(opener)):
        t = Target(image, symbols)
        t.feed(opener[:early])
        t.body_edge(True)
        t.feed(opener[early:])
        t.body_edge(False)
        assert t.call('probe_take', symbols['state'], REQUEST) == 1
        assert t.u.mem_read(REQUEST + 8, len(opener)) == opener
    t = Target(image, symbols)
    t.body_edge(True)
    t.feed(opener[:6])
    t.body_edge(False)
    assert t.call('probe_take', symbols['state'], REQUEST) == 0

    for case, expected in [('busy', 0), ('data', 1), ('hold', 2), (None, 3)]:
        t = Target(image, symbols)
        t.u.mem_write(BUF, bytes(opener))
        t.set(symbols['ticks'], 12, 4)
        if case == 'busy':
            t.set(PORT + 0x20, BODY, 4)
        t.overlap = case
        assert t.call('send', BUF, len(opener), REQUEST) == expected, case
        cs = [address for address, _, value in t.writes if value == LENS and address in (PORT + 0x14, PORT + 0x18)]
        assert cs == ([] if case == 'busy' else [PORT + 0x18, PORT + 0x14])
        assert bytes(t.tx) == opener[:{0: 0, 1: 1, 2: len(opener), 3: len(opener)}[expected]]
        assert t.get(REQUEST, 4) == (12 if expected >= 2 else 0)
        t.never_drives_motor()

    for address, occupied, error, good in [(0x9c00, False, False, True), (0x9fc0, False, False, True),
                                           (0x9bc0, False, False, False), (0x9c01, False, False, False),
                                           (0xa000, False, False, False), (0, False, False, False),
                                           (0x804000, False, False, False), (0x9c00, True, False, False),
                                           (0x9c00, False, True, False)]:
        t = Target(image, symbols)
        payload = bytes(range(64))
        t.u.mem_write(BUF, payload)
        if occupied:
            t.set(address, 0)
        if error:
            t.set(NVM + 0x18, 4, 2)
        before = bytes(t.u.mem_read(0, 0x20000))
        assert t.call('probe_write_page', address, BUF) == good
        after = bytes(t.u.mem_read(0, 0x20000))
        commands = [value for addr, _, value in t.writes if addr == NVM]
        stores = [addr for addr, size, _ in t.writes if addr < 0x20000 and size == 4]
        assert before[:0x9c00] == after[:0x9c00] and before[0xa000:] == after[0xa000:]
        assert commands == ([0xa544, 0xa504] if good else [])
        assert stores == (list(range(address, address + 64, 4)) if good else [])
        assert t.get(NVM + 0x1c, 4) == (address // 2 if good else 0)
        assert (after[address:address + 64] == payload) == good
    print('ARM probe startup, four RX cases, four TX cases and nine NVM cases passed.')


if __name__ == '__main__':
    main()

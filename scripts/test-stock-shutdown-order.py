#!/usr/bin/env python3
"""Replay original stock shutdown under an explicitly ready phase and PA3 low."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
out = parser.parse_args().output.resolve()
sys.path.insert(0, str(ROOT / 'research/stock-1.8'))
from config import configure, FIRMWARE_SHA256
configure(ROOT / 'firmware/recovery/stock-1.8.0/application.bin', out, 'clang')
from oracle import Machine

results = []
scenarios = [(sample, sequence, True) for sample in [0, 1, 4095, 4096, 5000, 16383] for sequence in [0, 1, 0x71, 0xff]]
scenarios.append((0, 0x71, False))  # Direct-state counterexample bypasses validated RX.
for sample, sequence, valid_checksum in scenarios:
    actions = []
    def tx(machine):
        actions.append({'kind': 'transmit', 'frame': bytes(machine.u.mem_read(0x20000694, 11)).hex()})
        return -7
    def action(kind):
        def stub(machine):
            actions.append({'kind': kind, 'argument': machine.calls[-1]['args'][0]})
            return -7
        return stub
    machine = Machine({0x51c8: tx, 0x91c4: 0, 0x91ac: 0, 0x66cc: 0, 0x66da: 0,
                       0x66fc: action('delay'), 0x70d0: action('uart-disable'), 0x7a70: action('sleep-setup'),
                       0x89a4: sample, 0x6a38: 0, 0x6918: 0, 0x69b0: 0})
    machine.u.mem_map(0x60000000, 0x1000)
    machine.u.mem_map(0x41004000, 0x1000)
    machine.u.mem_write(0x20000000, bytes(2048))
    frame = bytearray([0xf0, 11, 0, 2, sequence, 0x16, 0, 0, 0, 0, 0x55])
    frame[-3:-1] = sum(frame[1:-3]).to_bytes(2, 'little')
    if not valid_checksum: frame[-3:-1] = b'\xa5\xa5'
    machine.u.mem_write(0x20000694, bytes(frame))
    for off, value in [(0x52c, 1), (0x52d, 2), (0x695, 11)]: machine.set(0x20000000 + off, value, 1)
    def write(u, access, address, size, value, user):
        if address == 0x60000018 and value == 0x800000:
            actions.append({'kind': 'pa23-high', 'argument': value})
    def wake(u, address, size, user):
        if address == 0x5f7e:
            actions.append({'kind': 'wfi-simulated-wake'})
            u.reg_write(UC_ARM_REG_PC, address + 3)
    machine.u.hook_add(UC_HOOK_MEM_WRITE, write)
    machine.u.hook_add(UC_HOOK_CODE, wake)
    machine.run(0x5e00)
    kinds = [a['kind'] for a in actions]
    expected = ['transmit', 'delay', 'uart-disable', 'delay', 'delay', 'pa23-high', 'delay', 'sleep-setup', 'wfi-simulated-wake']
    if kinds != expected or [a['argument'] for a in actions if a['kind'] == 'delay'] != [50, 1, 1, 100]:
        raise RuntimeError('Original shutdown action-order mismatch: ' + repr(actions))
    if actions[0]['frame'] != frame.hex(): raise RuntimeError('Original shutdown echo mismatch')
    results.append({'sample': sample, 'sequence': sequence, 'incomingChecksumValid': valid_checksum, 'bypassesReceiverValidation': not valid_checksum, 'actions': actions})
record = {'sourceApplicationSHA256': FIRMWARE_SHA256, 'entry': '0x5e00', 'cases': results,
          'passingCases': len(results), 'validEchoCases': 24, 'directStateBadChecksumEchoCases': 1, 'hardwareReportsSent': 0,
          'checksumFinding': 'Shutdown echoes the retained request without repairing its checksum at this direct-state boundary. The bad-checksum fixture bypasses RX and is not a legal camera request.',
          'contract': 'Seeded shutdown phase 2; PA3 low; lower UART/timing/GPIO boundaries stubbed, dummy register memory and WFI wake supplied. Not reachability or physical timing.',
          'scriptSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'supportSHA256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                            for name in ['research/stock-1.8/config.py', 'research/stock-1.8/oracle.py', 'research/stock-1.8/requirements.txt']},
          'transmitCut': '0x51c8 final sender stub; retained request buffer observed at that boundary',
          'dummyRegisterPages': ['0x41004000', '0x60000000']}
(out / 'validation.json').write_text(json.dumps(record, indent=2) + '\n')
print(f'Passed {len(results)} original shutdown echo/order fixtures; hardware reports 0.')

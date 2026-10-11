#!/usr/bin/env python3
"""Compare production factory AF math with pinned original Thumb instructions.

Requires the existing REA Unicorn environment. No USB/device imports. Evidence
goes to a fresh directory; retained evidence is never replaced.
"""
import argparse
import ctypes as ct
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/stock-1.8"))
from config import configure, compile_library, FIRMWARE_SHA256

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path)
cfg = configure(output=parser.parse_args().output)
from oracle import Machine


class State(ct.Structure):
    _fields_ = [(n, ct.c_uint32) for n in ("accumulator", "previous_error", "previous_error2")] + [
        (n, ct.c_int32) for n in ("target", "previous_position", "velocity", "duty")
    ] + [("timeout", ct.c_uint16)] + [
        (n, ct.c_uint8) for n in ("direction", "enabled", "armed", "completed", "divider")
    ]


source = ROOT / "firmware/ea9/src/factory_af.c"
library = ct.CDLL(str(compile_library(source, "production_factory_af")))
for name, args, result in [
    ("target", [ct.POINTER(State), ct.c_uint16, ct.c_int32], None),
    ("stop", [ct.POINTER(State)], None),
    ("speed", [ct.c_uint8, ct.c_int32], ct.c_int32),
    ("pid", [ct.POINTER(State), ct.c_int32], ct.c_int32),
    ("control", [ct.POINTER(State), ct.c_int32], ct.c_int32),
    ("complete", [ct.POINTER(State), ct.c_int32], ct.c_uint8),
    ("tick", [ct.POINTER(State), ct.c_int32], ct.c_uint8),
]:
    function = getattr(library, "ea9_factory_" + name)
    function.argtypes, function.restype = args, result

drivers = []


def driver(address):
    def record(machine):
        drivers.append((address, machine.calls[-1]["args"][0]))
        return 0
    return record


machine = Machine({a: driver(a) for a in (0x8e88, 0x8ed8, 0x8f28, 0x8f78)})
# Execute the original stop's register stores against dummy RAM only.
machine.u.mem_map(0x41004000, 0x1000)
machine.u.mem_map(0x60000000, 0x1000)
fields = {
    "accumulator": (0x4f4, 4, False), "previous_error": (0x4d0, 4, False),
    "previous_error2": (0x4d4, 4, False), "target": (0x4a8, 2, True),
    "previous_position": (0x638, 2, True), "velocity": (0x4a4, 2, True),
    "duty": (0x63c, 4, True), "timeout": (0x4b4, 2, False),
    "direction": (0x4b0, 1, False), "enabled": (0x4b2, 1, False),
    "armed": (0x4b1, 1, False), "completed": (0x4b8, 1, False),
    "divider": (0x605, 1, False),
}
entries = {"target": 0x8dd4, "stop": 0x8e28, "speed": 0x8d20,
           "pid": 0x8bfc, "control": 0x8fc8, "complete": 0x8d94, "tick": 0x8a2c}
rng = random.Random(0x240180)
counts = {name: 0 for name in entries}


def seed(state, position):
    machine.u.mem_write(0x20000000, bytes(0x800))
    for name, (offset, width, _) in fields.items():
        machine.set(0x20000000 + offset, getattr(state, name), width)
    for offset, value in ((0x4c0, 500), (0x4c4, 150), (0x4c8, 300),
                          (0x4e8, 1280), (0x4ec, 200), (0x4f0, 200), (0x4a0, position)):
        machine.set(0x20000000 + offset, value)


def compare(name, state, argument, position, lib=library):
    seed(state, position)
    drivers.clear()
    machine.calls.clear()
    args = [0x200004c0, argument] if name == "pid" else [argument]
    expected = machine.run(entries[name], *args)
    fn = getattr(lib, "ea9_factory_" + name)
    if name == "speed": actual = fn(state.direction, argument)
    elif name == "stop": actual = fn(ct.byref(state))
    elif name == "target": actual = fn(ct.byref(state), argument & 65535, position)
    else: actual = fn(ct.byref(state), position if name in ("control", "complete", "tick") else argument)
    if name in ("speed", "pid", "complete"):
        assert actual == expected, (name, argument, actual, expected)
    for field, (offset, width, signed) in fields.items():
        expected_field = machine.get(0x20000000 + offset, width, signed)
        assert getattr(state, field) == expected_field, (name, field, getattr(state, field), expected_field)
    if name in ("control", "tick"):
        if drivers:
            duty = state.duty
            expected_drivers = [(a, abs(duty)) for a in ((0x8e88, 0x8f28) if duty > 0 else (0x8ed8, 0x8f78))]
            assert drivers == expected_drivers, (name, drivers, expected_drivers)
        if name == "tick":
            expected_flags = (2 if machine.get(0x200004b8, 1) and not machine.get(0x200004b1, 1)
                              and original_armed and original_timeout == 300 else 0) | (1 if drivers else 0)
            assert actual == expected_flags, ("callback flags", actual, expected_flags)
    counts[name] += 1


def random_state():
    s = State()
    for name in ("accumulator", "previous_error", "previous_error2"):
        setattr(s, name, rng.getrandbits(32))
    s.target = rng.randrange(-32768, 32768)
    s.previous_position = rng.randrange(-32768, 32768)
    s.velocity = rng.randrange(-32768, 32768)
    s.duty = rng.randrange(-1280, 1281)
    s.timeout = rng.choice([0, 299, 300, 301, 65535])
    s.divider = rng.choice([0, 9, 10, 11, 255])
    s.direction = rng.choice([0, 1, 2, 3, 255])
    s.enabled, s.armed, s.completed = rng.randrange(2), rng.randrange(2), rng.randrange(3)
    return s


for name in entries:
    for _ in range(600):
        s = random_state()
        original_armed, original_timeout = s.armed, s.timeout
        compare(name, s, rng.randrange(-2**31, 2**31), rng.randrange(-2**31, 2**31))

for direction in (0, 1, 2, 3, 255):
    for error in (-2**31, -601, -600, -599, -301, -300, -299, -101, -100, -99,
                  -1, 0, 1, 99, 100, 101, 299, 300, 301, 599, 600, 601, 2**31-1):
        s = random_state(); s.direction = direction
        compare("speed", s, error, 0)

# History across disabled ticks, reversals, Stop and timeout, not isolated calls.
s = State()
for i in range(1500):
    position = 192 + (i * 17 % 5952)
    if i in (0, 61, 93, 203, 511, 710):
        compare("target", s, [4144, 5632, 4900][i % 3], position)
    if i in (80, 500): compare("stop", s, 0, position)
    original_armed, original_timeout = s.armed, s.timeout
    compare("tick", s, 0, position)
    compare("complete", s, 0, position)

# An intentionally wrong recovered gain must fail the same binary oracle.
mutated = cfg.output / "negative-control.c"
text = source.read_text()
assert text.count("150u * e") == 1
mutated.write_text(text.replace("150u * e", "151u * e").replace('"factory_af.h"',
                    '"' + str(source.with_suffix(".h")) + '"'))
bad = ct.CDLL(str(compile_library(mutated, "negative-control")))
bad.ea9_factory_pid.argtypes = library.ea9_factory_pid.argtypes
bad.ea9_factory_pid.restype = ct.c_int32
try:
    compare("pid", State(), 100, 0, bad)
except AssertionError:
    negative = "150→151 integral-gain mutation detected"
else:
    raise AssertionError("original-byte oracle did not detect altered gain")

report = {"result": "pass", "oracle": "retained original Thumb instructions",
          "inputSHA256": FIRMWARE_SHA256, "randomSeed": "0x240180", "cases": counts,
          "totalComparisons": sum(counts.values()), "negativeControl": negative,
          "compared": "13 controller fields; return values where defined; four final motor-driver calls",
          "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (source, source.with_suffix(".h"), Path(__file__))},
          "limitations": ["Synthetic RAM, not physical movement or camera AF",
                          "Final motor drivers stubbed; stop register writes use dummy RAM",
                          "Unicorn is a behavior oracle, not an ARMv6-M legality check",
                          "Does not validate hardware scheduling, homing or protocol state machine"]}
(cfg.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))

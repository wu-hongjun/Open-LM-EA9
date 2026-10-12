#!/usr/bin/env python3
"""Original Thumb sensor/initialization oracle; synthetic bytes, no devices.

No production firmware, shared research source or retained input is modified.
The lower SPI peripheral supplies explicit response bytes, not real sensing.
"""

import argparse
import csv
import ctypes
import hashlib
import json
from pathlib import Path
import platform
import random
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = HERE.parents[3]
sys.path.insert(0, str(BASE))

from config import DEFAULT_FIRMWARE, FIRMWARE_SHA256, configure  # noqa: E402


class Event(ctypes.Structure):
    _fields_ = [("kind", ctypes.c_uint32), ("args", ctypes.c_uint32 * 5)]


class Model(ctypes.Structure):
    _fields_ = [
        ("ram", ctypes.c_uint8 * 0xc00),
        ("events", Event * 16),
        ("event_count", ctypes.c_uint32),
        ("spi_word", ctypes.c_uint16),
        ("enable_status", ctypes.c_int32),
        ("transfer_status", ctypes.c_int32),
    ]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_value(data, off, width=2, signed=False):
    return int.from_bytes(data[off:off + width], "little", signed=signed)


def write_value(data, off, value, width=2):
    data[off:off + width] = (value & ((1 << (8 * width)) - 1)).to_bytes(
        width, "little"
    )


def compile_model(cfg, source, name):
    output = cfg.output / (name + cfg.library_suffix)
    command = [
        cfg.compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
        "-pedantic", *cfg.library_flags, "-I", str(BASE), "-I", str(HERE),
        str(source), str(BASE / "stock_model.c"), "-o", str(output),
    ]
    subprocess.run(command, check=True)
    lib = ctypes.CDLL(str(output))
    lib.sensor_run.argtypes = [
        ctypes.POINTER(Model), ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32
    ]
    lib.sensor_run.restype = ctypes.c_uint32
    lib.sensor_restore.argtypes = [
        ctypes.POINTER(Model), ctypes.POINTER(ctypes.c_uint8)
    ]
    lib.sensor_restore.restype = None
    return lib, command


def main():
    if sys.flags.optimize:
        raise SystemExit("Python optimization disables fixture assertions")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firmware", type=Path, default=DEFAULT_FIRMWARE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compiler")
    args = parser.parse_args()
    cfg = configure(args.firmware, args.output, args.compiler)

    import unicorn
    from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
    from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_SP
    from oracle import Machine

    if unicorn.__version__ != "2.1.4":
        raise SystemExit("Use the pinned unicorn==2.1.4 dependency")

    started = time.monotonic()
    lib, command = compile_model(cfg, HERE / "sensor_boundary.c", "sensor-boundary")
    model = Model()
    machine = Machine()
    machine.u.mem_map(0x60000000, 0x1000)
    rng = random.Random(0xEA91889A4)
    original_events = []

    def record(kind, *values):
        original_events.append((kind, *values, *([0] * (5 - len(values)))))

    def assertion(mm):
        a = mm.calls[-1]["args"]
        assert a[0] == 1, ("unexpected assertion", a)
        record(2, a[0], a[2])
        return 0

    def enable(mm):
        a = mm.calls[-1]["args"]
        assert a[0] == 0x20000868, a
        record(3, a[0], mm.enable_status & 0xffffffff)
        return mm.enable_status

    def delay(mm):
        a = mm.calls[-1]["args"]
        assert a[0] == 1, a
        record(4, a[0])
        return 0

    def transfer(mm):
        a = mm.calls[-1]["args"]
        assert a[0] == 0x20000868, a
        tx = mm.get(a[1])
        rx = mm.get(a[1] + 4)
        length = mm.get(a[1] + 8)
        assert length == 2, length
        tx_bytes = bytes(mm.u.mem_read(tx, length))
        assert tx_bytes == b"\x00\x00", tx_bytes.hex()
        mm.u.mem_write(rx, mm.spi_word.to_bytes(2, "big"))
        record(5, a[0], length, int.from_bytes(tx_bytes, "big"), mm.spi_word,
               mm.transfer_status & 0xffffffff)
        return mm.transfer_status

    def memory_write(u, kind, address, size, value, data):
        if address in (0x60000014, 0x60000018):
            record(1, address, value, size)
        elif 0x20000c00 <= address < 0x20004000:
            # All unmodeled SRAM writes must be the caller/callee stack.
            assert 0x20003d00 <= address and address + size <= 0x20003e00, (
                hex(address), size, hex(value)
            )

    machine.stubs.update({
        0x7174: assertion, 0x8008: enable, 0x60cc: delay, 0x8040: transfer
    })
    machine.u.hook_add(UC_HOOK_MEM_WRITE, memory_write)

    def seed(data=None, word=0, enable_status=0, transfer_status=0):
        if data is None:
            data = rng.randbytes(0xc00)
        ctypes.memmove(ctypes.addressof(model.ram), bytes(data), len(data))
        machine.u.mem_write(0x20000000, bytes(data))
        model.spi_word = machine.spi_word = word
        model.enable_status = machine.enable_status = enable_status
        model.transfer_status = machine.transfer_status = transfer_status

    def clear_events():
        model.event_count = 0
        machine.calls.clear()
        original_events.clear()

    def compare(entry, arg0=0, arg1=0, compare_return=False, library=lib):
        clear_events()
        expected = machine.run(entry, arg0, arg1) & 0xffffffff
        actual = library.sensor_run(ctypes.byref(model), entry, arg0, arg1)
        if compare_return:
            assert actual == expected, (
                hex(entry), hex(model.spi_word), actual, expected
            )
        got_ram = bytes(model.ram)
        expected_ram = bytes(machine.u.mem_read(0x20000000, 0xc00))
        assert got_ram == expected_ram, (
            hex(entry), [(hex(i), got_ram[i], expected_ram[i])
                         for i in range(0xc00) if got_ram[i] != expected_ram[i]][:12]
        )
        got_events = [(e.kind, *e.args) for e in model.events[:model.event_count]]
        assert got_events == original_events, (hex(entry), got_events, original_events)
        return actual

    counts = []
    seed(enable_status=-7, transfer_status=-7)
    for word in range(65536):
        model.spi_word = machine.spi_word = word
        result = compare(0x89a4, 1, compare_return=True)
        assert result == word >> 2
    counts.append({
        "entry": "0x89a4", "cases": 65536,
        "scope": "every two-byte response, selector 1, ignored stub statuses -7",
        "result": "pass"
    })

    selectors = [0, 1, 2, 0xffffffff, 0x80000000, 0x7fffffff]
    statuses = [0, -7, 1, -2147483648, 2147483647]
    for i in range(1024):
        seed(word=rng.randrange(65536), enable_status=statuses[i % 5],
             transfer_status=statuses[(i // 5) % 5])
        compare(0x89a4, selectors[i % len(selectors)], compare_return=True)
    counts.append({
        "entry": "0x89a4", "cases": 1024,
        "scope": "selector boundaries, synthetic unrelated RAM, ignored status pairs",
        "result": "pass"
    })

    for i in range(1024):
        seed()
        compare(0x8c64, rng.getrandbits(32), rng.getrandbits(32))
    counts.append({"entry": "0x8c64", "cases": 1024, "result": "pass"})

    for i in range(1024):
        seed(word=rng.randrange(65536), enable_status=statuses[i % 5],
             transfer_status=statuses[(i // 5) % 5])
        compare(0x8c80)
        state = bytes(model.ram)
        raw = model.spi_word >> 2
        assert read_value(state, 0x494) == raw
        assert read_value(state, 0x498) == raw
        assert read_value(state, 0x49c) == raw
        assert read_value(state, 0x49a) == 4096
        assert read_value(state, 0x4a0, 4) == 0
        assert state[0x4b0:0x4b2] == b"\x03\x00"
    counts.append({
        "entry": "0x8c80", "cases": 1024,
        "scope": "real filter initializer, real sensor reader and valid HAL wrappers",
        "result": "pass"
    })

    # Reset-time origin and later persisted origin are different boundaries.
    # All records below are generated; no physical unit's calibration is read.
    traces = []
    for initial_raw, saved_reference in [
        (5000, 4800), (100, 16000), (16000, 100), (8191, 8192),
        (0, 16383), (16383, 0), (12000, 12000), (8000, 65535)
    ]:
        seed(word=(initial_raw << 2) | 3, enable_status=-7, transfer_status=-7)
        compare(0x8c80)
        steps = [{"operation": "encoder initialization", "position": 4096,
                  "reference": read_value(model.ram, 0x49c)}]
        position = compare(0x8cc0, compare_return=True)
        assert position == 4096
        steps.append({"operation": "same sample before restore", "position": position})

        saved = bytearray(rng.randbytes(44))
        write_value(saved, 8, saved_reference)
        write_value(saved, 6, 2222)
        write_value(saved, 38, 50)
        saved[29] = 1  # Intentionally armed persisted state, overwritten defaults.
        clear_events()
        machine.u.mem_write(0x4100, bytes(saved))
        machine.run(0x8ae4)
        lib.sensor_restore(ctypes.byref(model), (ctypes.c_uint8 * 44).from_buffer_copy(saved))
        assert bytes(model.ram) == bytes(machine.u.mem_read(0x20000000, 0xc00))
        assert bytes(model.ram)[0x494:0x4c0] == bytes(saved)
        assert read_value(model.ram, 0x680) == 50
        assert read_value(model.ram, 0xd) == 4144
        assert model.ram[0x4b1] == 1
        assert original_events == [] and model.event_count == 0
        steps.append({"operation": "synthetic settings restore", "position": 2222,
                      "reference": saved_reference, "armed": 1,
                      "advertisedLowerBound": 4144})
        position = compare(0x8cc0, compare_return=True)
        steps.append({"operation": "same physical sample after restore", "position": position,
                      "relativeCounts": read_value(model.ram, 0x4a0, 4, signed=True)})
        traces.append({"initialRawSample": initial_raw, "savedReference": saved_reference,
                       "steps": steps})
    counts.append({
        "sequence": "initialize → same sample → synthetic restore → same sample",
        "sequences": len(traces), "steps": 4 * len(traces), "result": "pass"
    })

    # Execute the original main initialization prefix up to its first foreground
    # poll. Board/timer/motor boundaries are assumptions, not reproduced hardware.
    # This makes restore-after-initialize/stop ordering an instruction trace,
    # rather than only the manually composed fixture above.
    startup_traces = []
    for i, focal in enumerate([0, 15, 16, 24, 35, 50, 70, 65535]):
        data = bytearray(rng.randbytes(0xc00))
        data[0x530] = 0  # Ordinary BSS-cleared homing gate, not a reachability proof.
        saved = bytearray(rng.randbytes(44))
        saved_ref = 4800 + i
        write_value(saved, 8, saved_ref)
        write_value(saved, 6, 2222)
        write_value(saved, 38, focal)
        saved[29] = 1
        prefix = Machine()
        prefix.u.mem_map(0x60000000, 0x1000)
        prefix.u.mem_write(0x20000000, bytes(data))
        prefix.u.mem_write(0x4100, bytes(saved))
        prefix.spi_word = (5000 << 2) | 3
        prefix.enable_status = prefix.transfer_status = -7
        prefix.stubs.update(machine.stubs)
        for address in [0x5114, 0x8b20, 0x6080, 0x904c, 0x551c, 0x6090, 0x6dd4, 0x6120]:
            prefix.stubs[address] = 0

        def assumed_stop(mm):
            for offset, value in [(0x4b2, 0), (0x4b1, 0), (0x4b8, 1), (0x4be, 0)]:
                mm.set(0x20000000 + offset, value, 1)
            return 0

        checkpoints = []
        stop_at_first_poll = []

        def capture_checkpoint(mm, address):
            checkpoints.append({
                "entry": hex(address), "sample": mm.get(0x20000494, 2),
                "reference": mm.get(0x2000049c, 2),
                "position": mm.get(0x2000049a, 2),
                "armed": mm.get(0x200004b1, 1),
            })

        def prefix_trace(u, address, size, unused):
            if address in [0x8c80, 0x8e28, 0x8ae4, 0x8a8c]:
                capture_checkpoint(prefix, address)

        def reached_foreground(mm):
            capture_checkpoint(mm, 0x5dd4)
            stop_at_first_poll.append(True)
            mm.u.emu_stop()
            return 0

        prefix.stubs[0x8e28] = assumed_stop
        prefix.stubs[0x5dd4] = reached_foreground
        prefix.u.hook_add(UC_HOOK_MEM_WRITE, memory_write)
        prefix.u.hook_add(UC_HOOK_CODE, prefix_trace)
        original_events.clear()
        prefix.u.reg_write(UC_ARM_REG_SP, 0x20003e00)
        prefix.u.reg_write(UC_ARM_REG_LR, 0x1001)
        prefix.u.emu_start(0x8b71, 0x1000, count=100000)
        assert stop_at_first_poll == [True]
        assert [x["entry"] for x in checkpoints] == [
            "0x8c80", "0x8e28", "0x8ae4", "0x8a8c", "0x5dd4"
        ], checkpoints
        assert checkpoints[1]["reference"] == 5000
        assert checkpoints[1]["position"] == 4096
        assert checkpoints[2]["armed"] == 0
        assert checkpoints[3]["reference"] == saved_ref
        assert checkpoints[3]["position"] == 2222
        assert checkpoints[3]["armed"] == 1

        seed(data=data, word=prefix.spi_word, enable_status=-7, transfer_status=-7)
        model.event_count = 0
        lib.sensor_run(ctypes.byref(model), 0x8c80, 0, 0)
        for offset, value in [(0x4b2, 0), (0x4b1, 0), (0x4b8, 1), (0x4be, 0)]:
            model.ram[offset] = value
        lib.sensor_restore(ctypes.byref(model), (ctypes.c_uint8 * 44).from_buffer_copy(saved))
        lib.sensor_run(ctypes.byref(model), 0x8a8c, 0, 0)
        assert bytes(model.ram) == bytes(prefix.u.mem_read(0x20000000, 0xc00))
        expected_events = [(e.kind, *e.args) for e in model.events[:model.event_count]]
        expected_events.append((1, 0x60000018, 0x10000, 4, 0, 0))
        assert original_events == expected_events
        # The prefix did not set the gate; no later-path absence is inferred.
        assert model.ram[0x530] == 0
        startup_traces.append({"focalMM": focal, "checkpoints": checkpoints,
                               "homingGateAtFirstPoll": 0})
    counts.append({
        "entry": "0x8b70 bounded startup prefix", "cases": 8,
        "scope": "through first foreground poll, explicit board/timer/stop/delay cuts",
        "result": "pass"
    })

    source = (HERE / "sensor_boundary.c").read_text()
    old = "return (uint32_t)(m->spi_word >> 2);"
    wrong = "return (uint32_t)((((m->spi_word & 255u) << 8) | (m->spi_word >> 8)) >> 2);"
    assert source.count(old) == 1
    negative_source = cfg.output / "sensor-byte-order-negative.c"
    negative_source.write_text(source.replace(old, wrong))
    negative, _ = compile_model(cfg, negative_source, "sensor-byte-order-negative")
    seed(word=0x48d3)
    mismatch_detected = False
    try:
        compare(0x89a4, 1, compare_return=True, library=negative)
    except AssertionError as exc:
        mismatch_detected = True
        assert exc.args[0] == ("0x89a4", "0x48d3", 13522, 4660), exc.args
    assert mismatch_detected, "byte-order negative control was not detected"

    assert digest(cfg.firmware) == FIRMWARE_SHA256
    assert bytes(machine.u.mem_read(0x5000, len(cfg.rom))) == cfg.rom
    sources = [
        HERE / "sensor_boundary.c", HERE / "sensor_boundary.h", Path(__file__).resolve(),
        BASE / "config.py", BASE / "oracle.py", BASE / "stock_model.c",
        BASE / "stock_model.h", BASE / "requirements.txt",
    ]
    inventory = ROOT / "docs/reverse-engineering/whole-app-inventory.csv"
    entries = {"0x89a4", "0x8c64", "0x8c80", "0x6be4", "0x6c0c", "0x8b70"}
    provenance = []
    for row in csv.DictReader(inventory.open()):
        if row["address"] not in entries:
            continue
        ranges = []
        for item in row["body_ranges_inclusive"].split(";"):
            start, end = [int(x, 16) for x in item.split("-")]
            ranges.append({"start": hex(start), "inclusiveEnd": hex(end),
                           "SHA256": hashlib.sha256(
                               cfg.rom[start - 0x5000:end + 1 - 0x5000]
                           ).hexdigest()})
        provenance.append({"entry": row["address"], "evidenceID": row["evidence_id"],
                           "bodyBytes": int(row["body_bytes"]), "ranges": ranges})
    assert {p["entry"] for p in provenance} == entries
    report = {
        "researchDate": "2026-10-12", "inputSHA256": FIRMWARE_SHA256,
        "inputSize": len(cfg.rom), "inputUnchanged": True,
        "newModeledEntries": ["0x89a4", "0x8c64", "0x8c80"],
        "realOriginalInstructionsBelowSensorBoundary": ["0x6be4", "0x6c0c"],
        "composedExistingEntries": ["0x8ae4", "0x8cc0", "0x8a8c"],
        "boundedStartupPrefix": "0x8b70 until the first 0x5dd4 invocation",
        "casesSteps": sum(x.get("cases", x.get("steps", 0)) for x in counts),
        "results": counts,
        "originTraces": traces,
        "startupTraces": startup_traces,
        "originalRoutineProvenance": provenance,
        "originalInventorySHA256": digest(inventory),
        "negativeControl": {
            "change": "host model reverses the two supplied response bytes before shifting",
            "responseWord": "0x48d3", "originalReturn": 4660,
            "incorrectHostReturn": 13522, "mismatchDetected": mismatch_detected,
            "modifiedSourceSHA256": digest(negative_source),
        },
        "comparisonContract": [
            "All 3,072 persistent SRAM bytes compared after every call/step",
            "Return values compared for sample and composed position calls; void returns excluded",
            "Ordered MMIO writes/assertions/enable/delay/transfer events compared",
            "Caller/callee stack addresses normalized to transfer contents and count",
            "Other SRAM writes are checked to remain inside declared stack range",
            "No new IRQ, busy/error/power-loss/peripheral readiness semantics inferred",
        ],
        "stubBoundaries": [
            "0x7174 assertion recorder, condition must be true",
            "0x8008 SPI enable returns supplied status without peripheral effects",
            "0x8040 SPI transfer writes exactly two supplied bytes, then returns supplied status",
            "0x60cc busy-loop recorder; no measured duration",
            "GPIO writes use dummy memory at 0x60000014/0x60000018; electrical polarity unknown",
            "Settings restore reads a generated 44-byte record at emulated 0x4100",
            "Startup-only board/priorities/timer/PWM/handshake registration/delay cuts have no effects",
            "Startup-only stop cut writes four known software fields, excluding real motor register writes",
        ],
        "limitations": [
            "No real sensor model, peripheral polling, interrupts, timing, camera or optical qualification",
            "Ignored failure status cases still supply complete response bytes; incomplete transfers unmodeled",
            "All exhaustive response words share one synthetic RAM state; other states are finite seeded cases",
            "Selector 1 versus all other values is established; physical sensor/channel identification is unknown",
            "Startup prefix establishes order only under explicit driver cuts; no reset/IRQ equivalence",
            "Homing gate stays zero in the bounded prefix; later gate reachability remains unproved",
            "Unicorn Cortex-M0 selection is not ARMv6-M instruction-legality proof",
        ],
        "sourcesSHA256": {str(p.relative_to(ROOT)): digest(p) for p in sources},
        "environment": {
            "python": platform.python_version(), "unicorn": unicorn.__version__,
            "platform": sys.platform, "compiler": subprocess.run(
                [cfg.compiler, "--version"], capture_output=True, text=True, check=True
            ).stdout.splitlines()[0],
            "compilerFlags": ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic"],
        },
        "elapsedSeconds": round(time.monotonic() - started, 3),
        "usbReports": 0, "deviceEnumeration": False, "hardwareOperations": 0,
        "wholeFirmwareReconstruction": False, "cameraQualification": False,
    }
    destination = cfg.output / "sensor-boundary-validation.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"result": "pass", "casesSteps": report["casesSteps"],
                      "newModeledEntries": report["newModeledEntries"],
                      "report": str(destination), "negativeControlDetected": True}, indent=2))


if __name__ == "__main__":
    main()

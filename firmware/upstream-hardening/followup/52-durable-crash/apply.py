#!/usr/bin/env python3
"""Apply the source-pinned retained-RAM core to a private copy of AF4.0."""
import argparse
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    'startup_trace.c': '096eb2d63947e9e090de4a62f63a477e243b8439ca7108012b5dc6c9c829692d',
    'startup_trace.h': 'b5e17f9ff7f9583f895e4eea5b0bd32e8775ee43dec8f43e444f1fc0a58b1bd4',
    'ea9.ld': 'edf950a23a0401286fa722749fabd94504ae15d14d86460608c57f7323fe4849',
    'main.c': '5969645ba81e12444ad249409412168239a7fa36006ade55875f8882f2c82695',
    'servo.c': '6a291a61dec72a42ada5f143e5122eb903b32b42b59af22d90b49bd4456c38f5',
    'startup_trace_flash.c': '551ce09cc3b1eccf265b55d11b8f07221c377c3542738c994f3c94d702f4f282',
}

def apply(source):
    source = Path(source)
    for name, pin in PINS.items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest() == pin, name
    trace = source/'startup_trace.c'
    text = trace.read_text().replace('static struct {', 'static uint8_t crash_latched;\nstatic struct {', 1)
    old = '    memset(&ram,0,sizeof(ram));'
    assert text.count(old) == 1
    text = text.replace(old, old + '\n    crash_latched=0;')
    old = '        if (!erased(p)) r_next_page=(uint8_t)(i+1);'
    assert text.count(old) == 1
    text = text.replace(old, old + '\n        uint32_t crc; memcpy(&crc,p+60,4);\n        uint32_t actual=st_crc32(p,60);\n        if (!erased(p) && actual!=crc) crash_latched=1;\n        if (!memcmp(p,"E9S3",4) && p[4]==3 && p[5]==5 && p[7]==1\n            && p[6]==i+1 && p[8]==i && !p[9] && p[10]<=1 && (p[11]&96u)\n            && actual==crc) crash_latched=1;')
    trace.write_text(text + '\n' + (HERE/'retained.inc').read_text())
    header = source/'startup_trace.h'
    header.write_text(header.read_text() + '\n/* Foreground checkpoint; boot record before protocol activation. */\nvoid st_checkpoint(uint32_t ms);\nint st_boot_record(uint8_t reset_cause);\nvoid st_crash_boot(void);\nvoid st_watchdog_start(void);\nvoid st_watchdog_arm(void);\nvoid st_health(uint32_t now);\n')
    flash = source/'startup_trace_flash.c'
    flash.write_text(flash.read_text() + '\n#include "motor.h"\n' + (HERE/'watchdog.inc').read_text())
    main = source/'main.c'
    text = main.read_text()
    old = '\tboard_init_pins();\n\tst_init();'
    assert text.count(old) == 1
    text = text.replace(old, '\tst_crash_boot();\n\tboard_init_pins();')
    old = '\tdelay_init();'
    assert text.count(old) == 1
    text = text.replace(old, old + '\n\tst_watchdog_start();')
    old = '\tst_note(ST_STAGE,ST_REFERENCE,0,0,0,0,millis());'
    assert text.count(old) == 1
    text = text.replace(old, old + '\n\tst_watchdog_arm();')
    old = '\t\t/* Operand-only queries remain live after motion inhibition. */'
    assert text.count(old) == 1
    text = text.replace(old, '\t\tst_health(millis());\n' + old)
    main.write_text(text)
    servo = source/'servo.c'
    text = servo.read_text()
    old = '\t\tif (cfg->pump) {\n\t\t\tcfg->pump(pos);\n\t\t}\n'
    assert text.count(old) == 1
    text = text.replace(old, old + '\t\t/* Completed bounded sensor/control/protocol iteration. */\n\t\tst_health(millis());\n')
    servo.write_text(text)
    linker = source/'ea9.ld'
    text = linker.read_text()
    anchor = '    /* stack section */'
    assert text.count(anchor) == 1
    ram = '  ram      (rwx) : ORIGIN = 0x20000000, LENGTH = 0x00004000'
    assert text.count(ram) == 1
    text = text.replace(ram, '  ram      (rwx) : ORIGIN = 0x20000000, LENGTH = 0x00003fc0\n  retained (rw)  : ORIGIN = 0x20003fc0, LENGTH = 0x00000040')
    text = text.replace(anchor, '    /* Outside both startup BSS and the original bootloader stack. */\n    .noinit (NOLOAD) :\n    {\n        . = ALIGN(4);\n        KEEP(*(.noinit.st_retained))\n        . = ALIGN(4);\n    } > retained\n\n' + anchor)
    linker.write_text(text)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    apply(parser.parse_args().source)

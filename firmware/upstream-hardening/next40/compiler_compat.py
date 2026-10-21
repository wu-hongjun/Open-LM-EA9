"""Explicit test-only observation ABI adapter; no production/source mutation.

Some retained host harnesses link their own peripheral/trace mocks. Append weak
RAM-observer mocks only to clang executable links. This does not stand in for
the real v3 instrumentation/storage integration tests, run separately.
"""
import subprocess
from pathlib import Path


def install(path, headers):
    original = subprocess.run
    def run(command, *args, **kwargs):
        if (isinstance(command, (list, tuple)) and command
                and Path(str(command[0])).name == 'clang'
                and '-o' in command and '-c' not in command
                and str(path) not in map(str, command)):
            # Frozen trace mocks define st_note as a function. Use the equivalent
            # generic API here; exact macro/packed dispatch is tested in35/36.
            command = [*command, '-DSTARTUP_TRACE_IMPLEMENTATION=', '-I'+str(headers),
                '-include', str(Path(headers)/'motion_trace.h'), str(path)]
            # Historical tables use C static initialization; new tables restore
            # identical bytes in Reset_Handler. Host tests skip that handler.
            if any(Path(str(p)).name == 'emount_packets.c' and
                    'void ea9_packets_init(void)' in Path(str(p)).read_text()
                    for p in command):
                initializer = Path(path).with_name('packet_test_init.c')
                command.append(str(initializer))
        return original(command, *args, **kwargs)
    subprocess.run = run

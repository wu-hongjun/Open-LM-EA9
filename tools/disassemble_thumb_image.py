#!/usr/bin/env python3
"""Wrap a raw flash image in an analysis-only ELF and disassemble using Xcode.

This never executes the supplied firmware. Linear decoding also interprets data
as instructions; validate control flow before drawing conclusions.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--base', type=lambda s: int(s, 0), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.image.read_bytes()
    strings = b'\0.text\0.shstrtab\0'
    text_offset = 0x100
    str_offset = text_offset + len(data)
    section_offset = (str_offset + len(strings) + 3) & ~3
    header = struct.pack('<16sHHIIIIIHHHHHH',
                         b'\x7fELF\x01\x01\x01' + b'\0' * 9,
                         2, 40, 1, args.base, 0, section_offset, 0x05000000,
                         52, 0, 0, 40, 3, 2)
    image = header.ljust(text_offset, b'\0') + data + strings
    image = image.ljust(section_offset, b'\0') + b'\0' * 40
    image += struct.pack('<IIIIIIIIII', 1, 1, 6, args.base, text_offset, len(data), 0, 0, 2, 0)
    image += struct.pack('<IIIIIIIIII', 7, 3, 0, 0, str_offset, len(strings), 0, 0, 1, 0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    elf = args.output.with_suffix('.analysis.elf')
    elf.write_bytes(image)
    result = subprocess.run(['xcrun', 'llvm-objdump', '-d', '--triple=thumbv6m-none-eabi', str(elf)],
                            capture_output=True, text=True, check=True)
    annotated = []
    literals = []
    for line in result.stdout.splitlines():
        match = re.match(r'\s*([0-9a-f]+):.*\bldr\s+(r\d+), \[pc, #0x([0-9a-f]+)\]', line)
        if match:
            pc = int(match[1], 16)
            address = ((pc + 4) & ~3) + int(match[3], 16)
            offset = address - args.base
            if 0 <= offset <= len(data) - 4:
                value = struct.unpack_from('<I', data, offset)[0]
                line += f' ; literal[{address:#x}]={value:#010x}'
                literals.append({'instruction': pc, 'register': match[2], 'address': address, 'value': value})
        annotated.append(line)
    args.output.write_text('\n'.join(annotated) + '\n')
    args.output.with_suffix('.literals.json').write_text(json.dumps(literals, indent=2) + '\n')
    print(json.dumps({'image_bytes': len(data), 'base': args.base, 'literal_references': len(literals),
                      'disassembly': str(args.output)}))


if __name__ == '__main__':
    main()

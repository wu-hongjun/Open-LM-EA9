#!/usr/bin/env python3
"""Bounded offline, exact-ELF stack audit. No build, device, or network access.

This is an image-specific reviewed call graph, not a general ARM verifier.
Unknown call sites, frames, cycles, or changed inputs fail closed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DEFAULT_BUILD = ROOT / 'artifacts/private/absolute35a'
TOOL = ROOT / 'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-objdump'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(build, policy, budget):
    for name, digest in policy['pins'].items():
        require(sha(build / name) == digest, 'pin mismatch: ' + name)
    # Read-only byte equality, no binary output/extraction: bind both ELF load
    # segments to the already-existing raw and published image prefixes.
    elf = (build / 'hardened.elf').read_bytes()
    raw = (build / 'raw.bin').read_bytes()
    image = (build / 'contax-zeiss-50-f1-4.bin').read_bytes()
    require(elf[:7] == b'\x7fELF\x01\x01\x01', 'expected ELF32 little endian')
    phoff = struct.unpack_from('<I', elf, 28)[0]
    phsize, phnum = struct.unpack_from('<HH', elf, 42)
    coverage = 0
    for i in range(phnum):
        kind, offset, _, load, size, _, _, _ = struct.unpack_from('<8I', elf, phoff + i * phsize)
        if kind == 1 and size:
            start = load - 0x5000
            require(start == coverage and start + size <= len(raw), 'unexpected ELF load layout')
            require(elf[offset:offset + size] == raw[start:start + size], 'ELF/raw image mismatch')
            coverage += size
    require(coverage == len(raw) and image[:len(raw)] == raw, 'raw/published image mismatch')
    manifest = json.loads((build / 'manifest.json').read_text())
    require(len(manifest['sources']) == 46, 'source inventory changed')
    for name, digest in manifest['sources'].items():
        require(sha(build / name) == digest, 'source mismatch: ' + name)
    frames = {}
    usage = []
    for path in sorted(build.glob('*.su')):
        for line in path.read_text().splitlines():
            location, size, kind = line.split('\t')
            name = location.rsplit(':', 1)[1]
            require(kind == 'static', 'unbounded/dynamic frame: ' + name)
            require(name not in frames, 'ambiguous frame: ' + name)
            frames[name] = int(size)
            usage.append(dict(function=name, bytes=int(size), kind=kind))
    require(sorted(usage, key=lambda x: x['function']) ==
            sorted(manifest['compilerStackUsage'], key=lambda x: x['function']),
            'compiler stack usage differs from pinned manifest')
    def run(*args):
        return subprocess.check_output([str(TOOL), *args, str(build / 'hardened.elf')], text=True, timeout=30)
    symtext = run('-t')
    function_names = set()
    symbols = {}
    for line in symtext.splitlines():
        parts = line.split()
        if len(parts) >= 5 and re.fullmatch('[0-9a-f]{8}', parts[0]):
            symbols[parts[-1]] = int(parts[0], 16)
            if 'F' in parts[1:4]:
                function_names.add(parts[-1])
    asm = run('-d')
    graph = {}
    instructions = {}
    current = None
    for line in asm.splitlines():
        header = re.match(r'([0-9a-f]+) <(.+)>:', line)
        if header:
            current = header[2] if header[2] in function_names else None
            if current:
                graph[current] = set()
                instructions[current] = []
        insn = re.match(r'\s*([0-9a-f]+):\s+(?:[0-9a-f]{4} )*[0-9a-f]{4}\s+([^\t]+)\t?(.*)', line)
        if current and insn:
            instructions[current].append((int(insn[1], 16), insn[2].strip(), insn[3].strip()))
    reviewed_indirect = policy['indirectCalls']
    seen_indirect = set()
    calls = []
    for name, insns in instructions.items():
        normalized = re.sub(r'\.(isra|constprop)\.\d+$', r'.\1', name)
        if name not in frames and normalized in frames:
            frames[name] = frames[normalized]
        if name not in frames:
            require(name in policy['libraryFrames'], 'unknown library frame: ' + name)
            frames[name] = policy['libraryFrames'][name]
        for address, op, operand in insns:
            if op == 'blx' or (op == 'bx' and operand != 'lr'):
                key = f'{address:04x}'
                require(key in reviewed_indirect, f'unknown indirect call: {name}@{key}')
                record = reviewed_indirect[key]
                require(record['caller'] == name, 'indirect caller mismatch: ' + key)
                seen_indirect.add(key)
                targets = record['targets']
                for target in targets:
                    graph[name].add(target)
                calls.append(dict(address=key, caller=name, kind='reviewed-indirect', targets=targets))
            elif re.fullmatch(r'b(?:l|[a-z]{2})?(?:\.[nw])?', op):
                target = re.search(r'<([^+>]+)(?:\+[^>]+)?>', operand)
                require(target is not None, f'unknown branch: {name}@{address:x}')
                if target[1] != name or op == 'bl':
                    graph[name].add(target[1])
                    calls.append(dict(address=f'{address:04x}', caller=name, kind='direct', targets=[target[1]]))
            elif op in ('mov', 'add', 'ldr') and operand.startswith('pc,'):
                raise ValueError(f'unreviewed computed PC write: {name}@{address:x}')
    require(seen_indirect == set(reviewed_indirect), 'reviewed indirect inventory changed')
    # Tail branches are charged as full additional callee frames, intentionally
    # overestimating. Intra-function branches do not grow the call stack.
    memo = {}
    def bound(name, active=()):
        require(name not in active, 'recursive/reentrant call graph: ' + ' -> '.join((*active, name)))
        require(name in graph and name in frames, 'unresolved target/frame: ' + name)
        if name not in memo:
            children = [bound(child, (*active, name)) for child in sorted(graph[name])]
            child_size, chain = max(children, default=(0, []), key=lambda x: x[0])
            memo[name] = (frames[name] + child_size, [name, *chain])
        return memo[name]
    # Audit even unreachable functions, so newly reachable library code cannot
    # silently inherit an unchecked frame or an unknown indirect target.
    for name in sorted(graph):
        bound(name)
    reserve = symbols['_estack'] - symbols['_sstack']
    require(reserve == manifest['reservedStackBytes'] == 8192, 'stack reserve mismatch')
    require(symbols['_ezero'] - symbols['_srelocate'] == manifest['staticRAMBytes'] == 3072,
            'static RAM mismatch')
    roots = {name: dict(bytes=bound(name)[0], chain=bound(name)[1]) for name in
             ('Reset_Handler', 'main', 'EIC_Handler', 'SERCOM1_Handler', 'SysTick_Handler', 'Dummy_Handler')}
    # ARMv6-M core exception frame is 8 words; allow an extra alignment word
    # on every exception even when an interrupted frame is already aligned.
    exception_frame = 36
    foreground = roots['Reset_Handler']['bytes']
    default_irq = roots['EIC_Handler']['bytes'] + max(roots['SERCOM1_Handler']['bytes'], roots['SysTick_Handler']['bytes']) + 2 * exception_frame
    arbitrary_irq = sum(roots[n]['bytes'] for n in ('EIC_Handler', 'SERCOM1_Handler', 'SysTick_Handler')) + 3 * exception_frame
    # Four configurable priority levels, plus HardFault and NMI. Unused vectors
    # are Dummy_Handler; a dummy at the fourth level adds one frame, no C stack.
    all_vectors = arbitrary_irq + 3 * exception_frame
    total = foreground + all_vectors
    require(total <= budget, f'conditional bound {total} exceeds budget {budget}')
    require(total <= reserve, f'conditional bound {total} exceeds linker reserve {reserve}')
    return dict(
        status='PASS-CONDITIONAL-SOFTWARE-BOUND', imageSHA256=manifest['imageSHA256'],
        inputPins=policy['pins'], sourceHashesVerified=46, compilerFramesVerified=len(usage),
        functionCount=len(graph), callSiteCount=len(calls), indirectCallSites=len(seen_indirect),
        unresolvedCompiledEdges=[], unboundedCompiledFrames=[], recursiveComponents=[],
        libraryFramesWithoutSU=policy['libraryFrames'], roots=roots,
        maximumDefaultPriorityBytes=foreground + default_irq,
        maximumThreeActiveIRQBytes=foreground + arbitrary_irq,
        maximumAllVectorPriorityBytes=total, budgetBytes=budget, reservedStackBytes=reserve,
        staticRAMBytes=3072, stackStart=hex(symbols['_sstack']), stackTop=hex(symbols['_estack']),
        establishedEntryEvidence=policy['establishedEntryEvidence'],
        unknowns=policy['unknowns'], stackHighWaterMeasured=False,
        calls=calls, functionBounds={k: dict(frameBytes=frames[k], chainBytes=v[0], chain=v[1]) for k,v in sorted(memo.items())})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=DEFAULT_BUILD)
    parser.add_argument('--policy', type=Path, default=HERE / 'policy.json')
    parser.add_argument('--budget', type=int, default=8192)
    parser.add_argument('--require-unconditional', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        policy = json.loads(args.policy.read_text())
        result = audit(args.build, policy, args.budget)
        if args.require_unconditional:
            require(not result['unknowns'], 'unconditional safety unavailable: ' + '; '.join(result['unknowns']))
        if args.output:
            args.output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ('calls', 'functionBounds', 'inputPins', 'libraryFramesWithoutSU')}, indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

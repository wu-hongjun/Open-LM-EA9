#!/usr/bin/env python3
"""Root continuation: exact startup source under explicit EIC activation cuts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from apply import apply, scoped, host_api, omit_legacy_snapshot, omit_legacy_close_snapshot

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
source, out = a.source.resolve(), a.output.resolve()
assert out.is_relative_to(ROOT / 'artifacts/private')
manifest = json.loads((source / 'manifest.json').read_text())
assert manifest['imageSHA256'] == '04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632'
for name, digest in manifest['sources'].items(): assert sha(source / name) == digest, name
out.mkdir(exist_ok=False)
rows = []
for variant in ('frozen', 'proposal', 'proposal-lean', 'scoped', 'scoped-lean'):
    work = out / variant
    shutil.copytree(source / 'src', work / 'src')
    shutil.copytree(source / 'tools', work / 'tools')
    if variant.startswith('proposal'): apply(work)
    if variant.startswith('scoped'):
        scoped(work)
        host_api(work)
    if variant.endswith('lean'):
        omit_legacy_snapshot(work)
        omit_legacy_close_snapshot(work)
    em = work / 'src/emount.c'
    text = em.read_text()
    marker = 'static void on_cs_edge(int level)\n{'
    assert text.count(marker) == 1
    text = text.replace(marker, 'extern void handoff_hook(unsigned);\n' + marker)
    marker = '\t/* Admission is independent of the ordinary request mailbox.'
    assert text.count(marker) == 1
    text = text.replace(marker, '\thandoff_hook(2);\n' + marker)
    text += '\nunsigned startup_snapshot(uint8_t *out) {\n'
    text += ' if (!g_owner.pending) return 0;\n'
    text += ' const struct em_owned_request *r = &g_owner.slot[g_owner.active ^ 1u];\n'
    text += ' for (unsigned i=0;i<r->length;i++) out[i]=r->bytes[i]; return r->length;\n}\n'
    em.write_text(text)
    owner = work / 'src/em_owner.c'
    text = owner.read_text()
    marker = '    for (i = 0; i < n; i++) r->bytes[i] = p[i];'
    assert text.count(marker) == 1
    text = text.replace(marker, '    for (i = 0; i < n; i++) {\n'
        '        if (i == 4u) handoff_hook(3);\n'
        '        r->bytes[i] = p[i];\n    }')
    owner.write_text('extern void handoff_hook(unsigned);\n' + text)
    shim = work / 'tools/hosttest/shim.c'
    text = shim.read_text()
    marker = '\tvd_cb = vd_edge;\n}'
    assert text.count(marker) == 1
    text = text.replace(marker, '\tvd_cb = vd_edge;\n\thandoff_hook(1);\n}')
    if variant.startswith('scoped'):
        text = text.replace('\tcs_cb = cs_edge;', '\thandoff_eic_gate(0);\n\tcs_cb = cs_edge;')
        text = text.replace('void em_eic_start(void) {}', 'void em_eic_start(void) { handoff_eic_gate(1); }')
        text = 'extern void handoff_eic_gate(unsigned);\n' + text
    shim.write_text('extern void handoff_hook(unsigned);\n' + text)
    trace = (ROOT / 'firmware/upstream-diagnostic/tests/trace_host.c').read_text()
    trace = trace.replace('uint32_t st_lock(void) { return 0; }', '')
    trace = trace.replace('void st_unlock(uint32_t k) { (void)k; }', '')
    # Avoid forming an out-of-bounds intermediate pointer in the host-only shim.
    trace = trace.replace('memory+a-ST_FLASH_BASE', 'memory+(a-ST_FLASH_BASE)')
    trace += '\nvoid trace_read_bytes(uint8_t *p) { memcpy(p, memory, sizeof(memory)); }\n'
    (work / 'trace_host.c').write_text(trace)
    modules = ['emount', 'emount_packets', 'em_frame', 'em_owner', 'em_shutdown', 'startup_trace']
    cmd = ['clang', '-std=gnu99', '-O1', '-Wall', '-Wextra', '-Werror',
        '-DST_HOST', '-DEA9_NO_LOG', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
        '-I' + str(work / 'src'), '-I' + str(work / 'tools/hosttest'),
        str(HERE / 'test_handoff.c'), str(shim), str(work / 'trace_host.c'),
        *[str(work / 'src' / (name + '.c')) for name in modules], '-o', str(work / 'probe')]
    subprocess.run(cmd, check=True)
    for cut in (0, 1, 2, 3):
        dump = work / ('observed-' + str(cut) + '.bin')
        r = subprocess.run([str(work / 'probe'), str(cut), str(dump)], capture_output=True, text=True, timeout=10)
        expected = int(variant == 'frozen' and cut != 0)
        assert r.returncode == expected and not r.stderr, (variant, cut, r.stdout, r.stderr)
        row = json.loads(r.stdout)
        row['traceAndWireSHA256'] = sha(dump)
        rows.append(dict(variant=variant, **row))
        print(rows[-1])
for cut in (0, 1, 2, 3):
    assert (out / 'proposal' / ('observed-' + str(cut) + '.bin')).read_bytes() == (out / 'proposal-lean' / ('observed-' + str(cut) + '.bin')).read_bytes()
    assert (out / 'scoped' / ('observed-' + str(cut) + '.bin')).read_bytes() == (out / 'scoped-lean' / ('observed-' + str(cut) + '.bin')).read_bytes()
for name, digest in manifest['sources'].items(): assert sha(source / name) == digest, name
(out / 'result.json').write_text(json.dumps(dict(sourceManifestSHA256=sha(source / 'manifest.json'),
    imageSHA256=manifest['imageSHA256'], cases=rows, hardwareReportsSent=0), indent=2) + '\n')

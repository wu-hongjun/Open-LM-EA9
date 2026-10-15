#!/usr/bin/env python3
"""Source-bound startup handoff probes; synthetic peripherals, never hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def function(s, name):
    a = s.index(name)
    a = s.rfind('\n', 0, a) + 1
    i = s.index('{', a) + 1
    depth = 1
    while depth:
        if s[i] == '{': depth += 1
        if s[i] == '}': depth -= 1
        i += 1
    return s[a:i] + '\n'


def replace(s, a, b):
    assert s.count(a) == 1, a
    return s.replace(a, b)


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
p.add_argument('--candidate', type=Path, help='Also test the exact pinned final 3.6 source without reapplying a proposal')
args = p.parse_args()
source, out = args.source.resolve(), args.output.resolve()
assert out.is_relative_to(ROOT / 'artifacts/private')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
m = json.loads((source / 'manifest.json').read_text())
assert m['imageSHA256'] == '04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632'
for name, digest in m['sources'].items(): assert sha(source / name) == digest, name
candidate = args.candidate.resolve() if args.candidate else None
cm = None
if candidate:
    cm = json.loads((candidate / 'manifest.json').read_text())
    assert cm['imageSHA256'] == 'd8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f'
    assert sha(candidate / 'contax-zeiss-50-f1-4.bin') == cm['imageSHA256']
    assert cm['baseImageSHA256'] == m['imageSHA256']
    for name, digest in cm['sources'].items(): assert sha(candidate / name) == digest, name
out.mkdir(exist_ok=False)
applicator = HERE.parent / '26-compiled-irq/apply.py'
applicator_hash = sha(applicator)
scoped_variants = ['eic-gate', 'gate-start-too-early', 'gate-no-disable']
variants = ['frozen', 'proposal', 'unlock-too-early', *scoped_variants]
if candidate:
    variants.append('exact-final36')
    scoped_variants.append('exact-final36')
rows = []
for variant in variants:
    selected_source = candidate if variant == 'exact-final36' else source
    work = out / variant
    shutil.copytree(selected_source / 'src', work / 'src')
    shutil.copytree(selected_source / 'tools', work / 'tools')
    if variant not in ['frozen', 'exact-final36']:
        method = 'scoped' if variant in scoped_variants else 'apply'
        runpy.run_path(str(applicator))[method](work)
    if variant == 'gate-no-disable':
        path = work / 'src/em_eic.c'
        path.write_text(replace(path.read_text(), '\tNVIC_DisableIRQ(EIC_IRQn);\n', ''))
    em = work / 'src/emount.c'
    s = em.read_text()
    if variant == 'unlock-too-early':
        s = replace(s, '\n\tst_unlock(handoff_key);\n', '\n')
        s = replace(s, '\tst_note(ST_STAGE,ST_EIC,0,0,0,0,millis());',
                    '\tst_unlock(handoff_key);\n\tst_note(ST_STAGE,ST_EIC,0,0,0,0,millis());')
    if variant == 'gate-start-too-early':
        s = replace(s, '\n\tem_eic_start();\n', '\n')
        s = replace(s, '\tst_note(ST_STAGE,ST_EIC,0,0,0,0,millis());',
                    '\tem_eic_start();\n\tst_note(ST_STAGE,ST_EIC,0,0,0,0,millis());')
    s = replace(s, '\tem_eic_init(on_cs_edge, on_vd_edge);',
                '\tem_eic_init(on_cs_edge, on_vd_edge);')
    s = replace(s, '\tem_first_window_ms   = millis() - em_t_cs_first_high;',
                '\tem_first_window_ms   = millis() - em_t_cs_first_high;\n\thandoff_hook(4);')
    s = replace(s, '\t/* Admission is independent of the ordinary request mailbox.',
                '\thandoff_hook(2);\n\t/* Admission is independent of the ordinary request mailbox.')
    s = 'extern void handoff_hook(unsigned);\n' + s
    s += '''\nunsigned startup_snapshot(uint8_t *out) {
 if (!g_owner.pending) return 0;
 const struct em_owned_request *r = &g_owner.slot[g_owner.active ^ 1u];
 for (unsigned i=0;i<r->length;i++) out[i]=r->bytes[i]; return r->length;
}
unsigned startup_receiving(void) { return g_owner.receiving; }
'''
    em.write_text(s)
    owner = work / 'src/em_owner.c'
    owner.write_text('extern void handoff_hook(unsigned);\n' + replace(owner.read_text(),
        '    for (i = 0; i < n; i++) r->bytes[i] = p[i];',
        '    for (i = 0; i < n; i++) { if (i == 4u) handoff_hook(3); r->bytes[i] = p[i]; }'))
    # Keep production UART state and functions together. Only MMIO DATA reads
    # and write-one-to-clear operations are represented by host helper calls.
    uart = (selected_source / 'src/em_uart.c').read_text()
    a = uart.index('static volatile uint8_t  g_rx[')
    b = uart.index('static void em_uart_sync', a)
    selected = uart[a:b] + ''.join(function(uart, n) for n in [
        'SERCOM1_Handler(', 'em_uart_rx_reset(', 'em_uart_rx_len(', 'em_uart_rx_buf('])
    selected = replace(selected, '(uint8_t)EMSERCOM->USART.DATA.reg', 'probe_data()')
    selected = replace(selected, 'EMSERCOM->USART.INTFLAG.reg = SERCOM_USART_INTFLAG_ERROR;',
                       'probe_clear_error();')
    (work / 'uart.inc').write_text(selected)
    eic_source = (work / 'src/em_eic.c').read_text()
    setup = function(eic_source, 'em_eic_init(')
    setup = setup.rstrip()[:-1] + '\thandoff_hook(1);\n}\n'
    setup = replace(setup, 'EIC->INTFLAG.reg  = (1u << EM_EXTINT_BODY_CS) | (1u << EM_EXTINT_BODY_VD);',
                    'EIC->INTFLAG.reg &= ~((1u << EM_EXTINT_BODY_CS) | (1u << EM_EXTINT_BODY_VD));')
    if variant in scoped_variants:
        setup += function(eic_source, 'em_eic_start(')
    (work / 'eic_setup.inc').write_text(setup)
    host_sam = work / 'tools/hosttest/sam.h'
    host_sam.write_text(replace(host_sam.read_text(), 'struct host_reg8  PINCFG[32];',
                               'struct host_reg8  PINCFG[32];\n\tstruct host_reg8 PMUX[16];'))
    eic = function(eic_source, 'EIC_Handler(')
    for flag in ['CS', 'VD']:
        eic = replace(eic, f'EIC->INTFLAG.reg = (1u << EM_EXTINT_BODY_{flag});',
                      f'EIC->INTFLAG.reg &= ~(1u << EM_EXTINT_BODY_{flag});')
    (work / 'eic.inc').write_text(eic)
    # Retain unrelated host infrastructure, replacing receive and EIC functions
    # with production receive bodies and a one-pending-bit EIC model.
    shim = work / 'tools/hosttest/shim.c'
    s = shim.read_text()
    for text in ['volatile uint32_t em_rx_bytes;', 'volatile uint32_t em_rx_errors;',
                 'volatile uint16_t em_rx_status;', 'static uint8_t  rx[256];',
                 'static uint16_t rx_len;']:
        s = replace(s, text, '')
    for name in ['em_uart_rx_reset(', 'host_preload_rx(', 'em_uart_rx_len(', 'em_uart_rx_buf(',
                 'em_eic_init(', 'host_body_frame(', 'em_eic_receive_pending(']:
        s = replace(s, function(s, name).rstrip('\n'), '')
    if 'void em_eic_start(' in s:
        s = replace(s, function(s, 'em_eic_start(').rstrip('\n'), '')
    s = replace(s, 'static void (*cs_cb)(int level);', '')
    # Frame sync helper retains this pointer but is not used by our model.
    a = s.index('\t\t\tif (rx_len + win_len <= sizeof(rx)) {')
    b = s.index('\n\t\t\twin_len = 0;', a)
    s = s[:a] + '\t\t\thost_rx_load(win_buf, win_len);' + s[b:]
    s = 'extern void host_rx_load(const unsigned char *, unsigned);\n' + s
    shim.write_text(s)
    trace = (ROOT / 'firmware/upstream-diagnostic/tests/trace_host.c').read_text()
    for name in ['st_lock(', 'st_unlock(']: trace = replace(trace, function(trace, name).rstrip('\n'), '')
    (work / 'trace_host.c').write_text(trace)
    modules = ['emount', 'emount_packets', 'em_frame', 'em_owner', 'em_shutdown', 'startup_trace']
    subprocess.run(['clang', '-std=gnu99', '-O1', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-variable', '-DST_HOST', '-DEA9_NO_LOG',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-I' + str(work), '-I' + str(work / 'src'), '-I' + str(work / 'tools/hosttest'),
                    str(HERE / 'test.c'), str(shim), str(work / 'trace_host.c'),
                    *[str(work / 'src' / (n + '.c')) for n in modules], '-o', str(work / 'probe')], check=True)
    cases = [('valid', 'none', 0), ('empty', 'none', 0), ('noise', 'none', 0), ('truncated', 'none', 0)]
    cases += [('valid', 'rise', cut) for cut in (1, 2, 3)]
    cases += [(initial, event, 1) for initial in ('valid', 'empty', 'noise', 'truncated')
              for event in ('fall', 'vd', 'both', 'uart1', 'uart2', 'overflow', 'rise-uart1', 'rise-fall')]
    cases += [('valid', 'prior-mask', 3), ('tail-missing', 'tail', 1)]
    for initial, event, cut in cases:
        r = subprocess.run([str(work / 'probe'), initial, event, str(cut)],
                           capture_output=True, text=True, timeout=10)
        assert r.returncode == 0 and not r.stderr, (variant, initial, event, cut, r.stdout, r.stderr)
        row = dict(variant=variant, **json.loads(r.stdout))
        rows.append(row)
    # The single rising IRQ at the copy cut is a real failing control; no
    # second frame, equal-priority recursion, UART delivery, or timing claim.
    by = {(r['initial'], r['event'], r['cut']): r for r in rows if r['variant'] == variant}
    control = by['valid', 'rise', 3]
    assert control['wholeFirst'] == (variant in ['proposal', 'eic-gate', 'exact-final36']), control
    assert control['validOwned'] == (variant in ['proposal', 'eic-gate', 'exact-final36']), control
    for initial in ('empty', 'noise', 'truncated'):
        assert by[initial, 'none', 0]['ownedBytes'] == 0
    if variant == 'proposal':
        for cut in (1, 2, 3): assert by['valid', 'rise', cut]['wholeFirst']
        assert by['valid', 'prior-mask', 3]['maskAtReturn'] == 1
        assert by['valid', 'prior-mask', 3]['deliveriesAtReturn'] == 0
        assert by['valid', 'prior-mask', 3]['wholeFirst']
        # Delayed FIFO completion is explicitly NOT solved by serialization.
        assert by['tail-missing', 'tail', 1]['ownedBytes'] == 0
    if variant in ['eic-gate', 'exact-final36']:
        for cut in (1, 2, 3): assert by['valid', 'rise', cut]['wholeFirst']
        assert by['tail-missing', 'tail', 1]['wholeFirst']
        assert by['valid', 'overflow', 1]['uartErrors'] == 0
        assert by['valid', 'prior-mask', 3]['maskAtReturn'] == 1
        assert by['valid', 'prior-mask', 3]['deliveriesAtReturn'] == 0
    # Assert every matrix row, including invalid/noise and the deliberately
    # unsafe gate-start and unlock placement controls.
    for row in by.values():
        expected = row['initial'] == 'valid'
        if row['event'] == 'tail': expected = variant != 'proposal'
        if row['event'] in ['rise', 'rise-uart1'] and variant not in ['proposal', 'eic-gate', 'exact-final36']:
            expected = False
        if row['event'] == 'overflow' and variant == 'unlock-too-early': expected = False
        assert row['wholeFirst'] == expected, row
        errors = int(row['event'] == 'overflow' and variant in ['proposal', 'unlock-too-early'])
        assert row['uartErrors'] == errors, row
        delivery = int(row['event'] in ['rise', 'fall', 'vd', 'both', 'rise-uart1', 'rise-fall', 'prior-mask'])
        assert row['deliveries'] == delivery, row
        assert row['maskAtReturn'] == int(row['event'] == 'prior-mask'), row
for name, digest in m['sources'].items(): assert sha(source / name) == digest, name
if candidate:
    for name, digest in cm['sources'].items(): assert sha(candidate / name) == digest, name
    assert sha(candidate / 'contax-zeiss-50-f1-4.bin') == cm['imageSHA256']
assert sha(applicator) == applicator_hash
report = dict(imageSHA256=m['imageSHA256'], sourceManifestSHA256=sha(source / 'manifest.json'),
              cases=rows, testCount=len(rows), hardwareAccess=False, applicatorSHA256=applicator_hash,
              sourceFiles={n: sha(source / 'src' / n) for n in ['emount.c', 'em_uart.c', 'em_eic.c', 'em_owner.c']},
              fixtureFiles={p.name: sha(p) for p in HERE.iterdir() if p.suffix in ['.py', '.c']})
if candidate:
    report['exactCandidate'] = dict(imageSHA256=cm['imageSHA256'],
        manifestSHA256=sha(candidate / 'manifest.json'),
        sourceFiles={n: sha(candidate / 'src' / n) for n in ['emount.c', 'em_uart.c', 'em_eic.c', 'em_eic.h', 'em_owner.c']},
        testCount=41, reappliedProposal=False)
(out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(testCount=len(rows), result=str(out / 'result.json'))))

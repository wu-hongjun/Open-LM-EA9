"""Startup handoff workbench; only scoped delivery is an accepted proposal.

The original apply() full-PRIMASK variant is retained as a rejected comparison:
review 28 demonstrates that it delays a final UART byte past the rescue check.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

def apply(work: Path) -> None:
    work = work.resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private')
    path = work / 'src/emount.c'
    text = path.read_text()
    start = '\tem_eic_init(on_cs_edge, on_vd_edge);'
    end = '\n\tdelay_ms(50);\n\tPORT->Group[0].OUTCLR.reg = (1u << EM_PIN_LENS_CS);'
    assert text.count(start) == text.count(end) == 1
    text = text.replace(start,
        '\t/* Keep first-window ownership atomic across EIC activation and rescue. */\n'
        '\tuint32_t handoff_key = st_lock();\n' + start)
    text = text.replace(end, '\n\tst_unlock(handoff_key);\n' + end)
    path.write_text(text)

def omit_legacy_snapshot(work: Path) -> None:
    """Keep the live RX counter; omit one snapshot read only by disabled logging."""
    work = work.resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private')
    path = work / 'src/emount.c'
    text = path.read_text()
    marker = '\tem_rx_bytes_at_open = em_rx_bytes;'
    assert text.count(marker) == 1
    text = text.replace(marker, '#ifndef EA9_NO_LOG\n' + marker + '\n#endif')
    path.write_text(text)

def scoped(work: Path) -> None:
    """Defer EIC delivery until startup rescue completes; keep UART IRQs live."""
    work = work.resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private')
    path = work / 'src/em_eic.c'
    text = path.read_text()
    marker = '\tg_cs_edge = cs_edge;'
    assert text.count(marker) == 1
    text = text.replace(marker, '\t/* Own startup delivery before publishing callbacks. */\n'
        '\tNVIC_DisableIRQ(EIC_IRQn);\n' + marker)
    marker = '\tNVIC_EnableIRQ(EIC_IRQn);\n}'
    assert text.count(marker) == 1
    text = text.replace(marker, '}\n\nvoid em_eic_start(void)\n{\n'
        '\t/* Preserve any edge latched since setup; UART reception stayed live. */\n'
        '\tNVIC_EnableIRQ(EIC_IRQn);\n}')
    path.write_text(text)
    path = work / 'src/em_eic.h'
    text = path.read_text()
    marker = 'void em_eic_init(void (*cs_edge)(int level), void (*vd_edge)(void));'
    assert text.count(marker) == 1
    text = text.replace(marker, '/* Prepare peripheral/callbacks with EIC delivery disabled. UART stays live. */\n' + marker)
    marker = '\n#endif'
    assert text.count(marker) == 1
    text = text.replace(marker, '\n/* Arm delivery after the caller finishes first-window ownership. */\n'
        'void em_eic_start(void);\n' + marker)
    path.write_text(text)
    path = work / 'src/emount.c'
    text = path.read_text()
    marker = '\n\tdelay_ms(50);\n\tPORT->Group[0].OUTCLR.reg = (1u << EM_PIN_LENS_CS);'
    assert text.count(marker) == 1
    text = text.replace(marker, '\n\tem_eic_start();\n' + marker)
    path.write_text(text)

def omit_legacy_close_snapshot(work: Path) -> None:
    """The matching close snapshot also has only a disabled legacy page reader."""
    work = work.resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private')
    path = work / 'src/emount.c'
    text = path.read_text()
    marker = '\tem_rx_bytes_at_close = em_rx_bytes;'
    assert text.count(marker) == 1
    path.write_text(text.replace(marker, '#ifndef EA9_NO_LOG\n' + marker + '\n#endif'))

def host_api(work: Path) -> None:
    """Host boundary ABI only; production builds never link this shim."""
    work = work.resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private')
    path = work / 'tools/hosttest/shim.c'
    text = path.read_text()
    assert 'void em_eic_start(' not in text
    path.write_text(text + '\nvoid em_eic_start(void) {}\n')

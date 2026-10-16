"""Image-specific 3.7 semantic checks; no instruction execution or IRQ scheduler."""
import re
import struct


def require(ok, message):
    if not ok:
        raise ValueError(message)


def instructions(body):
    result = {}
    for line in body.splitlines():
        m = re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{4} )*[0-9a-f]{4})\s+([^\t]+)\t?(.*)', line)
        if m:
            result[int(m[1], 16)] = (m[3].strip(), m[4].split('@')[0].strip(), len(m[2].replace(' ', '')) // 2)
    return result


def expect(insns, address, op, arg, reason):
    require(insns.get(address, ())[:2] == (op, arg), reason + ': ' + hex(address))


def mask_inventory(bodies):
    return [dict(function=name, operation=op, operand=arg)
            for name, body in sorted(bodies.items())
            for op, arg, _ in instructions(body).values()
            if op in ('cpsid', 'cpsie', 'msr', 'mrs')]


def handoff_paths(insns):
    paths = []
    relevant = {'em_eic_init', 'on_cs_edge', 'em_uart_rx_reset', 'em_eic_start'}
    def walk(pc, calls, active):
        if pc == 0x5fd6:
            paths.append(tuple(calls)); return
        require(pc not in active and len(active) < 100, 'handoff suffix cycle')
        require(pc in insns, 'handoff leaves suffix')
        op, arg, width = insns[pc]
        if op == 'bl':
            target = re.search(r'<([^>]+)>', arg)
            require(target is not None, 'unknown handoff call')
            if target[1] in relevant:
                calls = calls + [target[1]]
        elif re.fullmatch(r'b(?:[a-z]{2})?(?:\.[nw])?', op):
            walk(int(arg.split()[0], 16), calls, active | {pc})
            if op in ('b', 'b.n', 'b.w'): return
        require(op not in ('bx', 'blx', 'pop') and not arg.startswith('pc,'), 'handoff unexpected control')
        walk(pc + width, calls, active | {pc})
    walk(0x5fa2, [], set())
    require(len(paths) == 3 and set(paths) == {
        ('em_eic_init', 'on_cs_edge', 'em_eic_start'),
        ('em_eic_init', 'em_uart_rx_reset', 'em_eic_start')}, 'handoff ordering/path mismatch')
    return [list(p) for p in paths]


def setup(insns, raw, symbols):
    for pc, op, arg in [
        (0x68ba, 'movs', 'r3, #128'), (0x68bc, 'movs', 'r4, #16'),
        (0x68be, 'ldr', 'r2, [pc, #164]'), (0x68c0, 'str', 'r4, [r2, r3]'),
        (0x68c2, 'dsb', 'sy'), (0x68c6, 'isb', 'sy'),
        (0x68ca, 'ldr', 'r3, [pc, #156]'), (0x68ce, 'str', 'r0, [r3, #0]'),
        (0x68d0, 'ldr', 'r3, [pc, #156]'), (0x68d2, 'str', 'r1, [r3, #0]'),
        (0x6984, 'movs', 'r2, #16'), (0x6986, 'ldr', 'r3, [pc, #4]'),
        (0x6988, 'str', 'r2, [r3, #0]')]:
        expect(insns, pc, op, arg, 'EIC setup mismatch')
    # IPR1 at NVIC+0x304, low byte replaced with 0x40: EIC priority 1.
    for pc, op, arg in [
        (0x694a, 'movs', 'r2, #193'), (0x694c, 'movs', 'r0, #255'),
        (0x694e, 'ldr', 'r1, [pc, #20]'), (0x6950, 'lsls', 'r2, r2, #2'),
        (0x6952, 'ldr', 'r3, [r1, r2]'), (0x6954, 'bics', 'r3, r0'),
        (0x6956, 'subs', 'r0, #191'), (0x6958, 'orrs', 'r3, r0'),
        (0x695a, 'str', 'r3, [r1, r2]')]:
        expect(insns, pc, op, arg, 'EIC priority mismatch')
    word = lambda a: struct.unpack_from('<I', raw, a - 0x5000)[0]
    require(word(0x6964) == word(0x698c) == 0xe000e100, 'NVIC base mismatch')
    require(word(0x6968) == symbols['g_cs_edge'] and word(0x6970) == symbols['g_vd_edge'], 'EIC callback stores mismatch')
    require(word(0x6084) == symbols['on_cs_edge'] | 1 and word(0x607c) == symbols['on_vd_edge'] | 1, 'EIC registration mismatch')


def vectors(raw, symbols):
    require(symbols['exception_table'] == 0x5000, 'vector base mismatch')
    words = struct.unpack_from('<45I', raw)
    reserved = {4,5,6,7,8,9,10,12,13,29,30,37,38,44}
    special = {0:'_estack', 1:'Reset_Handler', 15:'SysTick_Handler', 20:'EIC_Handler', 26:'SERCOM1_Handler'}
    for i, word in enumerate(words):
        expected = 0 if i in reserved else symbols[special.get(i, 'Dummy_Handler')] | (0 if i == 0 else 1)
        require(word == expected, 'vector target mismatch: ' + str(i))
    return dict(wordsVerified=45, initialMSP=hex(words[0]), NVMCTRL='Dummy_Handler')


def callbacks(raw, symbols):
    word = lambda a: struct.unpack_from('<I', raw, a - 0x5000)[0]
    for offset, name in [(48,'pump'),(52,'focus_retarget'),(56,'focus_abort')]:
        require(word(symbols['STOCK'] + offset) == symbols[name] | 1, 'STOCK binding mismatch')
    require(symbols['__preinit_array_start'] == symbols['__preinit_array_end'] == symbols['__init_array_start'], 'preinit mismatch')
    require(symbols['__init_array_end'] - symbols['__init_array_start'] == 4 and word(symbols['__init_array_start']) == symbols['frame_dummy'] | 1, 'init callback mismatch')
    require(word(0x50c8) == word(0x50cc) == word(0x50f0) == word(0x50f4) == symbols['__TMC_END__'], 'clone endpoints mismatch')
    require(word(0x50d0) == word(0x50f8) == 0, 'clone weak callback mismatch')
    require(word(0x8824) == symbols['powerdown_signal'] | 1 and word(0x8828) == symbols['motion_shutdown_inhibit'] | 1, 'main callback registration mismatch')
    require(word(0x56e0) == word(0x5ab0) == symbols['g_powerdown'], 'powerdown pointer provenance mismatch')
    require(word(0x59d4) == word(0x5a98) == symbols['g_shutdown_inhibit'], 'inhibit pointer provenance mismatch')
    require(word(0x69d4) == symbols['g_cs_edge'] and word(0x69dc) == symbols['g_vd_edge'], 'IRQ callback pointer provenance mismatch')


def terminal_order(bodies):
    fail = instructions(bodies['st_fail'])
    # All GPIO detach and release writes precede first clock/log call.
    for pc, op, arg in [
        (0x8e56,'cpsid','i'), (0x8e64,'strb','r1, [r3, r0]'),
        (0x8e6c,'strb','r1, [r3, r0]'), (0x8e74,'strb','r1, [r3, r0]'),
        (0x8e7e,'strb','r1, [r3, r0]'), (0x8e80,'str','r2, [r3, #4]'),
        (0x8e86,'str','r2, [r3, #24]'), (0x8e88,'bl','5368 <millis>'),
        (0x8e94,'bl','8a0c <st_record>'), (0x8eb2,'bl','8ab8 <st_flush>'),
        (0x8ec0,'bl','8c30 <st_terminal>')]:
        expect(fail, pc, op, arg, 'emergency cutoff/log ordering mismatch')
    require(not any(re.fullmatch(r'b(?:l|x|lx|[a-z]{2})?(?:\.[nw])?', op) for pc,(op,_,_) in fail.items() if 0x8e56 <= pc < 0x8e88), 'emergency cutoff bypass')
    power = instructions(bodies['powerdown_signal'])
    for pc, op, arg in [
        (0x7bea,'bl','6808 <em_uart_disable>'), (0x7bf6,'bl','8a0c <st_record>'),
        (0x7c2e,'bl','8ab8 <st_flush>'), (0x7c54,'bl','8c30 <st_terminal>'),
        (0x7c5e,'str','r2, [r3, #24]'), (0x7c6a,'bl','8c30 <st_terminal>'),
        (0x7c70,'bl','5374 <delay_ms>'), (0x7c7e,'bl','8c30 <st_terminal>')]:
        expect(power, pc, op, arg, 'shutdown terminal ordering mismatch')
    reset = instructions(bodies['Reset_Handler'])
    for pc, op, arg in [(0x5154,'push','{r4, r5, r6, lr}'),
        (0x5182,'bl','96c0 <memset>'), (0x5186,'bl','65e4 <ea9_packets_init>'),
        (0x5196,'str','r3, [r2, #8]'), (0x51de,'bl','96d0 <__libc_init_array>'),
        (0x51e2,'bl','84b8 <main>')]:
        expect(reset, pc, op, arg, 'startup packet ordering mismatch')


def source_gates(build):
    src = build / 'src'
    trace = (src/'startup_trace.c').read_text()
    flash = (src/'startup_trace_flash.c').read_text()
    main = (src/'main.c').read_text()
    em = (src/'emount.c').read_text()
    require('if (!allowed || r_failed || r_sealed || r_next_page>=16) return;' in trace, 'NVM allowed gate missing')
    require(trace.index('if (!allowed ||') < trace.index('r_sealed=1;') < trace.index('if (!append(&p))'), 'NVM gate ordering mismatch')
    require('if (!r_sealed) return;' in trace and 'p->slot=r_next_page++;' in trace, 'terminal seal/consume gate missing')
    require('uint32_t k=__get_PRIMASK(); __disable_irq(); return k;' in flash and '__set_PRIMASK(k);' in flash, 'PRIMASK restore contract missing')
    for function in ('st_summary','st_record'):
        body = trace.split('void '+function+'(',1)[1].split('\n}\n',1)[0]
        require('uint32_t key=st_lock();' in body and 'st_unlock(key);' in body, 'nested trace lock missing')
        require(not any(name in body for name in ('st_read_page','st_write_page','append(','st_flush(')), 'active trace NVM call')
    require(main.index('em_uart_disable();') < main.index('st_flush(1,'), 'shutdown UART/NVM ordering mismatch')
    require(em.index('if (g_shutdown_inhibit) g_shutdown_inhibit();') < em.index('em_trace(ST_SHUTDOWN_ADMIT') < em.index('st_note(ST_RX'), 'shutdown inhibit/admission ordering mismatch')
    # Full source pins bind the unabridged code; these checks document the
    # meaning of the reviewed callbacks and avoid an inventory-only approval.
    require(main.count('em_set_powerdown_handler(powerdown_signal);') == 1 and main.count('em_set_shutdown_inhibit_handler(motion_shutdown_inhibit);') == 1, 'callback registrar mismatch')
    require('struct servo_cfg sweep = STOCK;' in main and 'struct servo_cfg drv = STOCK;' in main, 'servo config provenance mismatch')
    require('trace_session = g_control_active ? g_control_session : g_session_generation;' in em and
            'em_trace(ST_TX_RETURN, trace_identity, trace_flags, trace_session);' in em, 'immutable TX identity mismatch')
    require('st_motion_finish(out->outcome);' in (src/'servo.c').read_text(), 'motion finish missing')
    return dict(ordinaryTraceNVM=False, nestedPRIMASKRestored=True, shutdownInhibitBeforeAdmission=True,
                callbackContext='No opaque ctx/handle ABI. cfg points to STOCK or scalar-modified local copies; focus callbacks use existing globals.')

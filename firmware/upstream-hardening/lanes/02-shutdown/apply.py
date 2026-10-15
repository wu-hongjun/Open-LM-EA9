"""Reviewable overlay for frozen 3.2. Caller owns copying sources/build linkage.
Apply before lane01 ownership. No filesystem mutations occur on import.
"""
def apply_source(source):
    def once(old,new):
        nonlocal source
        assert source.count(old)==1, ('shutdown anchor',old,source.count(old))
        source=source.replace(old,new,1)
    once('#include "startup_trace.h"','#include "startup_trace.h"\n#include "em_shutdown.h"')
    once('static uint8_t g_shutdown_enabled = 1;', '''static uint8_t g_shutdown_enabled = 1;
static struct em_shutdown g_shutdown;
static void (*g_shutdown_inhibit)(void);
uint8_t em_shutdown_requested(void) { return g_shutdown.state != EM_SD_IDLE; }
void em_set_shutdown_inhibit_handler(void (*fn)(void)) { g_shutdown_inhibit=fn; }''')
    start=source.index('static void em_shutdown_ack(void)')
    end=source.index('\nstatic void em_send_id(',start)
    source=source[:start]+'''/* First accepted complete request owns the echo. No ordinary RX, repeated
 * shutdown, or callback may replace it. The ISR's GPIO-only inhibit executes
 * before foreground can enter park, UART or the factory powerdown tail. */
static void em_shutdown_ack(void)
{
    if (!g_shutdown_enabled || !em_shutdown_begin(&g_shutdown)) return;
    /* No new shutdown motion: the legacy park callback can block for a
     * full servo timeout and has no established reference at this boundary. */
    em_transmit(g_shutdown.request,g_shutdown.length);
    em_shutdown_acked=1;
    em_t_shutdown=millis();
    g_shutdown.state=EM_SD_OFF;
    em_handshake_done=0;
    if (g_powerdown) g_powerdown();
}
''' +source[end:]
    once('\tem_frames_rx++;', '''	/* Admission is independent of the ordinary request mailbox. Even when
	 * foreground shutdown service is disabled, latch and inhibit immediately.
	 * A disabled callback must never make a valid shutdown disappear. */
	if (em_shutdown_accept(&g_shutdown,rx,n)) {
		g_status_due=0;
		g_reply_pending=0;
		em_focus_pending=0;
		if (g_shutdown_inhibit) g_shutdown_inhibit();
		return;
	}
	if (em_shutdown_requested()) return;
	/* Invalid/oversized shutdown must not enter the legacy reply path. */
	if (rx[3] == EM_CLASS_INIT && rx[5] == EM_ID_SHUTDOWN) return;
	em_frames_rx++;''')
    once('\tconst struct ea9_packet *p = find_packet(id);', '\tif (em_shutdown_requested()) return;\n\tconst struct ea9_packet *p = find_packet(id);')
    once('if (!g_status_due || em_shutdown_acked)', 'if (!g_status_due || em_shutdown_requested())')
    once('\tdelay_us(EM_LEAD_US);\n\tem_transmit(', '\tdelay_us(EM_LEAD_US);\n\tif (em_shutdown_requested()) return;\n\tem_transmit(')
    once('\tdelay_us(EM_STATUS_GAP_US);', '\tif (em_shutdown_requested()) return;\n\tdelay_us(EM_STATUS_GAP_US);\n\tif (em_shutdown_requested()) return;')
    once('\tg_in_poll = 1;\n', '''	g_in_poll = 1;
	if (em_shutdown_requested()) {
		em_shutdown_ack();
		g_in_poll=0;
		return;
	}
''')
    once('\tif (!em_focus_pending) {', '\tif (em_shutdown_requested() || !em_focus_pending) {')
    once('\tif (!g_query_n) {', '\tif (em_shutdown_requested() || !g_query_n) {')
    # Interrupted final reply cannot publish readiness over a shutdown latch.
    once('if (id == 0x0A) {', 'if (id == 0x0A && !em_shutdown_requested()) {')
    return source

def apply_header(source):
    return source + '''\n/* Shutdown latch remains set until physical reset. The inhibit handler is
 * invoked from RX ISR and must use bounded GPIO-only motor release. */
uint8_t em_shutdown_requested(void);
void em_set_shutdown_inhibit_handler(void (*fn)(void));
'''

def apply(work):
    """Mutate only caller-provided staged src directory or build root."""
    from pathlib import Path
    import shutil
    src=Path(work)
    if (src/'src').is_dir(): src=src/'src'
    p=src/'emount.c'; p.write_text(apply_source(p.read_text()))
    p=src/'emount.h'; p.write_text(apply_header(p.read_text()))
    for name in ('em_shutdown.c','em_shutdown.h'):
        shutil.copyfile(Path(__file__).resolve().parent/name,src/name)

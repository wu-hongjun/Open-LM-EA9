#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "em_frame.h"
#include "startup_trace.h"

void host_window_payload(const uint8_t *, uint16_t);
void host_body_frame(const uint8_t *, uint16_t);
unsigned startup_snapshot(uint8_t *);
void trace_read_bytes(uint8_t *);
extern int sent_n;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
uint32_t millis(void);
static uint8_t first[11], next[17];
static unsigned mask, pending, in_irq, armed, cut, deliveries, eic_disabled;

static void deliver(void)
{
    if (pending && !mask && !in_irq && !eic_disabled) {
        pending = 0; in_irq = 1; deliveries++;
        host_body_frame(next, sizeof(next));
        in_irq = 0;
    }
}
void handoff_eic_gate(unsigned enabled) { eic_disabled = !enabled; deliver(); }
uint32_t st_lock(void) { unsigned prior = mask; mask = 1; return prior; }
void st_unlock(uint32_t prior) { mask = prior; deliver(); }
void handoff_hook(unsigned point)
{
    if (armed && cut == point) { armed = 0; pending = 1; deliver(); }
}
static void seal(uint8_t *p, unsigned n, unsigned seq, unsigned id)
{
    unsigned sum = 0;
    p[0] = 0xf0; p[1] = n; p[3] = 2; p[4] = seq; p[5] = id;
    p[n - 1] = 0x55;
    for (unsigned i = 1; i < n - 3; i++) sum += p[i];
    p[n - 3] = sum; p[n - 2] = sum >> 8;
}
int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    cut = (unsigned)atoi(argv[1]); armed = cut != 0;
    seal(first, sizeof(first), 0x11, 8);
    next[6] = 0xa1; next[7] = 0xb2;
    seal(next, sizeof(next), 0x77, 1);
    st_init();
    host_window_payload(first, sizeof(first));
    em_init();
    uint8_t owned[256]; unsigned n = startup_snapshot(owned);
    struct em_frame_view view;
    int valid = em_frame_open(owned, n, &view) == EM_FRAME_OK;
    int whole = (n == sizeof(first) && !memcmp(owned, first, n))
             || (n == sizeof(next) && !memcmp(owned, next, n));
    int preserved = n == sizeof(first) && !memcmp(owned, first, n);
    int good = valid && whole && preserved && mask == 0
             && deliveries == (cut != 0) && !pending;
    em_poll();
    st_flush(1, millis(), 0, 0, 0, 0);
    uint8_t trace[1024]; trace_read_bytes(trace);
    FILE *dump = fopen(argv[2], "wb");
    if (!dump) return 2;
    if (fwrite(trace, 1, sizeof(trace), dump) != sizeof(trace)) return 2;
    for (int i = 0; i < sent_n; i++) {
        uint8_t length[2] = {(uint8_t)sent_len[i], (uint8_t)(sent_len[i] >> 8)};
        if (fwrite(length, 1, 2, dump) != 2) return 2;
        if (fwrite(sent[i], 1, sent_len[i], dump) != sent_len[i]) return 2;
    }
    if (fclose(dump)) return 2;
    printf("{\"cut\":%u,\"validOwnedFrame\":%s,\"wholeRequest\":%s,"
           "\"firstWindowPreserved\":%s,\"ownedBytes\":%u,"
           "\"deliveries\":%u,\"session\":%u,\"passes\":%s}\n",
           cut, valid ? "true" : "false", whole ? "true" : "false",
           preserved ? "true" : "false", n, deliveries,
           (unsigned)em_session_generation(), good ? "true" : "false");
    return !good;
}

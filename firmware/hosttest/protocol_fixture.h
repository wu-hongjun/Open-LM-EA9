/* Synthetic protocol test helpers; extracted from the archived handshake harness. */
/* Drive exact 4.2 application protocol C through its upstream host shim.
 * All packets here are synthetic; no A7C II transcript is represented. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "board.h"
#include "emount.h"

extern int sent_n, sent_overflow, host_baud_changes, host_baud_at_sent_n;
extern uint8_t sent[][512];
extern uint16_t sent_len[], host_baud;
extern const int *host_cs_seq;
extern unsigned host_cs_seq_n, host_cs_seq_i;
void host_body_frame(const uint8_t *, uint16_t);
void host_window_payload(const uint8_t *, uint16_t);
void host_preload_rx(const uint8_t *, uint16_t);
void host_set_cs_pin(int);
void host_frame_sync(void);

#define CHECK(cond) do { if (!(cond)) { \
    fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #cond); exit(2); \
} } while (0)

static uint16_t u16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }

static uint16_t checksum(const uint8_t *f, uint16_t len) {
    uint16_t sum = 0;
    for (uint16_t i = 1; i < len - 3; ++i) sum += f[i];
    return sum;
}

static uint16_t request(uint8_t *f, uint8_t id, const uint8_t *payload, uint16_t n) {
    uint16_t len = n + 9;
    memset(f, 0, len);
    f[0] = 0xf0; f[1] = (uint8_t)len; f[2] = (uint8_t)(len >> 8);
    f[3] = 2; f[4] = 0x29; f[5] = id;
    memcpy(f + 6, payload, n);
    uint16_t sum = checksum(f, len);
    f[len - 3] = (uint8_t)sum; f[len - 2] = (uint8_t)(sum >> 8); f[len - 1] = 0x55;
    return len;
}

static void reply(int idx, uint8_t cls, uint8_t id) {
    CHECK(idx < sent_n);
    const uint8_t *f = sent[idx];
    uint16_t len = sent_len[idx];
    CHECK(len >= 9 && len <= 512 && u16(f + 1) == len);
    CHECK(f[0] == 0xf0 && f[3] == cls && f[5] == id && f[len - 1] == 0x55);
    CHECK(u16(f + len - 3) == checksum(f, len));
}

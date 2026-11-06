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

static void status_pair(void) {
    int before = sent_n;
    host_frame_sync(); em_poll();
    CHECK(sent_n == before + 2);
    reply(before, 1, 0x05); reply(before + 1, 1, 0x06);
    CHECK(u16(sent[before] + 6) == 4544);
}

static void opener(int buffered_before_reset) {
    uint8_t f[64], offer[32] = {0};
    memset(offer, 0xff, 12); /* Synthetic broad offer, not a camera capture. */
    uint16_t n = request(f, 1, offer, sizeof(offer));
    if (buffered_before_reset) host_preload_rx(f, n);
    else host_window_payload(f, n);
    em_init(); em_poll();
    int first = sent_n;
    CHECK(first == !buffered_before_reset && !em_handshake_done);
    if (first) reply(0, 2, 1);
    host_frame_sync(); em_poll(); CHECK(sent_n == first);
    host_body_frame(f, n); em_poll();
    CHECK(sent_n == first + 1); reply(first, 2, 1);
    printf("{\"firstOpenerReplies\":%d,\"retryReplies\":1,\"statusBeforeReadiness\":0}\n", first);
}

static void missing_baud_edge(int missing_fall) {
    uint8_t f[16], speed[] = {2};
    uint16_t n = request(f, 0x0c, speed, sizeof(speed));
    em_init();
    CHECK(host_baud == EM_BAUD);
    host_body_frame(f, n);
    /* No pulse: either remain low or remain high throughout the wait. */
    host_set_cs_pin(missing_fall);
    em_poll();
    CHECK(sent_n == 1); reply(0, 2, 0x0c);
    CHECK(sent[0][6] == 1 && host_baud == EM_BAUD_FAST);
    CHECK(host_baud_changes == 1 && host_baud_at_sent_n == 1);
    printf("{\"acceptedSpeedReply\":1,\"switchedWithoutEdge\":true,\"missingEdge\":\"%s\"}\n",
           missing_fall ? "fall" : "rise");
}

static void declared_init(void) {
    /* ID order from the documented A7 IV selection rule for this mask.
     * Payloads are synthetic and the host does not model camera acceptance. */
    static const uint8_t ids[] = {1, 7, 0x0c, 0x0b, 0x3f, 0x3d, 8, 9, 0x0d, 0x10, 0x0a};
    static const uint8_t lengths[] = {32, 1, 1, 2, 1, 23, 8, 4, 1, 1, 16};
    static const int pulse[] = {0, 1, 1, 0};
    uint8_t f[64], pl[32];
    em_init();
    for (unsigned i = 0; i < sizeof(ids); ++i) {
        memset(pl, 0, sizeof(pl));
        switch (ids[i]) {
        case 1: memset(pl, 0xff, 12); break;
        case 0x0c: pl[0] = 2; host_cs_seq = pulse; host_cs_seq_n = sizeof(pulse)/sizeof(*pulse); break;
        case 0x3d: pl[0] = 0xbd; break;
        case 0x10: pl[0] = 0x1f; break;
        case 0x0a: pl[0] = 0xff; pl[1] = 0xff; pl[2] = 3; pl[8] = 0x3f; break;
        }
        uint16_t n = request(f, ids[i], pl, lengths[i]);
        CHECK(!em_handshake_done);
        host_body_frame(f, n); em_poll();
        CHECK(sent_n == (int)i + 1); reply((int)i, 2, ids[i]);
        if (ids[i] == 1) {
            /* Optional init IDs the A7 IV would request if declared. */
            static const uint8_t optional[] = {0x4e, 0x0c, 0x4c, 0x3f, 0x32, 0x3d, 0x5a};
            for (unsigned j = 0; j < sizeof(optional); ++j) {
                unsigned bit = optional[j] - 1;
                CHECK(!!(sent[i][6 + bit/8] & (1u << (bit%8))) == (j == 1 || j == 3 || j == 5));
            }
        }
        if (ids[i] == 7) CHECK(sent[i][6] == 1 && u16(sent[i] + 15) == 50496);
        if (ids[i] == 0x0c) CHECK(host_cs_seq_i == 4 && host_baud == EM_BAUD_FAST);
        if (ids[i] == 0x09) CHECK(sent[i][13] == 0 && sent[i][14] == 0);
        if (ids[i] == 0x10) CHECK(!(sent[i][6] & 1));
        if (ids[i] == 0x0a) CHECK(sent_len[i] == n && !memcmp(sent[i], f, n));
    }
    CHECK(em_handshake_done);
    status_pair();
    puts("{\"initReplies\":11,\"handshakeFlag\":true,\"statusFrames\":2,\"statusApertureAV\":4544}");
}

static void invalid_readiness(void) {
    const uint8_t f[] = {0xf0, 6, 0, 2, 0x29, 0x0a}; /* header only, no trailer */
    em_init();
    host_frame_sync(); em_poll(); CHECK(sent_n == 0 && !em_handshake_done);
    host_body_frame(f, sizeof(f)); em_poll();
    CHECK(sent_n == 0 && em_handshake_done);
    status_pair();
    puts("{\"readinessEchoes\":0,\"handshakeFlag\":true,\"statusFrames\":2}");
}

int main(int argc, char **argv) {
    CHECK(argc == 2);
    if (!strcmp(argv[1], "opener-buffered-at-open")) opener(1);
    else if (!strcmp(argv[1], "opener-after-reset")) opener(0);
    else if (!strcmp(argv[1], "baud-no-rise")) missing_baud_edge(0);
    else if (!strcmp(argv[1], "baud-no-fall")) missing_baud_edge(1);
    else if (!strcmp(argv[1], "declared-init")) declared_init();
    else if (!strcmp(argv[1], "invalid-readiness")) invalid_readiness();
    else CHECK(0);
    CHECK(!sent_overflow);
    return 0;
}

/* Synthetic frames exercise the production parser, responder and record writer. */
#include "probe.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static uint8_t flash[PROBE_END - PROBE_BASE];
static unsigned reads, writes;
static bool fail_read, fail_write;

bool probe_read_page(uint32_t addr, uint8_t page[PROBE_PAGE])
{
    assert(addr >= PROBE_BASE && addr < PROBE_END && addr % PROBE_PAGE == 0);
    ++reads;
    if (fail_read) return false;
    memcpy(page, flash + (addr - PROBE_BASE), PROBE_PAGE);
    return true;
}

bool probe_write_page(uint32_t addr, const uint8_t page[PROBE_PAGE])
{
    assert(addr >= PROBE_BASE && addr < PROBE_END && addr % PROBE_PAGE == 0);
    ++writes;
    for (unsigned i = 0; i < PROBE_PAGE; ++i) assert(flash[addr - PROBE_BASE + i] == 0xff);
    memcpy(flash + (addr - PROBE_BASE), page, fail_write ? 17 : PROBE_PAGE);
    return !fail_write;
}

static unsigned check_sum(const uint8_t *frame, unsigned n)
{
    unsigned sum = 0;
    for (unsigned i = 1; i < n - 3; ++i) sum += frame[i];
    return sum;
}

static void frame(uint8_t *b, unsigned n, uint8_t cls, uint8_t id)
{
    memset(b, 0, n);
    b[0] = 0xf0;
    b[1] = (uint8_t)n;
    b[2] = (uint8_t)(n >> 8);
    b[3] = cls;
    b[4] = 0x7e;
    b[5] = id;
    for (unsigned i = 6; i < n - 3; ++i) b[i] = (uint8_t)(i * 7);
    unsigned sum = check_sum(b, n);
    b[n - 3] = (uint8_t)sum;
    b[n - 2] = (uint8_t)(sum >> 8);
    b[n - 1] = 0x55;
}

static void exchange(struct probe *p, uint8_t id, uint8_t rx_size, uint16_t tx_size,
                     uint32_t now, enum probe_tx outcome)
{
    struct probe_request request;
    uint8_t b[PROBE_WINDOW], reply[PROBE_REPLY];
    frame(b, rx_size, 2, id);
    memset(b + rx_size, 0x77, 5); /* Padding is outside the declared frame. */
    probe_close(p, b, rx_size + 5, false, now);
    assert(probe_take(p, &request));
    assert(request.mark.id == id && request.mark.length == rx_size && request.mark.ms == now);
    assert(probe_reply(&request, reply) == tx_size);
    assert(reply[0] == 0xf0 && reply[1] == tx_size && reply[3] == 2 && reply[5] == id);
    assert(reply[tx_size - 1] == 0x55);
    assert(check_sum(reply, tx_size) == (unsigned)(reply[tx_size - 3] | reply[tx_size - 2] << 8));
    if (id == 0x0a || id == 0x16) assert(!memcmp(reply, b, tx_size));
    if (id == 0x0c) assert(reply[6] == 0);
    if (id == 0x01) {
        static const uint8_t stock[] = {0xff, 0x9f, 0x60, 0x7d, 0x80, 0x07, 0x08, 0x50};
        assert(!memcmp(reply + 6, stock, sizeof(stock)));
        for (unsigned i = 14; i < 38; ++i) assert(reply[i] == 0);
    }
    if (id == 0x07) {
        assert(reply[6] == 2 && reply[7] == 3 && reply[8] == 8 && reply[9] == 1);
        assert(reply[12] == 0x18 && reply[15] == 0xea && reply[16] == 0);
    }
    if (id == 0x3f) assert(!memcmp(reply + 7, "TECHART LM-EA9", 14));
    if (id == 0x34) assert(reply[6] == 0 && reply[7] == b[6] && reply[8] == b[7]);
    assert(probe_sent(p, &request, tx_size, outcome, now + 1) == (id == 0x16 && outcome == TX_RELEASED));
}

int main(int argc, char **argv)
{
    struct probe p = {0};
    struct probe_request request;
    uint8_t b[PROBE_WINDOW], status[PROBE_REPLY];
    assert(!probe_timeout(&p, 7999, 0));
    assert(probe_timeout(&p, 8000, 0) == FIRST_CLOSE_TIMEOUT);
    assert(!probe_persist(&p, FIRST_CLOSE_TIMEOUT, 8000) && !reads && !writes);
    probe_open(&p, true);
    p.flags |= BUS_READY;
    assert(!probe_timeout(&p, 4049, 50));
    assert(probe_timeout(&p, 4050, 50) == INACTIVITY);
    exchange(&p, 1, 41, 41, 51, TX_RELEASED);
    assert((p.flags & (FIRST_PREFIX | CAPABILITIES)) == (FIRST_PREFIX | CAPABILITIES));
    exchange(&p, 7, 10, 43, 55, TX_RELEASED);
    assert(p.flags & IDENTITY);
    exchange(&p, 0x0c, 10, 10, 60, TX_RELEASED);
    exchange(&p, 0x0b, 11, 11, 65, TX_RELEASED);
    exchange(&p, 0x3f, 10, 74, 70, TX_RELEASED);
    exchange(&p, 0x3d, 32, 72, 75, TX_RELEASED);
    exchange(&p, 8, 17, 210, 80, TX_RELEASED);
    exchange(&p, 9, 13, 20, 85, TX_RELEASED);
    exchange(&p, 0x0d, 10, 10, 90, TX_RELEASED);
    exchange(&p, 0x10, 10, 10, 95, TX_RELEASED);
    assert(p.paired_tx.id == 0x10);

    frame(b, 25, 2, 0x0a);
    probe_close(&p, b, 6, false, 100); /* November header-only failing control. */
    b[23] ^= 1;
    probe_close(&p, b, 25, false, 101);
    frame(b, 24, 2, 0x0a);
    probe_close(&p, b, 24, false, 102);
    frame(b, 25, 2, 0x0a);
    b[24] = 0;
    probe_close(&p, b, 25, false, 103);
    b[24] = 0x55;
    probe_close(&p, b, 25, true, 104); /* UART corrupted a framed-looking window. */
    assert(p.invalid == 5 && !probe_take(&p, &request));
    assert(p.last_rx.id == 0x10 && !(p.flags & FINAL_ECHO));

    exchange(&p, 0x0a, 25, 25, 105, TX_ABORTED);
    assert(p.last_rx.id == 0x0a && p.paired_tx.id == 0x10 && p.last_txc.id == 0x10);
    exchange(&p, 0x0a, 25, 25, 107, TX_SHIFTED);
    assert(p.last_txc.id == 0x0a && p.paired_tx.id == 0x10 && !(p.flags & FINAL_ECHO));
    probe_vd(&p);
    assert(!p.status_due);
    frame(b, 29, 1, 3);
    probe_close(&p, b, 29, false, 110);
    assert(!p.first_normal.length);
    exchange(&p, 0x0a, 25, 25, 111, TX_RELEASED);
    assert(p.flags & FINAL_ECHO);
    assert(p.paired_rx.ms == 111 && p.paired_tx.ms == 112);
    probe_vd(&p);
    assert(p.status_due && p.status_seq == 0x7f);
    assert(probe_status(5, p.status_seq, status) == 105);
    assert(status[4] == 0x7f && status[6] == 0 && status[7] == 0x12);
    assert(probe_status(6, p.status_seq, status) == 48 && status[0x20] == 0x6c);
    assert(status[8] == 0x30 && status[9] == 0x10 && status[0x1a] == 0x30 && status[0x1b] == 0x10);
    probe_close(&p, b, 29, false, 113);
    assert(p.first_normal.id == 3 && p.first_normal.ms == 113);
    exchange(&p, 0x34, 11, 32, 115, TX_RELEASED);
    exchange(&p, 0x16, 10, 10, 116, TX_RELEASED);
    assert(p.paired_rx.ms == 111 && p.paired_tx.ms == 112 && p.last_rx.ms == 111);
    assert(probe_timeout(&p, 4116, 50) == INACTIVITY);

    struct probe congested = {.flags = BUS_READY};
    frame(b, 41, 2, 1);
    probe_close(&congested, b, 41, false, 70);
    frame(b, 10, 2, 7);
    probe_close(&congested, b, 10, false, 80);
    assert(congested.drops == 1 && congested.last_rx.id == 7);
    assert(probe_take(&congested, &request) && request.mark.id == 1);
    probe_close(&congested, b, 10, false, 12000);
    assert(probe_timeout(&congested, 12050, 50) == INIT_DEADLINE);

    memset(flash, 0xff, sizeof(flash));
    fail_write = true;
    assert(!probe_persist(&p, TX_FAULT, 117) && writes == 1);
    fail_write = false;
    assert(probe_persist(&p, SHUTDOWN, 117) && writes == 2);
    assert(flash[4] == 1 && flash[17] == 0xff && flash[64 + 5] == 1);
    if (argc == 2) {
        FILE *out = fopen(argv[1], "wbx");
        assert(out && fwrite(flash, 1, sizeof(flash), out) == sizeof(flash));
        assert(fclose(out) == 0);
    }
    fail_read = true;
    assert(!probe_persist(&p, SHUTDOWN, 117) && writes == 2);
    fail_read = false;
    flash[sizeof(flash) - 1] = 0;
    assert(!probe_persist(&p, SHUTDOWN, 117) && writes == 2);
    /* A subsequent session can complete a handshake with full storage. */
    assert(probe_take(&congested, &request));

    exchange(&congested, 0x0a, 25, 25, 12051, TX_RELEASED);
    assert(congested.flags & FINAL_ECHO);
    puts("Startup probe parser, reply, timeout and persistence tests passed.");
}

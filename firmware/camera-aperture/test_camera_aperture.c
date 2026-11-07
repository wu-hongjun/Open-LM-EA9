/* Synthetic body requests through the production protocol callback and pump. */
#define main historical_probe_main
#include "../upstream-hardening/followup/58-november-handshake/probe.c"
#undef main
#include "emount_packets.h"
#include "reported_aperture.h"

extern uint32_t host_primask;
extern void (*host_tx_hook)(void);

static void seal(uint8_t *f, uint16_t n)
{
    uint16_t sum = checksum(f, n);
    f[n - 3] = (uint8_t)sum;
    f[n - 2] = (uint8_t)(sum >> 8);
}

static uint16_t make_offer(uint8_t *f, uint8_t id, uint16_t value)
{
    uint8_t payload[20] = {0};
    uint16_t n = request(f, id, payload, id == 3 ? 20 : 2);
    if (id == 3) {
        f[3] = 1;
        f[11] = (uint8_t)value;
        f[12] = (uint8_t)(value >> 8);
    } else {
        f[6] = (uint8_t)value;
        f[7] = (uint8_t)(value >> 8);
    }
    seal(f, n);
    return n;
}

static void coherent(uint16_t value)
{
    CHECK(u16(em_msg_05 + 6) == value && u16(em_msg_05 + 8) == value);
    CHECK(u16(em_msg_1B + 6) == value && u16(em_msg_1B + 8) == value);
    uint16_t optional = em_m08_aperture_on ? value : 0;
    CHECK(u16(em_msg_28 + 15) == optional && u16(em_msg_35 + 15) == optional);
    CHECK(em_msg_05[0x32] == 0x18 && em_msg_05[0x39] == 0x18 && em_msg_05[0x3a] == 0x48);
    CHECK(u16(em_msg_08 + 6) == 4608 && u16(em_msg_08 + 8) == 6144);
    CHECK(em_msg_05[10] == 0 && (em_msg_05[14] & 1));
    struct em_focus_cmd cmd;
    CHECK(!em_take_focus_cmd(&cmd));
}

static void capability(uint8_t bit)
{
    uint8_t f[32], payload[8] = {0xc2, bit};
    uint16_t n = request(f, 8, payload, sizeof(payload));
    host_body_frame(f, n);
    em_poll();
    CHECK(em_m08_aperture_on == !(bit & 0x80));
}

static void inject_during_tx(void)
{
    uint8_t f[64];
    uint16_t n = make_offer(f, 3, 5120); /* f/4 */
    host_body_frame(f, n);
    coherent(4608); /* Wire buffers keep their precomputed checksum/current pair. */
}

int main(void)
{
    em_init();
    CHECK(em_focal_mm10 == 580 && u16(em_msg_05 + 0x1e) == 580);
    CHECK(em_msg_08[0x16] == 0 && em_msg_08[0x17] == 0x58);
    CHECK(!memcmp(em_msg_3F + 7, "Zeiss Jena Biotar 58mm f/2", 24));
    coherent(4608);

    uint8_t f[64];
    uint8_t empty[1] = {0};
    uint16_t name_len = request(f, 0x3f, empty, 0);
    host_body_frame(f, name_len);
    em_poll();
    reply(sent_n - 1, 2, 0x3f);
    CHECK(!memcmp(sent[sent_n - 1] + 7, "Zeiss Jena Biotar 58mm f/2", 24));
    uint16_t n = make_offer(f, 0x1b, 5120);
    host_body_frame(f, n);
    coherent(4608); /* Receive IRQ only queues the metadata request. */
    int start = sent_n;
    em_poll();
    CHECK(sent_n == start + 1 && u16(sent[start] + 6) == 5120);
    reply(start, 2, 0x1b);
    coherent(5120);

    capability(0x61);
    coherent(5120);
    n = make_offer(f, 3, 4693); /* fractional third-stop value */
    host_body_frame(f, n);
    coherent(5120);
    em_poll();
    coherent(4693);
    capability(0xe1);
    coherent(4693);

    uint8_t payload[16] = {0xff, 0x7f};
    n = request(f, 0x0a, payload, sizeof(payload));
    host_body_frame(f, n);
    em_poll();
    CHECK(em_handshake_done);
    host_frame_sync();
    start = sent_n;
    em_poll();
    CHECK(sent_n == start + 2 && u16(sent[start] + 6) == 4693);
    reply(start, 1, 5);
    reply(start + 1, 1, 6);

    n = make_offer(f, 3, 4608);
    host_body_frame(f, n);
    em_poll();
    coherent(4608);
    host_tx_hook = inject_during_tx;
    host_frame_sync();
    start = sent_n;
    em_poll();
    CHECK(sent_n == start + 2 && u16(sent[start] + 6) == 4608);
    reply(start, 1, 5);
    coherent(4608);
    em_poll();
    coherent(5120);

    /* A complete valid envelope is required by each reporting input. */
    for (unsigned bad = 0; bad < 6; ++bad) {
        n = make_offer(f, 3, 5632);
        unsigned available = n;
        if (bad == 0) f[n - 3] ^= 1;
        if (bad == 1) f[n - 1] = 0;
        if (bad == 2) available = 13;
        if (bad == 3) { f[3] = 3; seal(f, n); }
        if (bad == 4) { f[1] = 0xff; f[2] = 0x01; }
        if (bad == 5) { f[0] = 0; }
        reported_aperture_offer(f, (uint16_t)available);
        reported_aperture_commit();
        coherent(5120);
    }
    n = make_offer(f, 0x1b, 5632);
    f[1] = 10;
    f[9] = 0x55;
    seal(f, 10);
    reported_aperture_offer(f, 10);
    reported_aperture_commit();
    coherent(5120);

    /* Check every unsigned operand and preserve complete fractional values. */
    uint16_t current = 5120;
    for (unsigned value = 0; value <= UINT16_MAX; ++value) {
        n = make_offer(f, 3, (uint16_t)value);
        reported_aperture_offer(f, n);
        reported_aperture_commit();
        if (value >= 4608 && value <= 6144) current = (uint16_t)value;
        coherent(current);
    }
    /* Window padding cannot supply or override the declared operand. */
    n = make_offer(f, 0x1b, 5120);
    memset(f + n, 0xaa, 32u - n);
    host_body_frame(f, 32);
    em_poll();
    coherent(5120);
    host_primask = 1;
    n = make_offer(f, 0x1b, 5120);
    reported_aperture_offer(f, n);
    reported_aperture_commit();
    CHECK(host_primask == 1);
    host_primask = 0;

    uint8_t opener[32] = {0};
    n = request(f, 1, opener, sizeof(opener));
    host_body_frame(f, n);
    em_poll();
    coherent(4608);
    em_set_shutdown_enabled(1);
    uint8_t none[1] = {0};
    n = request(f, 0x16, none, 1);
    host_body_frame(f, n);
    em_poll();
    CHECK(em_shutdown_acked);
    n = make_offer(f, 3, 5632);
    host_body_frame(f, n);
    em_poll();
    coherent(4608);
    n = request(f, 1, opener, sizeof(opener));
    host_body_frame(f, n);
    em_poll();
    CHECK(!em_shutdown_acked);
    coherent(4608);
    CHECK(host_baud == EM_BAUD && host_baud_changes == 0);
    CHECK(!sent_overflow);
    puts("Camera aperture requests, dynamic status, optical-field gating, malformed frames, TX interleaving, 65536 operands and IRQ-mask preservation passed.");
}

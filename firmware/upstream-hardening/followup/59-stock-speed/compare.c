/* Use the historical synthetic helpers without changing their pinned source. */
#define main historical_main
#include "../58-november-handshake/probe.c"
#undef main

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    if (!strcmp(argv[1], "opener-buffered-at-open") || !strcmp(argv[1], "invalid-readiness"))
        return historical_main(argc, argv);
    CHECK(!strcmp(argv[1], "pulse") || !strcmp(argv[1], "no-rise") || !strcmp(argv[1], "no-fall"));
    static const uint8_t ids[] = {1, 7, 0x0c, 0x0b, 0x3f, 0x3d, 8, 9, 0x0d, 0x10, 0x0a};
    static const uint8_t lengths[] = {32, 1, 1, 2, 1, 23, 8, 4, 1, 1, 16};
    static const int pulse[] = {0, 1, 1, 0};
    uint8_t f[64], payload[32];

    em_init();
    CHECK(host_baud == EM_BAUD);
    for (unsigned i = 0; i < sizeof(ids); ++i) {
        memset(payload, 0, sizeof(payload));
        if (ids[i] == 1) memset(payload, 0xff, 12);
        if (ids[i] == 0x0c) payload[0] = 2;
        if (ids[i] == 0x3d) payload[0] = 0xbd;
        if (ids[i] == 0x10) payload[0] = 0x1f;
        if (ids[i] == 0x0a) {
            payload[0] = payload[1] = 0xff;
            payload[2] = 3;
            payload[8] = 0x3f;
        }
        uint16_t n = request(f, ids[i], payload, lengths[i]);
        host_body_frame(f, n);
        if (ids[i] == 0x0c) {
            if (!strcmp(argv[1], "pulse")) {
                host_cs_seq = pulse;
                host_cs_seq_n = sizeof(pulse) / sizeof(*pulse);
            } else {
                host_set_cs_pin(!strcmp(argv[1], "no-fall"));
            }
        }
        em_poll();
        CHECK(sent_n == (int)i + 1);
        reply((int)i, 2, ids[i]);
        if (ids[i] == 0x0a) CHECK(sent_len[i] == n && !memcmp(sent[i], f, n));
    }
    CHECK(em_handshake_done);
    status_pair();
    CHECK(!sent_overflow);

    printf("{\"baud\":%u,\"changes\":%d,\"switchAfterReply\":%d,\"pulseReads\":%u,\"frames\":[",
           (unsigned)host_baud, host_baud_changes, host_baud_at_sent_n, host_cs_seq_i);
    for (int i = 0; i < sent_n; ++i) {
        printf("%s\"", i ? "," : "");
        for (uint16_t j = 0; j < sent_len[i]; ++j) printf("%02x", sent[i][j]);
        putchar('"');
    }
    puts("]}");
}

/* Finite receive-window / status scheduling probe, not a camera emulator.
 * Include the actual responder so its registered CS callback can be exercised
 * without changing the shared hardware shim or any production source. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../src/emount.c"

extern void host_body_frame(const uint8_t *, uint16_t);
extern void host_frame_sync(void), host_set_cs_pin(int);
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern int sent_n, sent_overflow;
void motor_emergency_release(void) {} /* No actuator is linked to this probe. */
static uint8_t inject_cs_in_gap;
void host_probe_delay_us(uint32_t us)
{
    if (inject_cs_in_gap && us == EM_STATUS_GAP_US) {
        inject_cs_in_gap = 0;
        host_set_cs_pin(1);
        on_cs_edge(1);
    }
}

static void request(uint8_t id, uint8_t sequence, uint16_t operand)
{
    uint8_t frame[11] = {0xf0, 11, 0, 2, sequence, id,
                        (uint8_t)operand, (uint8_t)(operand >> 8), 0, 0, 0x55};
    uint16_t sum = 0;
    for (unsigned i = 1; i < 8; ++i) sum += frame[i];
    frame[8] = (uint8_t)sum;
    frame[9] = (uint8_t)(sum >> 8);
    host_body_frame(frame, sizeof frame);
    em_poll();
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    uint8_t profile[256];
    FILE *file = fopen(argv[1], "rb");
    assert(file && !fseek(file, -256, SEEK_END));
    assert(fread(profile, 1, sizeof profile, file) == sizeof profile);
    fclose(file);
    assert(ea9_profile_load_from(profile));
    em_init();
    const uint8_t init[] = {1, 7, 0x0b, 8, 9, 0x0d, 0x10, 0x0a};
    for (unsigned i = 0; i < sizeof init; ++i) request(init[i], (uint8_t)i, 0);
    assert(em_handshake_done);

    /* Supply a CS rise and VD edge before that receive window has closed.
     * The shim does not measure UART occupancy, interrupt priority or time. */
    host_set_cs_pin(1);
    on_cs_edge(1);
    host_frame_sync();
    int before = sent_n;
    em_poll();
    int during_open = sent_n - before;
#ifdef EA9_PROBE_WINDOW_GUARD
    assert(during_open == 0); /* Deliberate host-only guard mutation. */
#else
    assert(during_open == 2 && sent[before][5] == 5 && sent[before + 1][5] == 6);
#endif
    host_set_cs_pin(0);
    on_cs_edge(0);
    host_frame_sync();
    before = sent_n;
    em_poll();
    assert(sent_n == before + 2 && sent[before][5] == 5 && sent[before + 1][5] == 6);

    /* An entrance-only guard is insufficient: the body may open its window
     * during the gap after status05 has completed but before status06.
     * Supply that callback from the instrumented host delay boundary. */
    inject_cs_in_gap = 1;
    host_frame_sync();
    before = sent_n;
    em_poll();
    assert(!inject_cs_in_gap && em_pin_level(EM_PIN_BODY_CS));
    assert(sent_n == before + 2 && sent[before][5] == 5 && sent[before + 1][5] == 6);
    host_set_cs_pin(0);
    on_cs_edge(0);

    /* Upstream a9 II ID order; synthetic, checksum-valid 11-byte requests.
     * This is NOT a complete legal A7C II request grammar or traffic replay.
     * Service every request before the next: the documented init-class
     * exchange is strict request/response, not nine unacknowledged requests. */
    const uint8_t capture[] = {0x0a, 0x0b, 0x1b, 0x28, 0x19, 0x19, 0x28, 0x0b, 0x0a};
    unsigned replies = 0;
    for (unsigned i = 0; i < sizeof capture; ++i) {
        before = sent_n;
        request(capture[i], (uint8_t)(0x30 + i), 0x1100);
        assert(sent_n == before + 1 && sent[before][5] == capture[i]);
        if (capture[i] == 0x1b) {
            assert(sent[before][6] == 0 && sent[before][7] == 0x11);
            assert(sent[before][8] == 0 && sent[before][9] == 0x11);
        }
        ++replies;
    }
    assert(!sent_overflow);
    for (int i = 0; i < sent_n; ++i) {
        const uint8_t *frame = sent[i];
        uint16_t length = sent_len[i], sum = 0;
        assert(frame[0] == 0xf0 && frame[1] == length && frame[2] == 0);
        for (unsigned j = 1; j < length - 3u; ++j) sum += frame[j];
        assert(frame[length - 3] == (sum & 255) && frame[length - 2] == (sum >> 8));
        assert(frame[length - 1] == 0x55);
    }
    printf("{\"statusFramesWhileReceiveWindowOpen\":%d,\"statusFramesAfterWindowClose\":2,"
           "\"status06FramesAfterReceiveOpensInGap\":1,"
           "\"syntheticCaptureReplies\":%u,\"allSentFramesChecksumValid\":true}\n",
           during_open, replies);
    return 0;
}

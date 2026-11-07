#include "protocol_fixture.h"
#include "emount_packets.h"

int main(void)
{
    /* The packet initializer still contains f/2: only the selected flash word
     * changes. This checks that startup commits it before any camera request. */
    CHECK(u16(em_msg_05 + 6) == 4608);
    em_init();
    CHECK(em_focal_mm10 == EXPECT_FOCAL && u16(em_msg_05 + 0x1e) == EXPECT_FOCAL);
    CHECK(u16(em_msg_05 + 6) == EXPECT_BOOT && u16(em_msg_1B + 6) == EXPECT_BOOT);
    CHECK(u16(em_msg_08 + 6) == 4224 && u16(em_msg_08 + 8) == 6400);
    uint8_t frame[64], payload[32] = {0};
    uint16_t n = request(frame, 0x3f, payload, 0);
    host_body_frame(frame, n); em_poll(); reply(sent_n-1, 2, 0x3f);
    CHECK(!strcmp((char *)sent[sent_n-1] + 7, EXPECT_NAME));
    payload[0] = 0; payload[1] = 20; /* f/4, AV 5120 */
    n = request(frame, 0x1b, payload, 2);
    host_body_frame(frame, n); em_poll(); reply(sent_n-1, 2, 0x1b);
    CHECK(u16(em_msg_05 + 6) == 5120);
    memset(payload, 0, sizeof(payload));
    n = request(frame, 1, payload, sizeof(payload));
    host_body_frame(frame, n); em_poll();
    CHECK(u16(em_msg_05 + 6) == EXPECT_BOOT && u16(em_msg_1B + 6) == EXPECT_BOOT);
    CHECK(!sent_overflow && host_baud == EM_BAUD && host_baud_changes == 0);
    puts("Selected focal/name, startup override, name checksum, camera change and session reset passed.");
}

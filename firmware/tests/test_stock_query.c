/* 0x34 is an opaque stock query, not a known aperture channel.
 * Test the production parser, snapshot, fixups and transmitter offline.
 * SPDX-License-Identifier: MIT */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "emount_packets.h"
#include "lens_aperture.h"
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern int sent_n, sent_overflow;
void host_body_frame(const uint8_t *, uint16_t);
static uint8_t original[32];
static void seal(uint8_t *f, uint16_t n)
{
    uint16_t sum = 0;
    for (unsigned i = 1; i <= n - 4u; ++i) sum += f[i];
    f[n - 3] = (uint8_t)sum; f[n - 2] = (uint8_t)(sum >> 8); f[n - 1] = 0x55;
}
static int query(uint16_t operand, uint8_t seq, uint16_t n)
{
    uint8_t q[256] = {0xf0,0,0,2,0,0x34};
    uint8_t expected[32];
    if (n < 9 || n > sizeof q) return 2;
    q[1] = (uint8_t)n; q[2] = (uint8_t)(n >> 8); q[4] = seq;
    if (n >= 11) { q[6] = (uint8_t)operand; q[7] = (uint8_t)(operand >> 8); }
    seal(q, n);
    sent_n = sent_overflow = 0;
    host_body_frame(q, n);
    /* A later normal frame replaces the hardware RX window, not the pending
     * init snapshot. Its aperture request must not change fixed policy. */
    uint8_t normal[29] = {0xf0,29,0,1,0xee,3};
    normal[11] = 0; normal[12] = 0x16; seal(normal, sizeof normal);
    host_body_frame(normal, sizeof normal); em_poll();
    if (n < 11) return sent_n != 0;
    if (sent_n != 1 || sent_len[0] != sizeof expected || sent_overflow) return 2;
    memcpy(expected, original, sizeof expected);
    expected[6] = 0; expected[7] = (uint8_t)operand; expected[8] = (uint8_t)(operand >> 8);
    seal(expected, sizeof expected);
    if (memcmp(sent[0], expected, sizeof expected)) return 1;
    if (lens_aperture_value() != 0x1100 || em_m03_aperture != 0x1600) return 3;
    return 0;
}
int main(int argc, char **argv)
{
    memcpy(original, &ea9_data[EA9_OFF_34], sizeof original);
    em_init(); em_set_aperture_range(0x1100, 0x1100); em_set_aperture(0x1100);
    if (memcmp(original, &ea9_data[EA9_OFF_34], sizeof original)) return 1;
    if (argc == 4) {
        int result = query((uint16_t)strtoul(argv[1], 0, 0),
                           (uint8_t)strtoul(argv[2], 0, 0),
                           (uint16_t)strtoul(argv[3], 0, 0));
        if (sent_n == 1) for (unsigned i = 0; i < sent_len[0]; ++i) printf("%02x", sent[0][i]);
        puts(""); return result;
    }
    if (argc != 1) return 2;
    const uint16_t words[] = {0,1,0x1100,0x1200,0x1600,0x0352,0xa55a,0xffff};
    const uint16_t sizes[] = {11,12,16,17,32,255,256};
    unsigned cases = 0;
    for (unsigned i = 0; i < sizeof words / sizeof *words; ++i)
        for (unsigned j = 0; j < sizeof sizes / sizeof *sizes; ++j) {
            int result = query(words[i], (uint8_t)(i * 37 + j), sizes[j]);
            if (result) return result;
            ++cases;
        }
    for (uint16_t n = 9; n <= 10; ++n) if (query(0xffff, 0xff, n)) return 1;
    puts("Opaque 0x34: 56 operand/length/sequence cases, 2 missing-payload cases; exact stock response bytes and consumed snapshot preserved.");
    return cases != 56;
}

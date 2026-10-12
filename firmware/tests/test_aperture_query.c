/* Fixed-policy regression: reject an unavailable f/8 iris change consistently
 * in both 0x1b and 0x34. Stock echoes this request; our fixed policy overrides it.
 * Run against both frozen 2.4 and current transport; frozen 2.4 must fail.
 * SPDX-License-Identifier: MIT */
#include <stdint.h>
#include <stdio.h>
#include "emount.h"
extern uint8_t sent[][256];
extern int sent_n;
void host_body_frame(const uint8_t *, uint16_t);
int main(void)
{
    uint8_t q[11] = {0xf0,11,0,2,0x71,0x1b,0,0x16,0,0,0x55};
    em_init(); /* register the actual receive-window callbacks */
    em_set_aperture_range(0x1100, 0x1100);
    em_set_aperture(0x1100);
    for (unsigned j = 0; j < 2; ++j) {
        uint16_t sum = 0;
        q[5] = j ? 0x34 : 0x1b;
        for (unsigned i = 1; i <= 7; ++i) sum += q[i];
        q[8] = (uint8_t)sum; q[9] = (uint8_t)(sum >> 8);
        host_body_frame(q, sizeof q); em_poll();
    }
    if (sent_n != 2 || sent[0][5] != 0x1b || sent[1][5] != 0x34) return 2;
    uint16_t initial = sent[0][6] | (uint16_t)sent[0][7] << 8;
    uint16_t capture = sent[1][7] | (uint16_t)sent[1][8] << 8;
    printf("f/8 request: 0x1b AV=0x%04x, 0x34 AV=0x%04x, fixed declaration=0x1100\n",
           initial, capture);
    return initial != 0x1100 || capture != 0x1100;
}

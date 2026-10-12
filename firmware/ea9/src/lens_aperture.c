/* Coherent aperture status/replies. No body request operates a passive iris.
 * SPDX-License-Identifier: MIT */
#include "lens_aperture.h"
#include "emount_packets.h"
static uint16_t declared = 0x1200; /* pre-profile fallback agrees with factory */
static void put(unsigned at, uint16_t value)
{
    ea9_data[at] = (uint8_t)value;
    ea9_data[at + 1] = (uint8_t)(value >> 8);
}
void lens_aperture_set(uint16_t av) { declared = av; }
uint16_t lens_aperture_value(void) { return declared; }
void lens_aperture_publish(uint8_t include_exif)
{
    put(EA9_OFF_05 + 6, declared);
    put(EA9_OFF_05 + 8, declared);
    ea9_data[EA9_OFF_05 + 10] = 0; /* iris never in transit */
    ea9_data[EA9_OFF_05 + 14] |= 1; /* iris at rest; preserve other flags */
    put(EA9_OFF_1B + 6, declared);
    put(EA9_OFF_1B + 8, declared);
    /* Factory 0x58a4 echoes the parsed request word in 0x1b and 0x34.
     * Our passive-iris policy deliberately overrides BOTH echoes: a body
     * request cannot change the physical iris or its fixed declaration. */
    ea9_data[EA9_OFF_34 + 6] = 0;
    put(EA9_OFF_34 + 7, declared);
    put(EA9_OFF_28 + 15, include_exif ? declared : 0);
}

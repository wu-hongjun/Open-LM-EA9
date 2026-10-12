/* Open LM-EA9 profile format v1. SPDX-License-Identifier: MIT */
#include "lens_profile.h"
#include "emount.h"
#include "emount_packets.h"

/* A personalized image replaces this entire row; zero is intentionally invalid. */
const volatile uint8_t ea9_profile_blob[EA9_PROFILE_BYTES]
#if !defined(__APPLE__)
    __attribute__((section(".ea9_profile"), used))
#endif
    = {0};
static const volatile uint8_t *active;
static uint16_t u16(const volatile uint8_t *p) { return p[0] | (uint16_t)p[1] << 8; }
static uint32_t u32(const volatile uint8_t *p) {
    return u16(p) | (uint32_t)u16(p + 2) << 16;
}
static int string_ok(const volatile uint8_t *p, unsigned n) {
    unsigned i; int ended = 0;
    if (!p[0]) return 0;
    for (i = 0; i < n; ++i) {
        if (!p[i]) ended = 1;
        else if (ended || p[i] < 32 || p[i] > 126) return 0;
    }
    return ended;
}
int ea9_profile_validate(const volatile uint8_t *p) {
    static const uint8_t magic[8] = {'E','A','9','L','E','N','S','1'};
    uint32_t crc = 0xffffffffu; unsigned i, b;
    for (i = 0; i < 8; ++i) if (p[i] != magic[i]) return 0;
    if (u16(p+8) != 1 || u16(p+10) != 256 || u16(p+12) < 10 ||
        u16(p+12) > 10000 || u16(p+14) < 4096 || u16(p+14) > 7168 ||
        u16(p+16) < u16(p+14) || u16(p+16) > 7680 ||
        (u16(p+14) - 4096) % 32 || (u16(p+16) - 4096) % 32 ||
        u16(p+18) != 234 || !u32(p+20) || u32(p+20) > 1000000 ||
        !string_ok(p+24,80) || !string_ok(p+104,64)) return 0;
    for (i = 168; i < 252; ++i) if (p[i]) return 0;
    for (i = 0; i < 252; ++i) {
        crc ^= p[i];
        for (b = 0; b < 8; ++b) crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320u : 0);
    }
    return (crc ^ 0xffffffffu) == u32(p+252);
}
int ea9_profile_load(void) {
    return ea9_profile_load_from(ea9_profile_blob);
}
int ea9_profile_load_from(const volatile uint8_t *p) {
    active = ea9_profile_validate(p) ? p : 0;
    return active != 0;
}
uint16_t ea9_profile_focal(void) { return active ? u16(active+12) : 0; }
void ea9_profile_apply(void) {
    unsigned i;
    if (!active) return;
    em_set_focal_length(u16(active+12));
    /* No electronic iris: this is fixed declared metadata, not the physical setting.
     * Maximum-aperture specification remains in the profile for the Mac UI. */
    em_set_aperture_range(u16(active+16), u16(active+16));
    em_set_aperture(u16(active+16));
    for (i = 0; i < 64; ++i) ea9_data[EA9_OFF_3F + 7 + i] = active[104+i];
}

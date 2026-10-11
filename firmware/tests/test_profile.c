/* Exercise the shipped profile decoder and emount transmitter. SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "lens_profile.h"
#include "emount.h"
#include "emount_packets.h"
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern int sent_n;
void host_body_frame(const uint8_t *, uint16_t);
void host_frame_sync(void);
static uint16_t u16(const uint8_t *p) { return p[0] | (uint16_t)p[1]<<8; }
static void checksum_ok(int n) {
    uint8_t *f = sent[n]; uint16_t len = sent_len[n], sum = 0; unsigned i;
    assert(f[0] == 0xf0 && u16(f+1) == len && f[len-1] == 0x55);
    for (i = 1; i <= len-4u; ++i) sum += f[i];
    assert(u16(f+len-3) == sum);
}
static int request(uint8_t id, uint8_t a0) {
    uint8_t r[11] = {0xf0,11,0,2,0x40,0,0,0,0,0,0x55}; int before = sent_n;
    uint16_t sum = 0; unsigned i;
    r[5] = id; r[6] = a0;
    for (i = 1; i <= sizeof(r)-4u; ++i) sum += r[i];
    r[sizeof(r)-3u] = (uint8_t)sum; r[sizeof(r)-2u] = (uint8_t)(sum >> 8);
    host_body_frame(r, sizeof(r)); em_poll();
    assert(sent_n == before+1); assert(sent[before][5] == id); checksum_ok(before);
    return before;
}
int main(int argc, char **argv) {
    uint8_t blob[256], corrupt[256], original05[12], original28[12]; uint16_t focal, aperture; int n, before; unsigned i;
    static const uint8_t handshake[] = {1,7,0x0b,8,9,0x0d,0x10,0x0a};
    assert(argc == 2); FILE *f = fopen(argv[1], "rb"); assert(f);
    assert(!fseek(f,EA9_PROFILE_ADDRESS - 0x5000u,SEEK_SET)); assert(fread(blob,1,256,f)==256); fclose(f);
    assert(ea9_profile_load_from(blob)); focal = u16(blob+12); aperture = u16(blob+16);
    /* Every single-byte corruption must fail before a handshake. */
    for (i = 0; i < 256; ++i) {
        memcpy(corrupt,blob,256); corrupt[i] ^= 1; assert(!ea9_profile_validate(corrupt));
    }
    memcpy(original05,ea9_data+EA9_OFF_05+0x26,12);
    memcpy(original28,ea9_data+EA9_OFF_28+0x11,12);
    em_init(); assert(ea9_profile_focal() == focal);
    assert(!memcmp(original05,ea9_data+EA9_OFF_05+0x26,12));
    assert(!memcmp(original28,ea9_data+EA9_OFF_28+0x11,12));
    assert(u16(ea9_data+EA9_OFF_05+0x1e)==focal);
    assert(u16(ea9_data+EA9_OFF_05+0x20)==focal);
    assert(u16(ea9_data+EA9_OFF_28+0x0a)==focal);
    assert(u16(ea9_data+EA9_OFF_28+0x0c)==focal);
    assert(u16(ea9_data+EA9_OFF_05+6)==aperture);
    assert(u16(ea9_data+EA9_OFF_05+8)==aperture);
    for (i = 0; i < sizeof(handshake); ++i) request(handshake[i],0);
    n = request(0x07,0); assert(sent[n][12] == EM_FW_VERSION_BCD && u16(sent[n]+15)==234);
    n = request(0x3f,0); assert(!memcmp(sent[n]+7,blob+104,64));
    n = request(0x28,0); assert(u16(sent[n]+10)==focal && u16(sent[n]+12)==focal);
    assert(u16(sent[n]+15)==aperture); /* message 0x08 explicitly enabled this copy */
    n = request(0x1b,0xff); assert(u16(sent[n]+6)==aperture && u16(sent[n]+8)==aperture);
    before = sent_n; host_frame_sync(); em_poll(); assert(sent_n == before+2);
    checksum_ok(before); checksum_ok(before+1);
    assert(sent[before][5]==5 && u16(sent[before]+6)==aperture && u16(sent[before]+30)==focal);
    assert(ea9_data[EA9_OFF_05+0x32] == em_aperture_to_descriptor(aperture));
    assert(ea9_data[EA9_OFF_05+0x3a] == em_aperture_to_descriptor(aperture));
    puts("profile corruption checks and transmitted focal/aperture/name/checksums: PASS");
    return 0;
}

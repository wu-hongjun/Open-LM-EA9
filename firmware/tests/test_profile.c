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
    n = request(0x34,0xa5);
    assert(sent[n][6] == 0 && u16(sent[n]+7) == 0xa5); /* opaque stock echo */
    /* A query with no payload is not an operand-bearing request. Do not
     * invent a reply from checksum bytes or an aperture declaration. */
    {
        uint8_t query[9] = {0xf0,9,0,2,0x71,0x34,0,0,0x55};
        uint16_t sum = 0;
        for (i = 1; i <= 5; ++i) sum += query[i];
        query[6] = (uint8_t)sum; query[7] = (uint8_t)(sum >> 8);
        before = sent_n; host_body_frame(query, sizeof query); em_poll();
        assert(sent_n == before);
    }
    /* Ask for a real different AV (f/8). Preserve the fixed reply and range. */
    {
        uint8_t iris[11] = {0xf0,11,0,2,0x40,0x1b,0x00,0x16,0,0,0x55};
        uint16_t sum = 0;
        for (i = 1; i <= sizeof(iris)-4u; ++i) sum += iris[i];
        iris[8] = (uint8_t)sum; iris[9] = (uint8_t)(sum >> 8);
        before = sent_n; host_body_frame(iris, sizeof iris); em_poll();
        assert(sent_n == before+1 && em_aperture_req == 0x1600);
        checksum_ok(before);
        assert(u16(sent[before]+6)==aperture && u16(sent[before]+8)==aperture);
        assert(u16(ea9_data+EA9_OFF_05+6)==aperture && u16(ea9_data+EA9_OFF_05+8)==aperture);
    }
    /* Per-frame 0x03 requests are recorded, never applied to passive iris
     * policy. 0x35 remains unsupported by this dispatcher. */
    {
        uint8_t body[29] = {0xf0,29,0,1,0x61,3};
        uint16_t sum = 0;
        body[11] = 0; body[12] = 0x16; body[28] = 0x55;
        for (i = 1; i <= 25; ++i) sum += body[i];
        body[26] = (uint8_t)sum; body[27] = (uint8_t)(sum >> 8);
        before = sent_n; host_body_frame(body, sizeof body); em_poll();
        assert(sent_n == before && em_m03_aperture == 0x1600);
        assert(u16(ea9_data+EA9_OFF_05+6)==aperture && u16(ea9_data+EA9_OFF_1B+6)==aperture);
        assert(u16(ea9_data+EA9_OFF_28+15)==aperture);
        body[3] = 2; body[5] = 0x35; sum = 0;
        for (i = 1; i <= 25; ++i) sum += body[i];
        body[26] = (uint8_t)sum; body[27] = (uint8_t)(sum >> 8);
        host_body_frame(body, sizeof body); em_poll(); assert(sent_n == before);
    }
    before = sent_n; host_frame_sync(); em_poll(); assert(sent_n == before+2);
    checksum_ok(before); checksum_ok(before+1);
    assert(sent[before][5]==5 && u16(sent[before]+6)==aperture && u16(sent[before]+30)==focal);
    assert(ea9_data[EA9_OFF_05+0x32] == em_aperture_to_descriptor(aperture));
    assert(ea9_data[EA9_OFF_05+0x3a] == em_aperture_to_descriptor(aperture));
    assert(ea9_data[EA9_OFF_05+0x34] == em_aperture_to_descriptor(aperture));
    /* Disable the optional copy, then begin a fresh session. It stays omitted
     * until the consumed 0x08 explicitly requests it again. */
    {
        uint8_t req[11] = {0xf0,11,0,2,0x40,8,0,0x80,0,0,0x55};
        uint16_t sum = 0;
        for (i = 1; i <= 7; ++i) sum += req[i];
        req[8] = (uint8_t)sum; req[9] = (uint8_t)(sum >> 8);
        host_body_frame(req, sizeof req);
        assert(em_m08_aperture_on); /* not published in the receive ISR */
        em_poll(); assert(!em_m08_aperture_on);
        n = request(0x28,0); assert(u16(sent[n]+15) == 0);
        request(8,0); n = request(0x28,0); assert(u16(sent[n]+15) == aperture);
        request(1,0); n = request(0x28,0); assert(u16(sent[n]+15) == 0);
        request(8,0); n = request(0x28,0); assert(u16(sent[n]+15) == aperture);
    }
    puts("profile corruption checks and transmitted focal/aperture/name/checksums: PASS");
    return 0;
}

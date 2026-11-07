#include "profile_bank.h"
#include <string.h>

uint16_t pb_u16(const uint8_t *p) { return p[0] | (uint16_t)p[1] << 8; }
uint32_t pb_u32(const uint8_t *p) { return pb_u16(p) | (uint32_t)pb_u16(p+2) << 16; }
static void put32(uint8_t *p, uint32_t v) {
    for (unsigned i=0; i<4; ++i) p[i]=(uint8_t)(v>>(8*i));
}
static int fill(const uint8_t *p, unsigned n, uint8_t v) {
    for (unsigned i=0; i<n; ++i) if(p[i]!=v) return 0;
    return 1;
}
uint32_t pb_crc32(const uint8_t *p, size_t n) {
    uint32_t c=~0u;
    while(n--) { c^=*p++; for(unsigned b=0;b<8;++b) c=(c>>1)^(0xedb88320u & (0u-(c&1u))); }
    return ~c;
}
static int text(const uint8_t *p, unsigned n) {
    unsigned i=0;
    while(i<n && p[i]) { if(p[i]<32 || p[i]>126) return 0; ++i; }
    return i>0 && i<n && fill(p+i,n-i,0);
}
const uint8_t *pb_profile(const uint8_t *p, uint8_t slot) { return p+64+256u*slot; }
int pb_validate_bank(const uint8_t *p, pb_bank *bank) {
    if(memcmp(p,"OLABANK1",8) || pb_u16(p+8)!=1 || pb_u16(p+10)!=64 ||
       pb_u16(p+12)!=256 || p[14]==0 || p[14]>PB_MAX_PROFILES || p[15]>=p[14] ||
       pb_u32(p+16)!=PB_BANK_BYTES || !fill(p+24,36,0) ||
       pb_crc32(p,60)!=pb_u32(p+60) || pb_crc32(p+64,PB_BANK_BYTES-64)!=pb_u32(p+20)) return PB_INVALID;
    for(unsigned i=0;i<p[14];++i) {
        const uint8_t *r=pb_profile(p,(uint8_t)i);
        uint16_t focal=pb_u16(r+12), nominal=pb_u16(r+14), boot=pb_u16(r+16);
        if(memcmp(r,"EA9LENS1",8) || pb_u16(r+8)!=1 || pb_u16(r+10)!=256 ||
           focal<10 || focal>10000 || nominal<4096 || nominal>6400 || nominal%32 ||
           boot<nominal || boot<4224 || boot>6400 || boot%32 || pb_u16(r+18)!=234 ||
           !pb_u32(r+20) || pb_u32(r+20)>1000000 || !text(r+24,80) || !text(r+104,64) ||
           !fill(r+168,84,0) || pb_crc32(r,252)!=pb_u32(r+252)) return PB_INVALID;
        for(unsigned j=0;j<i;++j) if(!memcmp(r+24,pb_profile(p,(uint8_t)j)+24,80)) return PB_INVALID;
    }
    unsigned used=64+256u*p[14];
    if(!fill(p+used,PB_BANK_BYTES-used,255)) return PB_INVALID;
    bank->count=p[14]; bank->default_slot=p[15]; bank->fingerprint=pb_u32(p+20);
    return PB_OK;
}
void pb_encode_setting(uint8_t *p, const pb_bank *b, const pb_setting *s) {
    memset(p,0,64); memcpy(p,"OLASET1!",8); p[8]=1; p[10]=64;
    put32(p+12,b->fingerprint); put32(p+16,s->sequence); put32(p+20,s->generation);
    p[24]=s->slot; put32(p+56,pb_crc32(p,56)); memcpy(p+60,"DONE",4);
}
static int decode(const uint8_t *p, const pb_bank *b, pb_setting *s) {
    if(memcmp(p,"OLASET1!",8) || pb_u16(p+8)!=1 || pb_u16(p+10)!=64 ||
       pb_u32(p+12)!=b->fingerprint || !pb_u32(p+16) || p[24]>=b->count ||
       !fill(p+25,31,0) || memcmp(p+60,"DONE",4) ||
       pb_crc32(p,56)!=pb_u32(p+56)) return PB_INVALID;
    s->sequence=pb_u32(p+16); s->generation=pb_u32(p+20); s->slot=p[24];
    return PB_OK;
}
int pb_load(const pb_bank *b, const pb_io *io, pb_setting *out) {
    uint8_t page[64], newest[64]; pb_setting s; int found=0;
    for(unsigned i=0;i<PB_JOURNAL_ROWS;++i) {
        if(io->read(io->context,i*256,page,64)) return PB_IO;
        if(decode(page,b,&s)!=PB_OK) continue;
        if(found && s.sequence==out->sequence && memcmp(page,newest,64)) return PB_INVALID;
        if(!found || s.sequence>out->sequence) {
            *out=s; out->row=(uint8_t)i; memcpy(newest,page,64); found=1;
        }
    }
    /* Never erase unknown/nonblank storage, or silently reinitialize lost state. */
    return found ? PB_OK : PB_INVALID;
}
int pb_store(const pb_bank *b, const pb_io *io, uint8_t slot, uint32_t generation, pb_setting *out) {
    pb_setting old; uint8_t page[64], verify[64];
    int result=pb_load(b,io,&old); if(result!=PB_OK) return result;
    if(slot>=b->count || generation<old.generation) return PB_INVALID;
    if(slot==old.slot && generation==old.generation) { *out=old; return PB_UNCHANGED; }
    if(generation==old.generation) return PB_INVALID; /* no replay/reuse of a consumed request */
    if(old.sequence==UINT32_MAX) return PB_EXHAUSTED;
    unsigned next=(old.row+1u)%PB_JOURNAL_ROWS;
    /* Always erase, including after a reset. FF cannot prove that a page has
     * never been programmed. One program per erase avoids that ambiguity and
     * stays below the SAMD21 consecutive-write limit even after a torn program. */
    if(io->erase(io->context,next*256)) return PB_IO;
    for(unsigned i=0;i<4;++i) {
        if(io->read(io->context,next*256+i*64,page,64) || !fill(page,64,255)) return PB_IO;
    }
    pb_setting wanted={old.sequence+1,generation,slot,(uint8_t)next};
    pb_encode_setting(page,b,&wanted);
    if(io->program(io->context,next*256,page) || io->read(io->context,next*256,verify,64) ||
       memcmp(page,verify,64)) return PB_IO;
    *out=wanted; return PB_OK;
}
int pb_boot(const uint8_t *bytes, const uint8_t *metadata, const pb_io *io, pb_setting *out) {
    pb_bank bank; int r=pb_validate_bank(bytes,&bank); if(r!=PB_OK) return r;
    r=pb_load(&bank,io,out); if(r!=PB_OK) return r;
    const uint8_t *m=metadata+PB_MAILBOX_OFFSET;
    if(memcmp(m,"OLAC",4) || m[4]!=1 || m[5]>=bank.count || !fill(m+6,2,0) ||
       pb_u32(m+8)!=bank.fingerprint || !fill(m+16,4,0) ||
       pb_crc32(m,20)!=pb_u32(m+20) || memcmp(m+24,"OK",2) ||
       pb_u32(m+12)<=out->generation) return PB_UNCHANGED;
    pb_setting selected;
    r=pb_store(&bank,io,m[5],pb_u32(m+12),&selected);
    if(r<0) return PB_PENDING; /* keep last committed selection; pending is not applied */
    *out=selected; return PB_OK;
}

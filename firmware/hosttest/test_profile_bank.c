/* Actual portable production journal/boot code with synthetic flash only. */
#include "profile_bank.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"%d: %s\n",__LINE__,#x); exit(2); } } while(0)
static uint8_t bank_bytes[PB_BANK_BYTES], metadata[58];
static pb_bank bank;
typedef struct {
    uint8_t bytes[PB_JOURNAL_BYTES];
    unsigned erases, writes, per_row[PB_JOURNAL_ROWS];
    int erase_cut, write_cut, read_error;
} flash;
static int rd(void *p,unsigned off,uint8_t *out,unsigned n) {
    flash *f=p; CHECK(off<PB_JOURNAL_BYTES && n<=PB_JOURNAL_BYTES-off);
    if(f->read_error) return -1;
    memcpy(out,f->bytes+off,n); return 0;
}
static int wr(void *p,unsigned off,const uint8_t *data) {
    flash *f=p; CHECK(off%256==0 && off<=PB_JOURNAL_BYTES-64);
    for(unsigned i=0;i<64;++i) CHECK(f->bytes[off+i]==255);
    f->writes++;
    unsigned n=f->write_cut<0?64:(unsigned)f->write_cut;
    for(unsigned i=0;i<n;++i) f->bytes[off+i]&=data[i];
    return f->write_cut<0 ? 0 : -1;
}
static int er(void *p,unsigned off) {
    flash *f=p; CHECK(off%256==0 && off<=PB_JOURNAL_BYTES-256);
    f->erases++; f->per_row[off/256]++;
    memset(f->bytes+off,255,f->erase_cut<0?256:(unsigned)f->erase_cut);
    return f->erase_cut<0 ? 0 : -1;
}
static pb_io io(flash *f) { pb_io v={f,rd,wr,er}; return v; }
static void seed(flash *f,uint32_t seq,uint32_t gen) {
    memset(f,0,sizeof(*f)); memset(f->bytes,255,sizeof(f->bytes));
    f->erase_cut=f->write_cut=-1;
    pb_setting s={seq,gen,bank.default_slot,0}; pb_encode_setting(f->bytes,&bank,&s);
}
static void put32(uint8_t *p,uint32_t n) { for(unsigned i=0;i<4;++i) p[i]=(uint8_t)(n>>(i*8)); }
static void recheck_bank(void) {
    for(unsigned i=0;i<bank.count;++i) {
        uint8_t *p=bank_bytes+64+256*i; put32(p+252,pb_crc32(p,252));
    }
    put32(bank_bytes+20,pb_crc32(bank_bytes+64,PB_BANK_BYTES-64));
    put32(bank_bytes+60,pb_crc32(bank_bytes,60));
}
static void request(uint8_t slot,uint32_t gen) {
    memset(metadata,0,sizeof(metadata)); uint8_t *m=metadata+32;
    memcpy(m,"OLAC",4); m[4]=1; m[5]=slot; put32(m+8,bank.fingerprint); put32(m+12,gen);
    put32(m+20,pb_crc32(m,20)); memcpy(m+24,"OK",2);
}
int main(int argc,char **argv) {
    CHECK(argc==2); FILE *file=fopen(argv[1],"rb"); CHECK(file);
    CHECK(fread(bank_bytes,1,sizeof(bank_bytes),file)==sizeof(bank_bytes)); fclose(file);
    CHECK(pb_crc32((const uint8_t *)"123456789",9)==0xcbf43926u);
    CHECK(pb_validate_bank(bank_bytes,&bank)==PB_OK);
    /* Every single-bit bank corruption must be rejected, including record/padding/header. */
    for(unsigned i=0;i<sizeof(bank_bytes)*8;++i) {
        pb_bank b; bank_bytes[i/8]^=1u<<(i%8);
        CHECK(pb_validate_bank(bank_bytes,&b)==PB_INVALID); bank_bytes[i/8]^=1u<<(i%8);
    }
    /* Recompute checksums so semantic validation, rather than CRC alone, must reject. */
    uint8_t original[PB_BANK_BYTES]; memcpy(original,bank_bytes,sizeof(original));
    for(unsigned test=0;test<12;++test) {
        uint8_t *r=bank_bytes+64;
        switch(test) {
        case 0: r[12]=r[13]=0; break;
        case 1: r[14]=255; r[15]=255; break;
        case 2: r[16]=0; r[17]=0; break;
        case 3: memset(r+24,'a',80); break;
        case 4: r[168]=1; break;
        case 5: memcpy(r+256+24,r+24,80); break;
        case 6: bank_bytes[14]=0; break;
        case 7: bank_bytes[14]=16; break;
        case 8: bank_bytes[15]=bank.count; break;
        case 9: bank_bytes[24]=1; break;
        case 10: r[105]=31; break;
        case 11: bank_bytes[64+256*bank.count]=0; break;
        }
        recheck_bank(); pb_bank invalid;
        CHECK(pb_validate_bank(bank_bytes,&invalid)==PB_INVALID);
        memcpy(bank_bytes,original,sizeof(original));
    }
    flash f; seed(&f,1,0); pb_io v=io(&f); pb_setting s;
    CHECK(pb_load(&bank,&v,&s)==PB_OK && s.slot==bank.default_slot);
    CHECK(pb_store(&bank,&v,s.slot,0,&s)==PB_UNCHANGED && f.erases==0 && f.writes==0);
    for(unsigned n=1;n<=320;++n) CHECK(pb_store(&bank,&v,n%bank.count,n,&s)==PB_OK);
    CHECK(f.erases==320 && f.writes==320);
    for(unsigned i=0;i<PB_JOURNAL_ROWS;++i) CHECK(f.per_row[i]==20);
    CHECK(pb_store(&bank,&v,bank.count,321,&s)==PB_INVALID);
    CHECK(pb_store(&bank,&v,0,319,&s)==PB_INVALID);
    CHECK(pb_store(&bank,&v,(s.slot+1)%bank.count,320,&s)==PB_INVALID);
    flash full=f; pb_setting before; CHECK(pb_load(&bank,&v,&before)==PB_OK);
    /* Each byte boundary of erase and page program, then reboot and retry. */
    for(unsigned phase=0;phase<2;++phase) for(int cut=0;cut<=(phase?64:256);++cut) {
        f=full; v=io(&f);
        if(phase) f.write_cut=cut; else f.erase_cut=cut;
        CHECK(pb_store(&bank,&v,(before.slot+1)%bank.count,321,&s)==PB_IO);
        CHECK(!memcmp(f.bytes+before.row*256,full.bytes+before.row*256,256));
        f.erase_cut=f.write_cut=-1;
        CHECK(pb_load(&bank,&v,&s)==PB_OK);
        CHECK(s.sequence==before.sequence || (phase && cut==64 && s.sequence==before.sequence+1));
        int result=pb_store(&bank,&v,(before.slot+1)%bank.count,321,&s);
        CHECK(result==PB_OK || result==PB_UNCHANGED);
        CHECK(pb_load(&bank,&v,&s)==PB_OK && s.generation==321);
    }
    /* All corrupted latest-page bits fall back to a prior committed record. */
    f=full; v=io(&f); CHECK(pb_load(&bank,&v,&before)==PB_OK);
    for(unsigned i=0;i<512;++i) {
        f=full; f.bytes[before.row*256+i/8]^=1u<<(i%8);
        CHECK(pb_load(&bank,&v,&s)==PB_OK && s.sequence<before.sequence);
    }
    seed(&f,UINT32_MAX,0); CHECK(pb_store(&bank,&v,0,1,&s)==PB_EXHAUSTED && !f.erases);
    memset(f.bytes,255,sizeof(f.bytes)); CHECK(pb_store(&bank,&v,0,1,&s)==PB_INVALID && !f.erases);
    seed(&f,1,0); f.read_error=1; CHECK(pb_load(&bank,&v,&s)==PB_IO); f.read_error=0;
    /* Matching sequence with differing valid payload is ambiguous, never guessed. */
    pb_setting conflict={1,1,0,1}; pb_encode_setting(f.bytes+256,&bank,&conflict);
    CHECK(pb_load(&bank,&v,&s)==PB_INVALID);
    seed(&f,1,0); memset(metadata,0,sizeof(metadata));
    CHECK(pb_boot(bank_bytes,metadata,&v,&s)==PB_UNCHANGED && !f.erases);
    request(0,1);
    uint8_t request_copy[58]; memcpy(request_copy,metadata,58);
    metadata[37]=bank.count; put32(metadata+52,pb_crc32(metadata+32,20));
    CHECK(pb_boot(bank_bytes,metadata,&v,&s)==PB_UNCHANGED && !f.erases);
    memcpy(metadata,request_copy,58); metadata[40]^=1; put32(metadata+52,pb_crc32(metadata+32,20));
    CHECK(pb_boot(bank_bytes,metadata,&v,&s)==PB_UNCHANGED && !f.erases);
    memcpy(metadata,request_copy,58);
    for(unsigned i=0;i<26*8;++i) {
        metadata[32+i/8]^=1u<<(i%8);
        CHECK(pb_boot(bank_bytes,metadata,&v,&s)==PB_UNCHANGED && !f.erases);
        metadata[32+i/8]^=1u<<(i%8);
    }
    f.write_cut=10;
    CHECK(pb_boot(bank_bytes,metadata,&v,&s)==PB_PENDING && s.slot==bank.default_slot);
    f.write_cut=-1;
    CHECK(pb_boot(bank_bytes,metadata,&v,&s)==PB_OK && s.slot==0 && s.generation==1);
    unsigned writes=f.writes, erases=f.erases;
    for(unsigned i=0;i<100;++i) CHECK(pb_boot(bank_bytes,metadata,&v,&s)==PB_UNCHANGED);
    CHECK(f.writes==writes && f.erases==erases);
    request(1,1); CHECK(pb_boot(bank_bytes,metadata,&v,&s)==PB_UNCHANGED && s.slot==0);
    puts("Bank CRC, journal rotation, 322 torn operations/reboots, replay/no-op and pending request tests passed.");
}

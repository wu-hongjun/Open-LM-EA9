#include "startup_trace.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
static uint8_t flash[1024];
static unsigned writes, reads, cut=64, cut_at=1, read_fail, locked;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); return 1; } } while(0)
uint32_t st_lock(void) { unsigned p=locked; locked=1; return p; }
void st_unlock(uint32_t p) { locked=p; }
int st_read_page(uint32_t a,uint8_t p[64]) {
    if (a<ST_FLASH_BASE || a>=ST_FLASH_END || (a&63)) abort();
    reads++; if (read_fail) return 0;
    memcpy(p,flash+(a-ST_FLASH_BASE),64); return 1;
}
int st_write_page(uint32_t a,const uint8_t p[64]) {
    if (!locked || a<ST_FLASH_BASE || a>=ST_FLASH_END || (a&63)) abort();
    unsigned off=a-ST_FLASH_BASE;
    for (unsigned i=0;i<64;i++) if (flash[off+i]!=255) abort();
    writes++; unsigned bytes=writes==cut_at?cut:64;
    memcpy(flash+off,p,bytes); return bytes==64;
}
void st_fail(uint8_t fault) { (void)fault; abort(); }
static void reset(void) { memset(flash,255,sizeof(flash)); writes=reads=read_fail=locked=0;cut=64;cut_at=1;st_init(); }
static void notes(unsigned n) { for(unsigned i=0;i<n;i++) st_note(ST_RX,4,2,i,11,0,i); }
static void flush(void) { st_flush(1,12345,444,7,3,2); }
static unsigned u16(uint8_t *p) { return p[0]|((unsigned)p[1]<<8); }
static unsigned u32(uint8_t *p) { return u16(p)|(u16(p+2)<<16); }
static uint8_t *summary(void) { for(unsigned i=0;i<16;i++) if(!memcmp(flash+64*i,"E9S2",4) && flash[64*i+5]==1 && st_crc32(flash+64*i,60)==u32(flash+64*i+60)) return flash+64*i+12; return NULL; }
#ifndef STORAGE_NO_MAIN
int main(int argc,char **argv) {
    if(argc<2) return 2;
    reset();
    if(!strcmp(argv[1],"tail")) {
        notes(100); st_note(ST_SHUTDOWN,0,0,0,0,0,100);st_note(ST_FAULT,5,0,0,0,0,101); flush();
        unsigned n=0;
        for(unsigned i=0;i<16;i++) if(flash[64*i+5]==2) for(unsigned j=0;j<flash[64*i+7];j++) {
            unsigned ms=u32(flash+64*i+12+12*j); CHECK(ms==(n<24?n:n+54));n++;
        }
        CHECK(n==48); uint8_t *q=summary(); CHECK(q && u16(q+30)==54 && q[36]==1 && u16(q+2)==5);
    } else if(!strcmp(argv[1],"summary-reserved")) {
        flash[14*64]=0;st_init();notes(48);flush();CHECK(writes==1);
        uint8_t *q=summary();CHECK(q && u16(q+30)==48 && q[35]==0);
    } else if(!strcmp(argv[1],"partial-budget")) {
        flash[12*64]=0;st_init();notes(48);flush();CHECK(writes==3);
        uint8_t *q=summary();CHECK(q && u16(q+30)==40 && q[35]==8);
    } else if(!strcmp(argv[1],"terminal-once")) {
        notes(1);flush();unsigned before=writes;notes(8);flush();CHECK(writes==before);
#ifdef PROPOSED
    } else if(!strcmp(argv[1],"inhibit-facts")) {
        for(unsigned reason=10;reason<=16;reason++) {
            reset();st_inhibit_fault(reason);CHECK(writes==0);st_inhibit_fault(99);flush();
            CHECK(summary() && u16(summary()+2)==reason);
        }
#endif
    } else if(!strcmp(argv[1],"saturation")) {
        notes(70000);flush();CHECK(summary() && u16(summary()+30)==65535);
    } else if(!strcmp(argv[1],"gated")) {
        notes(100);unsigned r=reads;for(unsigned i=0;i<100;i++) st_flush(0,i,0,0,0,0);
        CHECK(writes==0 && reads==r && locked==0);
    } else if(!strcmp(argv[1],"cuts")) {
        for(unsigned page=1;page<=13;page++) for(unsigned c=0;c<64;c++) {
            reset();cut=c;cut_at=page;notes(48);flush();CHECK(writes==page && locked==0);
#ifdef PROPOSED
            CHECK((summary()!=NULL)==(page>1));
#else
            CHECK(!summary());
#endif
            cut=64;flush();CHECK(writes==page);
            uint8_t saved[1024];memcpy(saved,flash,1024);
            st_init();notes(1);flush();CHECK(writes==page+2);
            unsigned occupied=page-1+(c!=0);
            CHECK(!memcmp(saved,flash,occupied*64));
        }
    } else if(!strcmp(argv[1],"budgets")) {
        for(unsigned used=0;used<=16;used++) for(unsigned n=0;n<=128;n++) {
            reset();if(used) flash[64*(used-1)]=0;st_init();notes(n);flush();
            if(used==16) { CHECK(writes==0);continue; }
            unsigned retained=n<48?n:48;
            unsigned eventpages=(retained+3)/4;
            if(eventpages>15-used) eventpages=15-used;
            CHECK(writes==eventpages+1);uint8_t *q=summary();CHECK(q);
            unsigned serialized=retained<4*eventpages?retained:4*eventpages;
            CHECK(q[35]==serialized && u16(q+30)==n-serialized);
            for(unsigned page=used;page<used+writes;page++)
                CHECK(st_crc32(flash+64*page,60)==u32(flash+64*page+60));
        }
    } else if(!strcmp(argv[1],"read-error")) {
        notes(48);read_fail=1;flush();CHECK(!writes && !locked);read_fail=0;flush();CHECK(!writes);
        reset();read_fail=1;st_init();read_fail=0;notes(48);flush();CHECK(!writes);
    } else if(!strcmp(argv[1],"full")) {
        memset(flash,0,1024);st_init();notes(48);flush();CHECK(!writes && !locked);
    } else if(!strcmp(argv[1],"fixture")) {
        if(argc!=3) return 2; notes(100);st_note(ST_SHUTDOWN,0,0,0,0,0,100);flush();
        FILE *f=fopen(argv[2],"wb");CHECK(f);CHECK(fwrite(flash,1,1024,f)==1024);CHECK(!fclose(f));
    } else return 2;
    return 0;
}

#endif

#include "startup_trace.h"
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint8_t flash[0x20000];
static unsigned writes, fail_write, fail_read;
static jmp_buf jumped;
static uint8_t fault_seen;
uint32_t st_lock(void) { return 0; }
void st_unlock(uint32_t p) { (void)p; }
int st_read_page(uint32_t a,uint8_t p[64]) {
    assert(a>=ST_FLASH_BASE && a<=ST_FLASH_END-64 && !(a&63));
    if (fail_read) return 0;
    memcpy(p,flash+a,64); return 1;
}
int st_write_page(uint32_t a,const uint8_t p[64]) {
    assert(a>=ST_FLASH_BASE && a<=ST_FLASH_END-64 && !(a&63));
    for (unsigned i=0;i<64;i++) assert(flash[a+i]==255);
    writes++;
    memcpy(flash+a,p,fail_write ? 31 : 64);
    return !fail_write;
}
void st_fail(uint8_t f) { fault_seen=f; longjmp(jumped,1); }
static void reset(void) { memset(flash,255,sizeof(flash)); writes=fail_write=fail_read=0; st_init(); }
static void note(unsigned n) {
    for (unsigned i=0;i<n;i++) st_note(ST_RX,(uint8_t)i,2,(uint8_t)(i+0x40),11,0xe100,i);
}
int main(int argc,char **argv) {
    assert(argc==2);
    reset(); note(1); assert(writes==0);
    st_flush(0,0,0,0,0,0); assert(writes==0);
    st_flush(1,3,11,0,0,0); assert(writes==2);
    assert(st_crc32((const uint8_t *)"123456789",9)==0xcbf43926u);
    assert(!memcmp(flash+ST_FLASH_BASE,"E9S2",4));
    note(200); st_flush(1,200,1000,0,0,0); assert(writes<=16);
    for (unsigned i=0;i<10;i++) { st_init(); note(48); st_flush(1,0,0,0,0,0); }
    assert(writes==16);
    for (unsigned i=0;i<ST_FLASH_BASE;i++) assert(flash[i]==255);
    for (unsigned i=ST_FLASH_END;i<sizeof(flash);i++) assert(flash[i]==255);
    reset(); flash[ST_FLASH_BASE+5*64]=0; st_init(); note(1);
    st_flush(1,0,0,0,0,0); assert(writes==2 && flash[ST_FLASH_BASE+5*64]==0);
    assert(!memcmp(flash+ST_FLASH_BASE+6*64,"E9S2",4));
    reset(); fail_write=1; note(4); st_flush(1,0,0,0,0,0); assert(writes==1);
    fail_write=0; st_flush(1,0,0,0,0,0); assert(writes==1);
    st_init(); note(1); st_flush(1,0,0,0,0,0); assert(writes==3);
    reset(); fail_read=1; st_init(); note(1); st_flush(1,0,0,0,0,0); assert(writes==0);
    if (!setjmp(jumped)) { ST_WAIT_WHILE(1,ST_EIC_WAIT); assert(0); }
    assert(fault_seen==ST_EIC_WAIT);
    ST_WAIT_WHILE(0,ST_CLOCK_WAIT);
    reset(); st_note(ST_STAGE,ST_MAIN,0,0,0,0,0); st_flush(1,0,0,0,0,0);
    for (unsigned i=0;i<8;i++) {
        st_note(ST_RX,(uint8_t)i,2,(uint8_t)i,11,0x8000,100+i);
        st_note(ST_TX,(uint8_t)i,3,(uint8_t)(i+1),19,0,101+i);
    }
    st_note(ST_HANDSHAKE,10,0,0,0,0,110); st_flush(1,200,88,0,0,0);
    FILE *out=fopen(argv[1],"wb"); assert(out);
    assert(fwrite(flash+ST_FLASH_BASE,1,1024,out)==1024); assert(!fclose(out));
    puts("trace: bounds, no writes when gated, exhaustion, torn pages, write/read failures, guard budget and fixture passed");
    return 0;
}

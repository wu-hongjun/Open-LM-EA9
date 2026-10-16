#include "startup_trace.h"
#include "trace_format.h"
#include "motion_trace.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static _Alignas(4) unsigned char flash[1024];
static unsigned char motion[144];
static int writes,reads,write_fail,read_fail,lock_depth,torn_bytes;
uint32_t st_lock(void) { return lock_depth++; }
void st_unlock(uint32_t k) { assert(lock_depth==(int)k+1); lock_depth=k; }
const uint8_t *st_motion_data(void) { return motion; }
int st_read_page(uint32_t a,uint8_t *p) {
    assert(a>=ST_FLASH_BASE && a<ST_FLASH_END && !(a&63));
    if (++reads==read_fail) return 0;
    memcpy(p,flash+(a-ST_FLASH_BASE),64); return 1;
}
int st_write_page(uint32_t a,const uint8_t *p) {
    assert(lock_depth>0 && a>=ST_FLASH_BASE && a<ST_FLASH_END && !(a&63));
    for (unsigned i=0;i<64;i++) assert(flash[a-ST_FLASH_BASE+i]==255);
    if (++writes==write_fail) { memcpy(flash+(a-ST_FLASH_BASE),p,torn_bytes); return 0; }
    memcpy(flash+(a-ST_FLASH_BASE),p,64); return 1;
}
static void init(int occupied) {
    memset(flash,255,1024); memset(flash,0,occupied*64);
    struct st_motion_trace m={.version=1,.valid=1,.frozen=1,.begin_ms=10,
        .initial_start=100,.initial_target=300,.target=300,.leg_start=100,
        .guard_ms=20,.guard_position=-21,.duty=64,.direction=1,.outcome=4,
        .sample_count=1,.sample_next=1,.fault=15,.last_ms=20,.accepted_ms=10,
        .samples={{.ms=20,.position=-21,.duty=64}}};
    memcpy(motion,&m,144);
    writes=reads=write_fail=read_fail=lock_depth=torn_bytes=0; st_init();
}
static struct page *page(int slot) { return (struct page *)(void *)(flash+slot*64); }
static void valid(int slot,int type,int cohort) {
    struct page *p=page(slot);
    assert(!memcmp(p->magic,"E9S3",4) && p->version==3 && p->type==type && p->cohort==cohort && p->slot==slot);
    assert(p->crc==st_crc32((void *)p,60) && !p->reserved);
}
static void populate(void) {
    for (unsigned i=0;i<70;i++) st_note(ST_CS,0,0,0,0,0,i);
    for (unsigned i=0;i<40;i++) st_note(ST_OWNER_OFFER,i,7,9,0x1234,0xabcd,1000+i);
    st_inhibit_fault(ST_SERVO_WRONG_WAY);
}
static void flush(void) { st_flush(1,2000,500,0,0,2); }
int main(int argc,char **argv) {
    init(0); populate(); st_flush(0,0,0,0,0,0); assert(writes==0);
    st_terminal(ST_PA23,0,0); assert(writes==0);
    flush(); assert(writes==12); valid(0,1,1);
    struct summary s; memcpy(&s,page(0)->data,48);
    assert(s.filtered==70 && s.dropped==8 && s.retained==32 && s.planned==32 && s.motion_chunks==3 && s.fault==15);
    for (int i=0;i<3;i++) { valid(i+1,3,1); assert(page(i+1)->chunk==i && !memcmp(page(i+1)->data,motion+48*i,48)); }
    for (int i=0;i<8;i++) { valid(i+4,2,1); assert(page(i+4)->n==4 && page(i+4)->chunk==i);
        for (int j=0;j<4;j++) { struct event e;memcpy(&e,page(i+4)->data+j*12,12);assert(e.id==8+i*4+j && e.ms==1008u+i*4+j && e.length==0x1234 && e.operand==0xabcd); }
    }
    flush(); assert(writes==12);
    st_terminal(ST_VD_LOW,2,2050);st_terminal(ST_PA23,0,2051);st_terminal(ST_TAIL_DONE,0,2151);
    st_note(ST_FAULT,ST_TICK_WAIT,0,0,0,0,2200);flush();st_terminal(ST_TERMINAL_FAULT,ST_TICK_WAIT,2200);
    if(argc==2){FILE *out=fopen(argv[1],"wb");assert(out);assert(fwrite(flash,1,1024,out)==1024);assert(!fclose(out));}
    assert(writes==16);for(int i=12;i<16;i++){valid(i,4,1);assert(page(i)->data[3]==i-11);}
    assert(page(15)->data[2]==ST_TICK_WAIT && page(15)->data[0]==5);
    /* Every initial occupancy/capacity, including no remaining pages. */
    for(int occupied=0;occupied<=16;occupied++) {
        init(occupied); populate(); flush(); int snapshot_writes=writes;
        for(int i=0;i<4;i++)st_terminal(i+1,0,3000+i);
        assert(writes<=16-occupied && writes>=snapshot_writes);
        if(occupied<16){valid(occupied,1,occupied+1);memcpy(&s,page(occupied)->data,48);
            assert(s.planned<=32 && (s.motion_chunks==0||s.motion_chunks==3));
            if(occupied<=11)assert(16-occupied-snapshot_writes>=4);
        }
    }
    /* Every failed page attempt and every power-cut byte boundary. */
    for(int fail=1;fail<=16;fail++)for(int cut=0;cut<=64;cut++) {
        init(0); populate();write_fail=fail;torn_bytes=cut;flush();
        for(int i=0;i<4;i++)st_terminal(i+1,0,3000+i);
        assert(writes==fail);int before=writes;flush();st_terminal(5,7,4000);assert(writes==before);
        for(int i=0;i<fail-1;i++)assert(page(i)->crc==st_crc32((void *)page(i),60));
        /* Reboot skips any occupied torn slot, including invalid CRC/header. */
        write_fail=0;st_init();st_inhibit_fault(1);flush();
        int start=(cut==0?fail-1:fail); if(start<16)valid(start,1,start+1);
    }
    /* Mixed cohorts, a gap, corrupt occupied page: append beyond highest slot. */
    init(0);flash[9*64+37]=1;st_init();flush();valid(10,1,11);assert(flash[9*64+37]==1);
    init(0);read_fail=reads+1;flush();assert(writes==0);st_terminal(5,1,1);assert(writes==0);
    init(0);read_fail=reads+1;st_init();flush();assert(writes==0);
    /* Erased-at-init is rechecked immediately before append; never overwrite. */
    init(0);flash[7]=0;flush();assert(writes==0);st_terminal(5,1,1);assert(writes==0&&flash[7]==0);
    /* Counter saturation and explicit conditional filters, no IRQ/NVM access. */
    init(0);for(unsigned i=0;i<70000;i++){st_note(ST_RX,3,0,0,0,0,i);st_note(ST_TX,4,0,0,0,0,i);}
    st_note(ST_OWNER_CS,0,0,0,0,0,1);st_note(ST_OWNER_PHASE,0,0,0,0,0,1);
    st_note(ST_TX_START,0,0,0,0,0,1);st_note(ST_TX_RETURN,0,0,0,0,0,1);
    assert(writes==0&&reads==16);flush();memcpy(&s,page(0)->data,48);
    assert(s.rx_count==65535&&s.tx_count==65535&&s.filtered==65535&&s.retained==0);
    /* Constant macro paths and generic ABI preserve identical serialized bytes. */
    unsigned char generic[1024];
    for(int fast=0;fast<2;fast++){
        init(0);
        if(fast){
            st_note(ST_STAGE,ST_UART,0,0,0,0,1);st_note(ST_RX,10,3,4,5,6,2);
            st_note(ST_TX,11,3,4,5,6,3);st_note(ST_CS,1,0,0,0,0,4);
            st_note(ST_CAPABILITY,3,2,1,5,0,5);st_note(ST_HANDSHAKE,10,0,0,0,0,6);
            st_note(ST_TX_START,10,2,7,0x1234,0xabcd,7);st_note(ST_FAULT,15,0,0,0,0,8);
        }else{
            (st_note)(ST_STAGE,ST_UART,0,0,0,0,1);(st_note)(ST_RX,10,3,4,5,6,2);
            (st_note)(ST_TX,11,3,4,5,6,3);(st_note)(ST_CS,1,0,0,0,0,4);
            (st_note)(ST_CAPABILITY,3,2,1,5,0,5);(st_note)(ST_HANDSHAKE,10,0,0,0,0,6);
            (st_note)(ST_TX_START,10,2,7,0x1234,0xabcd,7);(st_note)(ST_FAULT,15,0,0,0,0,8);
        }
        flush();if(!fast)memcpy(generic,flash,1024);else assert(!memcmp(generic,flash,1024));
    }
    /* CRC known vector and tampering control; first-window helper unchanged. */
    assert(st_crc32((void *)"123456789",9)==0xcbf43926u);
    init(0);flush();page(0)->data[0]^=1;assert(page(0)->crc!=st_crc32((void *)page(0),60));
    uint8_t p[9]={0xf0,9,0,2,0,0,11,0,0x55};assert(st_preserve_first_window(p,9));p[6]^=1;assert(!st_preserve_first_window(p,9));
    puts("v3 core: capacity, chronological retention, CRC, cohort, all 1040 page/cut cases, terminal-after-seal PASS");
}

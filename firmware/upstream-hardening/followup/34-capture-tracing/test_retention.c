/* Actual v3 core, motion core and production emount: synthetic status churn. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "startup_trace.h"
#include "trace_format.h"
#include "motion_trace.h"
extern int sent_n;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern uint32_t host_millis;
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
static _Alignas(4) uint8_t flash[1024];
static uint8_t incoming[25];
static int mask,inject=1,active_bus,writes,reads;
uint32_t st_lock(void){uint32_t key=mask;mask=1;return key;}
void st_unlock(uint32_t key){mask=(int)key;}
int st_read_page(uint32_t a,uint8_t *p){assert(!active_bus && a>=ST_FLASH_BASE && a<ST_FLASH_END && !(a&63));reads++;memcpy(p,flash+(a-ST_FLASH_BASE),64);return 1;}
int st_write_page(uint32_t a,const uint8_t *p){assert(!active_bus && mask && a>=ST_FLASH_BASE && a<ST_FLASH_END && !(a&63));writes++;memcpy(flash+(a-ST_FLASH_BASE),p,64);return 1;}
void st_fail(uint8_t reason){(void)reason;abort();}
int host_tx_fail;
void host_probe_send(const uint8_t *p,uint16_t n){(void)n;if(p[5]==5 && inject){inject=0;host_body_frame(incoming,25);}}
static void frame(uint8_t *p,uint16_t n,uint8_t cls,uint8_t id,uint8_t seq){
    uint16_t sum=0;memset(p,0,n);p[0]=0xf0;p[1]=(uint8_t)n;p[3]=cls;p[4]=seq;p[5]=id;p[n-1]=0x55;
    for(uint16_t i=1;i<n-3;i++)sum=(uint16_t)(sum+p[i]);p[n-3]=(uint8_t)sum;p[n-2]=(uint8_t)(sum>>8);
}
#define CHECK(c) do{if(!(c)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c);return 1;}}while(0)
int main(void){
    uint8_t p[25];memset(flash,255,sizeof flash);st_init();active_bus=1;em_init();
    frame(p,11,2,0x0a,0x20);host_body_frame(p,11);em_poll();CHECK(em_handshake_done);
    frame(incoming,25,2,0x0a,0x71);host_frame_sync();em_poll();CHECK(!inject);
    host_frame_sync();em_poll();CHECK(sent_len[sent_n-1]==25 && !memcmp(sent[sent_n-1],incoming,25));
    frame(p,25,2,0x0a,0x72);host_body_frame(p,25);em_poll();CHECK(em_handshake_done);
    for(unsigned i=0;i<100;i++){
        host_millis++;frame(p,9,1,3,(uint8_t)i);host_body_frame(p,9);host_frame_sync();int before=sent_n;em_poll();CHECK(sent_n==before+2);
    }
    frame(p,11,2,0x16,0x73);host_body_frame(p,11);em_poll();CHECK(em_shutdown_acked);
    CHECK(writes==0 && reads==16 && !mask);active_bus=0;
    st_note(ST_SHUTDOWN,0,0,0,0,0,host_millis);st_flush(1,host_millis,0,0,0,0);
    struct page *first=(void *)flash;struct summary s;memcpy(&s,first->data,48);
    CHECK(s.tx_count==em_frames_tx && s.tx_count==(unsigned)sent_n);
    int offer_raw=0,offer_normal=0,phase_end=0,admit=0,raw_start=0,raw_return=0,shutdown_return=0;
    for(unsigned slot=0;slot<16;slot++){
        struct page *page=(void *)(flash+64*slot);if(page->type!=2)continue;
        CHECK(page->crc==st_crc32((void *)page,60));
        for(unsigned i=0;i<page->n;i++){
            struct event e;memcpy(&e,page->data+12*i,12);
            if(e.kind==ST_OWNER_OFFER && e.id==0x0a && e.seq==0x71 && (e.cls&129)==129)offer_raw++;
            if(e.kind==ST_OWNER_OFFER && e.id==0x0a && e.seq==0x72 && (e.cls&129)==128)offer_normal++;
            if(e.kind==ST_OWNER_PHASE && e.cls==1)phase_end++;
            if(e.kind==ST_TX_START && e.id==0x0a && e.seq==0x71 && (e.cls&3)==3)raw_start++;
            if(e.kind==ST_TX_RETURN && e.id==0x0a && e.seq==0x71 && (e.cls&3)==3)raw_return++;
            if(e.kind==ST_SHUTDOWN_ADMIT && e.id==0x16 && e.seq==0x73)admit++;
            if(e.kind==ST_TX_RETURN && e.id==0x16 && e.seq==0x73 && (e.cls&4))shutdown_return++;
        }
    }
    CHECK(offer_raw==1 && offer_normal==1 && phase_end==1 && raw_start==1 && raw_return==1 && admit==1 && shutdown_return==1);
    CHECK(s.dropped==0 && s.retained==s.planned && s.filtered>1000);
    printf("{\"statusCycles\":100,\"filtered\":%u,\"retained\":%u,\"dropped\":%u,\"txCount\":%u,\"writesWhileBusActive\":0}\n",s.filtered,s.retained,s.dropped,s.tx_count);
    return 0;
}

/* Synthetic protocol frames only; links the manifest-pinned production bodies. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#define STARTUP_TRACE_IMPLEMENTATION
#include "startup_trace.h"
#include "board.h"
extern int sent_n, sent_overflow;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
unsigned test_status(void),test_retry(void),test_pending(void),test_raw(void);
static uint8_t incoming[32];
static unsigned incoming_n;
static int inject_id=-1, injected, inject_vd, mask, inhibit_n, powerdown_n;
int host_tx_fail;
struct event { uint8_t kind,id,flags,seq; uint32_t session; };
static struct event events[1024];
static unsigned event_n;
uint32_t st_lock(void) { uint32_t before=(uint32_t)mask;mask=1;return before; }
void st_unlock(uint32_t before) { mask=(int)before; }
void st_note(uint8_t kind,uint8_t id,uint8_t flags,uint8_t seq,uint16_t lo,uint16_t hi,uint32_t ms) {
    (void)ms; assert(event_n<1024);
    events[event_n++]=(struct event){kind,id,flags,seq,(uint32_t)lo|((uint32_t)hi<<16)};
}
void st_record(uint32_t ms,uint32_t identity,uint32_t payload) {
 st_note((uint8_t)identity,(uint8_t)(identity>>8),(uint8_t)(identity>>16),(uint8_t)(identity>>24),(uint16_t)payload,(uint16_t)(payload>>16),ms);
}
int st_preserve_first_window(const uint8_t *p,unsigned n) { (void)p;(void)n;return 0; }
void st_fail(uint8_t reason) { (void)reason;abort(); }
static void inhibit(void) { inhibit_n++; }
static void powerdown(void) { powerdown_n++; }
static void frame(uint8_t *p,unsigned n,uint8_t id,uint8_t seq) {
    memset(p,0,n); p[0]=0xf0;p[1]=(uint8_t)n;p[3]=2;p[4]=seq;p[5]=id;p[n-1]=0x55;
    unsigned sum=0;for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=(uint8_t)sum;p[n-2]=(uint8_t)(sum>>8);
}
void host_probe_send(const uint8_t *p,uint16_t n) {
    (void)n;assert(!mask);
    if(p[5]==inject_id && !injected) {
        injected=1;
        if(inject_vd)host_frame_sync();else host_body_frame(incoming,(uint16_t)incoming_n);
    }
}
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);return 1; } } while(0)
static void arm(uint8_t id,unsigned n,int trigger) {
    frame(incoming,n,id,0x71);incoming_n=n;inject_id=trigger;injected=0;inject_vd=0;
}
static void receive(uint8_t id,unsigned n) {
    uint8_t p[32];frame(p,n,id,0x73);host_body_frame(p,(uint16_t)n);
}
static int matching_pairs(void) {
    unsigned pairs=0;
    for(unsigned i=0;i<event_n;i++)if(events[i].kind==ST_TX_RETURN) {
        int found=0;
        for(unsigned j=i;j>0;j--)if(events[j-1].kind==ST_TX_START) {
            struct event a=events[j-1],b=events[i];
            found=a.id==b.id&&a.seq==b.seq&&a.flags==b.flags&&a.session==b.session;break;
        }
        if(!found)return 0;
        pairs++;
    }
    return pairs>0;
}
int main(int argc,char **argv) {
    assert(argc==2);const char *c=argv[1];
    em_init();em_set_shutdown_inhibit_handler(inhibit);em_set_powerdown_handler(powerdown);
    receive(0x0a,25);em_poll();CHECK(em_handshake_done&&test_status());
    sent_n=0;event_n=0;
    /* Ordinary readiness -> status CS interruption -> deferred raw owner. */
    arm(0x34,11,!strcmp(c,"second-status-cut")?6:5);
    host_frame_sync();em_poll();CHECK(injected&&test_pending()&&test_raw());
    unsigned before=(unsigned)sent_n;
    em_poll();CHECK((unsigned)sent_n==before); /* Cannot echo until VD. */
    host_frame_sync();
    if(!strcmp(c,"raw-failed")) {
        host_tx_fail=1;em_poll();CHECK(test_retry()&&(unsigned)sent_n==before);
        host_tx_fail=0;
    }
    if(!strcmp(c,"raw-vd")) { inject_id=0x34;injected=0;inject_vd=1; }
    if(!strcmp(c,"raw-readiness"))arm(0x0a,25,0x34);
    if(!strcmp(c,"raw-session"))arm(1,17,0x34);
    if(!strcmp(c,"raw-shutdown"))arm(0x16,11,0x34);
    if(!strcmp(c,"raw-queued-control"))arm(0x19,11,0x34);
    em_poll();CHECK(!test_retry());
    uint8_t original[32];frame(original,11,0x34,0x71);
    CHECK(sent_len[before]==11&&!memcmp(sent[before],original,11));
    CHECK(!test_status());
    if(!strcmp(c,"raw-session"))CHECK(em_session_generation()==1&&!em_handshake_done);
    if(!strcmp(c,"raw-shutdown")) {
        CHECK(inhibit_n==1&&!em_handshake_done);em_poll();CHECK(powerdown_n==1&&em_shutdown_acked);
    } else if(!strcmp(c,"raw-readiness")) {
        CHECK(test_pending());em_poll();CHECK(test_status());
    } else {
        /* VD alone remains silent in the stock-compatible post-capture mode. */
        em_poll();unsigned quiet=(unsigned)sent_n;
        for(unsigned k=0;k<8;k++){host_frame_sync();em_poll();}
        CHECK((unsigned)sent_n==quiet&&!test_status());
        receive(0x0a,25);
        if(!strcmp(c,"readiness-failed")) {
            host_tx_fail=1;em_poll();CHECK(!test_status()&&test_retry());host_tx_fail=0;
        }
        if(!strcmp(c,"readiness-session"))arm(1,17,0x0a);
        if(!strcmp(c,"readiness-shutdown"))arm(0x16,11,0x0a);
        em_poll();
        if(!strcmp(c,"readiness-session")) {
            CHECK(injected&&!test_status()&&!em_handshake_done);em_poll();
            receive(0x0a,25);em_poll();
        }
        if(!strcmp(c,"readiness-shutdown")) {
            CHECK(injected&&!test_status()&&!em_handshake_done);em_poll();
            CHECK(inhibit_n==1&&powerdown_n==1&&em_shutdown_acked);
        } else CHECK(test_status()&&em_handshake_done&&!test_retry());
    }
    if(!em_shutdown_acked) {
        unsigned again=(unsigned)sent_n;host_frame_sync();em_poll();CHECK((unsigned)sent_n==again+2);
        /* A second capture and re-arm: completed requests do not stick. */
        arm(0x34,11,5);host_frame_sync();em_poll();CHECK(injected&&test_raw());
        host_frame_sync();em_poll();CHECK(!test_retry()&&!test_status());
        receive(0x0a,25);em_poll();CHECK(test_status());
        receive(0x16,11);em_poll();CHECK(inhibit_n==1&&powerdown_n==1&&em_shutdown_acked);
    }
    CHECK(!sent_overflow&&!mask&&matching_pairs());
    printf("{\"case\":\"%s\",\"passed\":true,\"txCount\":%d,\"pairedReturns\":true}\n",c,sent_n);
    return 0;
}

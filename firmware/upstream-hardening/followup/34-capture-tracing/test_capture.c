/* All frames here are synthetic. Compile exact emount.c, not a behavioral model. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "startup_trace.h"
#include "motion_trace.h"
#include "board.h"
extern int sent_n, sent_overflow, sent_cs_asserted[];
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern uint32_t host_millis;
void host_body_frame(const uint8_t *, uint16_t);
void host_frame_sync(void);
void test_set_session(uint32_t);
static uint8_t incoming[32];
static uint16_t incoming_n;
static int inject_id = -1, injected, mask, inhibit_n, powerdown_n;
int host_tx_fail;
static int check_trace, enabled = 1;
struct event { uint8_t kind,id,flags,seq; uint32_t session; };
static struct event log_events[2048];
static unsigned log_n, completion_n;
static uint8_t completion_state[32];
static uint16_t completion_event[32];
uint32_t st_lock(void) { uint32_t prior=(uint32_t)mask; mask=1; return prior; }
void st_unlock(uint32_t prior) { mask=(int)prior; }
void st_note(uint8_t kind,uint8_t id,uint8_t flags,uint8_t seq,uint16_t lo,uint16_t hi,uint32_t ms) {
    (void)ms; if (!enabled) return; assert(log_n<2048);
    log_events[log_n++]=(struct event){kind,id,flags,seq,(uint32_t)lo|((uint32_t)hi<<16)};
}
void st_motion_completion(uint8_t state,uint16_t event) {
    if (!enabled) return; assert(completion_n<32);
    completion_state[completion_n]=state;completion_event[completion_n++]=event;
}
int st_preserve_first_window(const uint8_t *p,unsigned n) { (void)p;(void)n;return 0; }
void st_fail(uint8_t reason) { (void)reason;abort(); }
static void inhibit(void) { inhibit_n++; }
static void powerdown(void) { powerdown_n++; }
static void seal(uint8_t *p,uint16_t n) {
    uint16_t sum=0;p[1]=(uint8_t)n;p[2]=(uint8_t)(n>>8);p[n-1]=0x55;
    for (uint16_t i=1;i<n-3;i++) sum=(uint16_t)(sum+p[i]);
    p[n-3]=(uint8_t)sum;p[n-2]=(uint8_t)(sum>>8);
}
static void frame(uint8_t *p,uint16_t n,uint8_t id,uint8_t seq) {
    memset(p,0,n);p[0]=0xf0;p[3]=2;p[4]=seq;p[5]=id;seal(p,n);
}
void host_probe_send(const uint8_t *p,uint16_t n) {
    (void)n; assert(!mask);
    if (p[5]==inject_id && !injected) { injected=1;host_body_frame(incoming,incoming_n); }
}
static int find(unsigned from,uint8_t kind,int id) {
    for(unsigned i=from;i<log_n;i++) if(log_events[i].kind==kind && (id<0||log_events[i].id==id)) return (int)i;
    return -1;
}
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c); return 1; } } while(0)
#define TRACE(c) do { if(check_trace) CHECK(c); } while(0)
static uint32_t digest(uint32_t h,uint32_t v) { return (h^v)*16777619u; }
int main(int argc,char **argv) {
    assert(argc==4);check_trace=atoi(argv[2]);enabled=atoi(argv[3]);
    uint8_t p[32];em_init();em_set_shutdown_inhibit_handler(inhibit);em_set_powerdown_handler(powerdown);
    frame(p,11,0x0a,0x20);host_body_frame(p,11);em_poll();CHECK(em_handshake_done);
    sent_n=0;log_n=0;completion_n=0;
    const char *c=argv[1];
    if (!strcmp(c,"ordinary")||!strcmp(c,"raw")) {
        int raw=!strcmp(c,"raw");
        frame(p,25,0x0a,0x71);
        if(raw) { memcpy(incoming,p,25);incoming_n=25;inject_id=5;host_frame_sync();em_poll();CHECK(injected);host_frame_sync(); }
        else host_body_frame(p,25);
        em_poll();int offer=find(0,ST_OWNER_OFFER,0x0a),take=find(0,ST_OWNER_TAKE,0x0a);
        int start=find(0,ST_TX_START,0x0a),ret=find(0,ST_TX_RETURN,0x0a),complete=find(0,ST_OWNER_COMPLETE,0x0a);
        CHECK(sent_len[sent_n-1]==25 && sent[sent_n-1][5]==0x0a);
        TRACE(offer>=0 && take>offer && start>take && ret>start && complete>ret);
        TRACE((log_events[offer].flags&129)==(128|raw));
        TRACE((log_events[start].flags&3)==(2|raw) && log_events[start].seq==0x71);
        TRACE(log_events[ret].flags==log_events[start].flags && log_events[ret].session==log_events[start].session);
        TRACE((log_events[complete].flags&195)==(raw?131:194));
        if(raw) { TRACE(find(0,ST_OWNER_PHASE,-1)>=0);CHECK(!memcmp(sent[sent_n-1],p,25)); }
    } else if(!strcmp(c,"session-irq")||!strcmp(c,"shutdown-irq")) {
        int shutdown=!strcmp(c,"shutdown-irq");
        frame(p,11,0x34,0x41);host_body_frame(p,11);
        frame(incoming,17,shutdown?0x16:1,0x55);incoming_n=17;inject_id=0x34;em_poll();CHECK(injected);
        int start=find(0,ST_TX_START,0x34),ret=find(0,ST_TX_RETURN,0x34),done=find(0,ST_OWNER_COMPLETE,0x34);
        int rx=find(0,shutdown?ST_SHUTDOWN_ADMIT:ST_OWNER_OFFER,shutdown?0x16:1);
        TRACE(start>=0 && rx>start && ret>rx && done>ret);
        TRACE(log_events[start].session==0 && log_events[ret].session==0 && log_events[ret].seq==0x41);
        TRACE(log_events[start].flags==log_events[ret].flags);
        TRACE(shutdown ? (log_events[done].flags&4)!=0 : (log_events[done].flags&2)==0);
        if(!shutdown) TRACE(log_events[rx].session==1);
        em_poll();
        if(shutdown) { CHECK(inhibit_n==1 && powerdown_n==1 && em_shutdown_acked);TRACE(find(0,ST_RX,0x16)<0); }
    } else if(!strcmp(c,"pending")) {
        frame(p,11,0x34,0x41);host_body_frame(p,11);frame(p,11,0x19,0x42);host_body_frame(p,11);em_poll();
        CHECK(sent_n==1 && sent[0][5]==0x34 && em_control_overflow()==1);
        int a=find(0,ST_OWNER_OFFER,0x34),b=find(0,ST_OWNER_OFFER,0x19),t=find(0,ST_OWNER_TAKE,0x34);
        TRACE(a>=0 && b>a && t>b && (log_events[a].flags&128) && !(log_events[b].flags&128));
        TRACE(log_events[t].seq==0x41 && (log_events[a].flags&48)==48 && !(log_events[t].flags&48));
    } else if(!strcmp(c,"session-high")) {
        test_set_session(0xa1b2c3d4u);frame(p,11,0x34,0x45);host_body_frame(p,11);em_poll();
        int a=find(0,ST_OWNER_OFFER,0x34),t=find(0,ST_OWNER_TAKE,0x34),r=find(0,ST_TX_RETURN,0x34);
        TRACE(a>=0 && t>a && r>t && log_events[a].session==0xa1b2c3d4u && log_events[t].session==0xa1b2c3d4u && log_events[r].session==0xa1b2c3d4u);
    } else if(!strcmp(c,"failed-tx")) {
        frame(p,11,0x0a,0x43);host_body_frame(p,11);host_tx_fail=1;em_poll();
        TRACE(find(0,ST_TX_START,0x0a)>=0 && find(0,ST_TX_RETURN,0x0a)<0);
        int done=find(0,ST_OWNER_COMPLETE,0x0a);TRACE(done>=0 && !(log_events[done].flags&128));
        CHECK(sent_n==0);host_tx_fail=0;em_poll();CHECK(sent_n==1);
        TRACE(find(0,ST_TX_RETURN,0x0a)>=0);
    } else if(!strcmp(c,"shutdown")) {
        frame(p,11,0x16,0x44);host_body_frame(p,11);CHECK(inhibit_n==1);em_poll();CHECK(powerdown_n==1 && em_shutdown_acked);
        int a=find(0,ST_SHUTDOWN_ADMIT,0x16),s=find(0,ST_TX_START,0x16),r=find(0,ST_TX_RETURN,0x16);
        TRACE(a>=0 && s>a && r>s && find(0,ST_RX,0x16)<0 && log_events[s].seq==0x44);
    } else if(!strcmp(c,"queue")) {
        em_post_event(EM_REC_MOVE,0x11);em_post_event(EM_REC_STOP,0x22);em_post_event(EM_REC_MOVE,0x33);
        host_frame_sync();em_poll();CHECK(sent_n==2 && sent_len[1]==50 && sent[1][45]==EM_REC_MOVE && sent[1][46]==0x11);
        TRACE(completion_n==4 && completion_state[0]==ST_MC_QUEUED && completion_state[1]==ST_MC_QUEUED && completion_state[2]==ST_MC_QUEUE_FULL && completion_state[3]==ST_MC_TX_RETURN);
        TRACE(completion_event[0]==completion_event[3]);
    } else if(!strcmp(c,"phase")) {
        host_frame_sync();em_poll();CHECK(sent_n==2);
        int a=find(0,ST_OWNER_PHASE,-1),b=a<0?-1:find((unsigned)a+1,ST_OWNER_PHASE,-1);
        TRACE(a>=0 && b>a && (log_events[a].flags&8) && log_events[b].flags==0);
    } else assert(0);
    CHECK(!sent_overflow && !mask);
    uint32_t h=2166136261u;
    for(int i=0;i<sent_n;i++) { h=digest(h,sent_len[i]);h=digest(h,(uint32_t)sent_cs_asserted[i]);for(unsigned j=0;j<sent_len[i];j++)h=digest(h,sent[i][j]); }
    h=digest(h,em_handshake_done);h=digest(h,em_shutdown_acked);h=digest(h,em_session_generation());h=digest(h,em_control_overflow());h=digest(h,(uint32_t)inhibit_n);h=digest(h,(uint32_t)powerdown_n);h=digest(h,host_millis);
    h=digest(h,host_port.Group[0].OUTSET.reg);h=digest(h,host_port.Group[0].OUTCLR.reg);
    printf("{\"case\":\"%s\",\"wireAndSideEffectsFNV32\":\"%08x\",\"txCount\":%d}\n",c,h,sent_n);
    return 0;
}

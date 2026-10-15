#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
extern int sent_n;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
void host_body_frame(const uint8_t *, uint16_t);
void host_frame_sync(void);
static uint8_t incoming[256];
static uint16_t incoming_n;
static int cut, injected;
int host_tx_fail;
int host_tx_fail_id = -1;
int host_irq_mask, host_copy_arm, host_irq_pending;
void host_irq_replay(void) {
    if (host_irq_pending && !host_irq_mask) { host_irq_pending=0; host_body_frame(incoming,incoming_n); }
}
void host_copy_interrupt(void) {
    if (!host_copy_arm) return;
    host_copy_arm=0;host_irq_pending=1;host_irq_replay();
}
static void seal(uint8_t *p,uint16_t n) {
    uint16_t sum=0; p[1]=(uint8_t)n; p[2]=(uint8_t)(n>>8); p[n-1]=0x55;
    for (uint16_t i=1;i<n-3u;i++) sum=(uint16_t)(sum+p[i]);
    p[n-3]=(uint8_t)sum; p[n-2]=(uint8_t)(sum>>8);
}
static void frame(uint8_t *p,uint16_t n,uint8_t cls,uint8_t id,uint8_t seq) {
    memset(p,0,n);p[0]=0xf0;p[3]=cls;p[4]=seq;p[5]=id;p[6]=0x34;p[7]=0x12;seal(p,n);
}
static void inject(void) {
    injected=1; host_body_frame(incoming,incoming_n);
}
void host_probe_delay(uint32_t us) {
    if (injected || !cut) return;
    int last=sent_n?sent[sent_n-1][5]:-1;
    if ((cut==1 && us==10) || (cut==3 && us==100 && last==5)
        || (cut==4 && us==300) || (cut==6 && us==100 && last==6)) inject();
}
void host_probe_send(const uint8_t *p,uint16_t n) {
    (void)n;
    if (injected || !cut) return;
    if ((cut==2 && p[5]==5) || (cut==5 && p[5]==6) || (cut==7 && p[5]==0x34)) inject();
}
static void boot(void) {
    uint8_t p[11]; em_init(); frame(p,11,2,0x0a,0x20);
    host_body_frame(p,11); em_poll(); assert(em_handshake_done); sent_n=0;
}
#define CHECK(x) do { if (!(x)) { printf("FAIL line %d: %s\n",__LINE__,#x); return 1; } } while(0)
int main(int argc,char **argv) {
    assert(argc>=2); boot();
    uint8_t p[32];
    if (!strcmp(argv[1],"baseline")) {
        host_frame_sync();em_poll();CHECK(sent_n==2 && sent[0][5]==5 && sent[1][5]==6);
    } else if (!strcmp(argv[1],"immutable") || !strcmp(argv[1],"first-wins") || !strcmp(argv[1],"sequence")) {
        frame(p,11,2,0x34,0x71); host_body_frame(p,11);
        if (strcmp(argv[1],"sequence")) {
            frame(p,11,!strcmp(argv[1],"immutable")?1:2,0x19,0xff);p[6]=0x99;seal(p,11);host_body_frame(p,11);
        }
        em_poll();CHECK(sent_n==1 && sent[0][5]==0x34);
        CHECK(sent[0][7]==0x34 && sent[0][8]==0x12 && sent[0][4]==0);
    } else if (!strcmp(argv[1],"active")) {
        frame(p,11,2,0x34,0x71);host_body_frame(p,11);
        frame(incoming,11,2,0x34,0x55);incoming[6]=0xaa;seal(incoming,11);incoming_n=11;cut=7;
        em_poll();CHECK(sent_n==1 && sent[0][7]==0x34 && sent[0][4]==0);
        em_poll();CHECK(sent_n==2 && sent[1][7]==0xaa && sent[1][4]==0);
    } else if (!strcmp(argv[1],"capture") || !strcmp(argv[1],"normal")) {
        assert(argc==5);cut=atoi(argv[2]);uint8_t id=(uint8_t)strtoul(argv[3],0,0);
        incoming_n=(uint16_t)atoi(argv[4]);int normal=!strcmp(argv[1],"normal");
        frame(incoming,incoming_n,normal?1:2,id,0x71);
        uint32_t hs=em_t_handshake;
        em_post_event(EM_REC_MOVE,0);
        host_frame_sync();em_poll();
        int old=cut==1?0:cut<5?1:2;
        CHECK(injected && sent_n==old);
        em_poll();CHECK(sent_n==old);
        host_frame_sync();em_poll();
        if (normal) {
            CHECK(sent_n==old+2 && sent[old][5]==5 && sent[old+1][5]==6);
            CHECK(sent[old][4]==0x72 && sent[old+1][4]==0x72);
        } else {
            CHECK(sent_n==old+1 && sent_len[old]==incoming_n);
            CHECK(!memcmp(sent[old],incoming,incoming_n));
            CHECK(em_handshake_done && em_t_handshake==hs);
            host_frame_sync();em_poll();CHECK(sent_n==old+1);
            frame(p,11,2,0x0a,0x41);host_body_frame(p,11);em_poll();
            host_frame_sync();em_poll();CHECK(sent_n==old+4);
            if (cut<5) CHECK(sent[old+3][45]==EM_REC_MOVE && sent_len[old+3]==50);
        }
    } else if (!strcmp(argv[1],"failed-init")) {
        frame(p,17,2,1,0x61);host_body_frame(p,17);em_poll();sent_n=0;
        frame(p,11,2,0x0a,0x62);host_body_frame(p,11);
        host_tx_fail=1;em_poll();CHECK(sent_n==0 && !em_handshake_done);
        host_tx_fail=0;em_poll();CHECK(sent_n==1 && em_handshake_done);
    } else if (!strcmp(argv[1],"failed-tail")) {
        em_post_event(EM_REC_MOVE,0);uint32_t tx=em_frames_tx;
        host_tx_fail_id=6;host_frame_sync();em_poll();
        CHECK(sent_n==1 && em_frames_tx==tx+1 && em_events_sent==0);
        host_tx_fail_id=-1;host_frame_sync();em_poll();
        CHECK(sent_n==3 && sent_len[2]==50 && sent[2][45]==EM_REC_MOVE);
    } else if (!strcmp(argv[1],"failed-raw")) {
        frame(incoming,11,2,0x34,0x71);incoming_n=11;cut=4;
        host_frame_sync();em_poll();CHECK(sent_n==1);
        host_tx_fail=1;host_frame_sync();em_poll();CHECK(sent_n==1);
        frame(p,11,2,0x19,0x55);host_body_frame(p,11);
        host_tx_fail=0;em_poll();CHECK(sent_n==2 && !memcmp(sent[1],incoming,11));
        em_poll();CHECK(sent_n==3 && sent[2][5]==0x19 && sent[2][4]==0);
    } else if (!strcmp(argv[1],"failed-shutdown")) {
        frame(p,11,2,0x16,0x44);host_body_frame(p,11);uint32_t tx=em_frames_tx;
        host_tx_fail=1;em_poll();CHECK(!em_shutdown_acked && em_frames_tx==tx && sent_n==0);
        host_tx_fail=0;em_poll();CHECK(em_shutdown_acked && sent_n==1 && !memcmp(sent[0],p,11));
    } else if (!strcmp(argv[1],"focus-copy")) {
        frame(p,27,1,4,0x50);p[19]=EM_REC_MOVE;p[20]=0x34;p[21]=0x12;p[23]=0;seal(p,27);host_body_frame(p,27);
        memcpy(incoming,p,27);incoming[20]=0x78;incoming[21]=0x56;seal(incoming,27);incoming_n=27;
        host_copy_arm=1;struct em_focus_cmd cmd;
        CHECK(em_take_focus_cmd(&cmd) && cmd.target==0x1234);
        CHECK(em_take_focus_cmd(&cmd) && cmd.target==0x5678);
        CHECK(!em_take_focus_cmd(&cmd));
    } else if (!strcmp(argv[1],"session-queues")) {
        frame(p,27,1,4,0x50);p[19]=EM_REC_MOVE;p[20]=0x34;p[21]=0x12;p[23]=0;seal(p,27);host_body_frame(p,27);
        em_post_event(EM_REC_MOVE,0);em_post_query_answer(0x60,0x1234);
        frame(p,17,2,1,0x61);host_body_frame(p,17);
        struct em_focus_cmd cmd;CHECK(!em_take_focus_cmd(&cmd));
        em_poll();frame(p,11,2,0x0a,0x62);host_body_frame(p,11);em_poll();
        host_frame_sync();em_poll();CHECK(sent_len[sent_n-1]==48);
    } else if (!strcmp(argv[1],"session")) {
#ifdef OWNED
        uint32_t g=em_session_generation();
        frame(p,17,2,1,0x61);host_body_frame(p,17);
        CHECK(em_session_generation()==g+1 && !em_handshake_done && !em_t_handshake);
        em_poll();host_frame_sync();em_poll();CHECK(sent_n==1);
#endif
    } else assert(0);
    puts("PASS");return 0;
}

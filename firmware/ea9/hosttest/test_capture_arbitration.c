/* Adversarial callback ordering at actual responder boundaries, not wire timing. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../src/emount.c"
extern void host_body_frame(const uint8_t *, uint16_t), host_frame_sync(void), host_set_cs_pin(int);
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern int sent_n, host_tx_fail_id;
static const char *scenario;
static unsigned injected, inhibited, powered_down, parked;
void motor_emergency_release(void) {}
void motor_inhibit(void) { ++inhibited; }
static void powerdown(void) { assert(em_shutdown_acked); ++powered_down; }
static void park(void) { ++parked; }
static void receive(uint8_t id, uint16_t word)
{
    uint8_t frame[11]={0xf0,11,0,2,0x71,id,(uint8_t)word,(uint8_t)(word>>8),0,0,0x55};
    unsigned sum=0;for(unsigned i=1;i<8;++i)sum+=frame[i];
    frame[8]=(uint8_t)sum;frame[9]=(uint8_t)(sum>>8);
    host_body_frame(frame,sizeof frame);
}
void host_probe_after_tx(uint8_t id)
{
    if(injected) return;
    if(id==5 && !strcmp(scenario,"shutdown-in-05")) { injected=1; receive(0x16,0); }
    if(id==0x0a && !strcmp(scenario,"new-session-in-final")) { injected=1; receive(1,0); }
}
void host_probe_delay_us(uint32_t us)
{
    if(injected || us!=300) return;
    if(!strcmp(scenario,"shutdown-gap")) { injected=1; receive(0x16,0); }
    if(!strcmp(scenario,"capture-gap")) { injected=1; receive(0x28,0); }
    if(!strcmp(scenario,"window-gap")) { injected=1; host_set_cs_pin(1); on_cs_edge(1); }
}
int main(int argc,char **argv)
{
    assert(argc==2);scenario=argv[1]; em_init();
    em_set_powerdown_handler(powerdown);em_set_park_handler(park);
    if(!strncmp(scenario,"shutdown-length-",16)) {
        unsigned n=(unsigned)atoi(scenario+16);assert(n>=9 && n<=65);
        uint8_t frame[65]={0xf0,0,0,2,0x71,0x16};frame[1]=n;
        for(unsigned i=6;i<n-3;++i)frame[i]=(uint8_t)i;
        unsigned sum=0;for(unsigned i=1;i<n-3;++i)sum+=frame[i];
        frame[n-3]=sum;frame[n-2]=sum>>8;frame[n-1]=0x55;
        int before=sent_n;host_body_frame(frame,n);em_poll();
        if(n<=64) {assert(sent_n==before+1 && sent_len[before]==n && !memcmp(sent[before],frame,n) && inhibited==1 && powered_down==1);}
        else assert(sent_n==before && !inhibited && !powered_down);
        printf("capture arbitration %s passed\n",scenario);return 0;
    }
    receive(1,0);em_poll();
    if(!strcmp(scenario,"new-session-in-final")) {
        receive(0x0a,0);em_poll();
        if(em_handshake_done) { fputs("old final reply armed new session\n",stderr);return 1; }
        em_poll(); receive(0x0a,0);em_poll();assert(em_handshake_done);
    } else {
        receive(0x0a,0);em_poll();assert(em_handshake_done);
        int before=sent_n;
        if(!strcmp(scenario,"capture-sequence")) {
            uint8_t frame[25]={0xf0,25,0,2,0x71,0x0a};
            for(unsigned i=6;i<22;++i)frame[i]=(uint8_t)i;
            unsigned sum=0;for(unsigned i=1;i<22;++i)sum+=frame[i];
            frame[22]=sum;frame[23]=sum>>8;frame[24]=0x55;
            host_body_frame(frame,sizeof frame);em_poll();
#ifdef EM_ARBITRATION_H
            assert(sent_n==before);host_frame_sync();em_poll();
#endif
            if(sent_n!=before+1 || sent_len[before]!=25 || memcmp(sent[before],frame,25)) {fputs("capture opener did not echo complete request\n",stderr);return 1;}
            const uint8_t ids[]={0x0b,0x1b,0x28,0x19,0x19,0x28,0x0b};
            for(unsigned i=0;i<sizeof ids;++i) {
                before=sent_n;receive(ids[i],0x1100);em_poll();assert(sent_n==before+1 && sent[before][5]==ids[i]);
                before=sent_n;host_frame_sync();em_poll();assert(sent_n==before);
            }
            before=sent_n;receive(0x0a,0);em_poll();assert(sent_n==before+1 && sent_len[before]==25);
            before=sent_n;host_frame_sync();em_poll();assert(sent_n==before+2);
            puts("capture arbitration capture-sequence passed");return 0;
        }
        if(!strcmp(scenario,"snapshot-deferred")) {
            receive(0x34,0xa55a);
            host_set_cs_pin(1);on_cs_edge(1); em_poll();
            if(sent_n!=before) { fputs("control sent during receive window\n",stderr);return 1; }
            /* Supply a normal empty window; pending control keeps its operand. */
            host_set_cs_pin(0);on_cs_edge(0);em_poll();
            assert(sent_n==before+1 && sent[before][5]==0x34);
            assert(sent[before][7]==0x5a && sent[before][8]==0xa5);
        } else {
            em_post_event(EM_REC_MOVE,0);em_post_query_answer(EM_REC_Q_POS2D,0x1234);
            if(!strcmp(scenario,"fail-05"))host_tx_fail_id=5;
            if(!strcmp(scenario,"fail-06"))host_tx_fail_id=6;
            host_frame_sync();em_poll();
            if(!strcmp(scenario,"shutdown-in-05") || !strcmp(scenario,"shutdown-gap")) {
                if(sent_n!=before+1) { fputs("status06 sent after shutdown admission\n",stderr);return 1; }
                assert(inhibited==1 && !em_shutdown_acked && !parked);
                em_poll();
                assert(sent_n==before+2 && sent[before+1][5]==0x16 && powered_down==1 && !parked);
                before=sent_n;receive(1,0);em_poll();host_frame_sync();em_poll();assert(sent_n==before);
            } else if(!strcmp(scenario,"capture-gap") || !strcmp(scenario,"window-gap")) {
                if(sent_n!=before+1) { fputs("status06 sent after receive interruption\n",stderr);return 1; }
                assert(!em_events_sent);
                if(!strcmp(scenario,"window-gap")) {host_set_cs_pin(0);on_cs_edge(0);}
                em_poll();
                if(!strcmp(scenario,"capture-gap"))assert(sent[before+1][5]==0x28);
                before=sent_n;host_frame_sync();em_poll();
                assert(sent_n==before+2 && sent_len[before+1]==53 && sent[before+1][45]==EM_REC_MOVE && sent[before+1][47]==EM_REC_Q_POS2D);
            } else if(!strcmp(scenario,"fail-05") || !strcmp(scenario,"fail-06")) {
                assert(!em_events_sent);host_tx_fail_id=-1;before=sent_n;
                host_frame_sync();em_poll();assert(sent_n==before+2 && sent_len[before+1]==53);
            } else return 2;
        }
    }
    for(int i=0;i<sent_n;++i) {
        unsigned sum=0,n=sent_len[i]; for(unsigned j=1;j<n-3;++j)sum+=sent[i][j];
        assert(sent[i][n-1]==0x55 && sent[i][n-3]==(sum&255) && sent[i][n-2]==(sum>>8));
    }
    printf("capture arbitration %s passed\n",scenario);return 0;
}

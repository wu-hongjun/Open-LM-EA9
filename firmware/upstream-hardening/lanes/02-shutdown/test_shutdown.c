/* Actual production dispatcher, including private queues for consumption checks.
 * IRQ/UART/delay boundaries are explicit scripted cuts in the retained shim. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount-under-test.c"
extern int sent_n;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern int host_pad_to;
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
static uint8_t shutdown_frame[65], other[65];
static unsigned shutdown_length=11, park_count, off_count, inhibit_count;
static int injection, park_reenter, armed, park_never_returns;
static void seal(uint8_t *p,unsigned n,uint8_t cls,uint8_t seq,uint8_t id)
{
    memset(p,0,n);p[0]=0xf0;p[1]=n;p[3]=cls;p[4]=seq;p[5]=id;p[n-1]=0x55;
    unsigned sum=0;for(unsigned i=1;i<n-3;i++)sum+=p[i];
    p[n-3]=sum;p[n-2]=sum>>8;
}
static void send_shutdown(void) { host_body_frame(shutdown_frame,shutdown_length); }
static void inhibit(void) { inhibit_count++; }
static void park(void)
{
    park_count++;
    while (park_never_returns) { __asm__ volatile ("" ::: "memory"); }
#ifdef PROPOSED
    assert(inhibit_count==1 && em_shutdown_requested());
#endif
    if(park_reenter) {
        host_body_frame(other,11);host_frame_sync();em_poll();
        send_shutdown();em_poll();
    }
}
static void off(void) {
    off_count++;
    if (park_reenter) {
        host_body_frame(other,11); host_frame_sync(); em_poll();
        send_shutdown(); em_poll();
    }
}
void shutdown_host_delay(uint32_t us)
{
    if(armed && injection==(int)us) { armed=0;send_shutdown(); }
}
void shutdown_host_tx(void)
{
    if(armed && injection==-1) { armed=0;send_shutdown(); }
}
#define CHECK(x) do { if(!(x)){printf("FAIL %s:%d %s\n",__FILE__,__LINE__,#x);return 1;} } while(0)
int main(int argc,char **argv)
{
    assert(argc>=2 && argc<=4);const char *c=argv[1];
    em_init();em_set_park_handler(park);em_set_powerdown_handler(off);
#ifdef PROPOSED
    em_set_shutdown_inhibit_handler(inhibit);
#else
    (void)inhibit;
#endif
    shutdown_length=argc>=3?(unsigned)atoi(argv[2]):11;
    seal(shutdown_frame,shutdown_length,2,argc>=4?(uint8_t)atoi(argv[3]):0x71,0x16);seal(other,11,2,0x42,0x0b);
    if(!strcmp(c,"valid-control")) { host_body_frame(other,11);em_poll();CHECK(sent_n==1&&sent[0][5]==0x0b);return 0; }
    if(!strcmp(c,"padding"))host_pad_to=64;
    if(!strcmp(c,"length64")) {shutdown_length=64;seal(shutdown_frame,64,2,0xff,0x16);}
    if(!strcmp(c,"length9")) {shutdown_length=9;seal(shutdown_frame,9,2,0,0x16);}
    if(!strcmp(c,"oversize65")) {shutdown_length=65;seal(shutdown_frame,65,2,0x71,0x16);}
    if(!strcmp(c,"bad-checksum"))shutdown_frame[8]^=1;
    if(!strcmp(c,"bad-terminator"))shutdown_frame[10]=0;
    if(!strcmp(c,"truncated"))shutdown_length=10;
    if(!strcmp(c,"disabled"))em_set_shutdown_enabled(0);
    if(!strcmp(c,"park-reentry"))park_reenter=1;
    if(!strcmp(c,"park-unresponsive"))park_never_returns=1;
    if(!strcmp(c,"pending-command")) {seal(other,27,1,0x42,4);other[19]=0x1c;unsigned s=0;for(unsigned i=1;i<24;i++)s+=other[i];other[24]=s;other[25]=s>>8;host_body_frame(other,27);CHECK(em_focus_pending);}
    if(!strcmp(c,"lead")||!strcmp(c,"gap")||!strcmp(c,"during-status-tx")) {
        em_handshake_done=1;em_post_event(0x1c,0);em_post_query_answer(0x22,0x1234);
        host_frame_sync();armed=1;injection=!strcmp(c,"lead")?10:(!strcmp(c,"gap")?300:-1);
        em_poll();
        CHECK(g_event_n==1&&g_ans_n==1);
        unsigned expected=!strcmp(c,"lead")?0:1;CHECK(sent_n==(int)expected);
        em_poll();CHECK(sent_n==(int)expected+1);CHECK(sent[expected][5]==0x16);
    } else {
        send_shutdown();
        if(!strcmp(c,"normal-overwrite")){seal(other,11,1,0x42,3);host_body_frame(other,11);}
        if(!strcmp(c,"init-overwrite"))host_body_frame(other,11);
        if(!strcmp(c,"repeat-pending")){seal(other,11,2,0x99,0x16);host_body_frame(other,11);}
        em_poll();
        if(!strcmp(c,"oversize65")||!strcmp(c,"bad-checksum")||!strcmp(c,"bad-terminator")||!strcmp(c,"truncated")) {CHECK(sent_n==0&&park_count==0&&off_count==0);return 0;}
        if(!strcmp(c,"disabled")) {CHECK(sent_n==0&&park_count==0);host_body_frame(other,11);em_set_shutdown_enabled(1);em_poll();}
        CHECK(sent_n==1);CHECK(sent_len[0]==shutdown_length);CHECK(!memcmp(sent[0],shutdown_frame,shutdown_length));
    }
#ifdef PROPOSED
    CHECK(park_count==0&&off_count==1&&em_shutdown_acked);
#else
    CHECK(park_count==1&&off_count==1&&em_shutdown_acked);
#endif
#ifdef PROPOSED
    CHECK(inhibit_count==1&&em_shutdown_requested());
#endif
    if(!strcmp(c,"pending-command")){struct em_focus_cmd cmd;CHECK(!em_take_focus_cmd(&cmd));}
    if(!strcmp(c,"off-session")) {seal(other,11,2,0x50,1);host_body_frame(other,11);em_poll();CHECK(em_shutdown_acked);}
    if(!strcmp(c,"repeat-off")) {send_shutdown();em_poll();CHECK(off_count==1);}
    int before=sent_n;host_frame_sync();em_poll();CHECK(sent_n==before);
    if(!strcmp(c,"off-session")||!strcmp(c,"repeat-off"))CHECK(sent_n==1);
    printf("PASS %s\n",c);return 0;
}

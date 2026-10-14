/* Offline AF 3.0 boundary probe; no hardware or motor is linked. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../src/emount.c"
extern void host_body_frame(const uint8_t *, uint16_t), host_frame_sync(void);
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern int sent_n;
void motor_inhibit(void) {}
void motor_emergency_release(void) {}
static uint8_t request_frame[11], inject;
static void receive(uint8_t id)
{
    uint8_t frame[11] = {0xf0,11,0,2,0x71,id,0,0x11,0,0,0x55};
    unsigned sum=0; for(unsigned i=1;i<8;++i) sum+=frame[i];
    frame[8]=sum; frame[9]=sum>>8;
    memcpy(request_frame,frame,sizeof frame);
    host_body_frame(frame,sizeof frame);
}
void host_probe_delay_us(uint32_t us)
{
    if(inject && us==EM_STATUS_GAP_US) {
        inject=0;
        host_body_frame(request_frame,sizeof request_frame);
    }
}
int main(int argc,char **argv)
{
    assert(argc==3);
    unsigned id=(unsigned)strtoul(argv[1],NULL,0);
    uint8_t profile[256]; FILE *f=fopen(argv[2],"rb");
    assert(f && !fseek(f,-256,SEEK_END));
    assert(fread(profile,1,sizeof profile,f)==sizeof profile); fclose(f);
    assert(ea9_profile_load_from(profile)); em_init();
    receive(1); em_poll(); receive(0x0a); em_poll(); assert(em_handshake_done);
    /* Build the supplied request without publishing it before the gap. */
    request_frame[5]=(uint8_t)id;
    unsigned sum=0; for(unsigned i=1;i<8;++i)sum+=request_frame[i];
    request_frame[8]=sum;request_frame[9]=sum>>8;
    int first=sent_n; inject=1;host_frame_sync();em_poll();
    assert(!inject && sent_n==first+1 && sent[first][5]==5);
    int after05=sent_n;em_poll();
    int before_vd=sent_n-after05;
    host_frame_sync();em_poll();
    assert(sent_n>after05 && sent[after05][5]==id);
    int raw=sent_len[after05]==sizeof request_frame &&
            !memcmp(sent[after05],request_frame,sizeof request_frame);
    printf("{\"id\":%u,\"replyBeforeNextVD\":%s,\"firstReplyLength\":%u,"
           "\"firstReplyRawEchoExact\":%s,\"framesAfterInterruption\":[",
           id,before_vd?"true":"false",sent_len[after05],raw?"true":"false");
    for(int i=after05;i<sent_n;++i)printf("%s%u",i==after05?"":",",sent[i][5]);
    puts("]}");return 0;
}

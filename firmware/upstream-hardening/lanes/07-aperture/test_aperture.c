#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
extern int sent_n, host_pad_to;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
static uint8_t pending[32];
static int inject;
static uint16_t word(const uint8_t *p) { return p[0]|((uint16_t)p[1]<<8); }
static void seal(uint8_t *p,uint16_t n) {
    uint16_t sum=0;p[1]=(uint8_t)n;p[2]=(uint8_t)(n>>8);p[n-1]=0x55;
    for(uint16_t i=1;i<n-3;i++) sum=(uint16_t)(sum+p[i]);
    p[n-3]=(uint8_t)sum;p[n-2]=(uint8_t)(sum>>8);
}
static void frame(uint8_t *p,uint16_t n,uint8_t id,uint16_t operand) {
    memset(p,0,32);p[0]=0xf0;p[3]=2;p[4]=0x79;p[5]=id;
    p[6]=(uint8_t)operand;p[7]=(uint8_t)(operand>>8);seal(p,n);
}
static void send(uint8_t id,uint16_t operand) {
    uint8_t p[32];frame(p,17,id,operand);host_body_frame(p,17);em_poll();
}
void host_probe_send(const uint8_t *p,uint16_t n) {
    (void)n;
    if(inject && p[5]==5) { inject=0;host_body_frame(pending,17); }
}
static int wire_ok(void) {
    for(int k=0;k<sent_n;k++) {
        uint8_t *p=sent[k];uint16_t n=sent_len[k],sum=0;
        if(word(p+1)!=n || p[n-1]!=0x55) return 0;
        for(uint16_t i=1;i<n-3;i++) sum=(uint16_t)(sum+p[i]);
        if(word(p+n-3)!=sum) return 0;
    }
    return 1;
}
#define CHECK(x) do { if(!(x)) {printf("FAIL %d: %s\n",__LINE__,#x);return 1;} } while(0)
int main(int argc,char **argv) {
    assert(argc>=2);em_init();send(0x0a,0);sent_n=0;uint8_t p[32];
    if(!strcmp(argv[1],"short")) {
        assert(argc==5);int id=atoi(argv[2]),n=atoi(argv[3]);host_pad_to=atoi(argv[4]);
        frame(p,(uint16_t)n,(uint8_t)id,0x1234);host_body_frame(p,(uint16_t)n);em_poll();
        CHECK(sent_n==0);
    } else if(!strcmp(argv[1],"deferred")) {
        frame(p,17,8,0);host_body_frame(p,17);CHECK(!em_m08_aperture_on);
        em_poll();CHECK(em_m08_aperture_on);send(0x28,0);CHECK(word(sent[sent_n-1]+15)==0x1100);
    } else if(!strcmp(argv[1],"overflow")) {
        frame(p,17,0x34,0x1234);host_body_frame(p,17);
        frame(p,17,8,0);host_body_frame(p,17);em_poll();send(0x28,0);
        CHECK(word(sent[sent_n-1]+15)==0);
    } else if(!strcmp(argv[1],"session")) {
        send(8,0);send(0x28,0);CHECK(word(sent[sent_n-1]+15)==0x1100);
        send(1,0);send(0x28,0);CHECK(word(sent[sent_n-1]+15)==0);
    } else if(!strcmp(argv[1],"capture")) {
        frame(pending,17,8,0);inject=1;host_frame_sync();em_poll();
        host_frame_sync();em_poll();send(0x28,0);CHECK(word(sent[sent_n-1]+15)==0);
    } else if(!strcmp(argv[1],"metadata")) {
        host_frame_sync();em_poll();CHECK(sent[0][5]==5);
        CHECK(word(sent[0]+6)==0x1100 && word(sent[0]+8)==0x1100);
        CHECK(sent[0][50]==0x10 && sent[0][52]==0x10 && sent[0][57]==0x10 && sent[0][58]==0x10);
        CHECK(sent[0][10]==0 && (sent[0][14]&1));
        CHECK(word(sent[0]+30)==500 && word(sent[0]+32)==500);
        send(0x1b,0x1600);CHECK(word(sent[sent_n-1]+6)==0x1100 && word(sent[sent_n-1]+8)==0x1100);
        frame(p,17,3,0);p[3]=1;p[11]=0;p[12]=0x16;seal(p,17);host_body_frame(p,17);
        CHECK(em_m03_aperture==0x1600);
        send(8,0);send(0x28,0);CHECK(word(sent[sent_n-1]+15)==0x1100);
        CHECK(word(sent[sent_n-1]+10)==500 && word(sent[sent_n-1]+12)==500);
        send(8,0x8000);send(0x28,0);CHECK(word(sent[sent_n-1]+15)==0);
        send(7,0);CHECK(word(sent[sent_n-1]+15)==234);
        int before=sent_n;send(0x35,0);CHECK(sent_n==before);
        send(1,0);CHECK(!(sent[sent_n-1][6+52/8]&(1u<<(52%8))));
        CHECK(em_aperture_from_descriptor(0x10)==0x1100 && em_aperture_to_descriptor(0x1100)==0x10);
    } else if(!strcmp(argv[1],"opaque")) {
        for(unsigned v=0;v<=65535;v++) {
            sent_n=0;send(0x34,(uint16_t)v);
            CHECK(sent_n==1 && sent[0][5]==0x34 && sent_len[0]==32);
            CHECK(sent[0][6]==0 && word(sent[0]+7)==v && word(sent[0]+10)==850 && word(sent[0]+12)==850);
            CHECK(wire_ok());
        }
    } else assert(0);
    CHECK(wire_ok());puts("PASS");return 0;
}

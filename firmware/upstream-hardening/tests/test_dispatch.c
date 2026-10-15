/* Exercise the actual emount.c dispatcher, not a second parser model. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "emount.h"
extern int sent_n;
extern uint8_t sent[][256];
void host_body_frame(const uint8_t *, uint16_t);

static void seal(uint8_t *f, uint16_t n)
{
    uint16_t sum=0;
    f[1]=(uint8_t)n; f[2]=(uint8_t)(n>>8); f[n-1]=0x55;
    for (uint16_t i=1;i<=n-4u;i++) sum=(uint16_t)(sum+f[i]);
    f[n-3]=(uint8_t)sum; f[n-2]=(uint8_t)(sum>>8);
}
int main(int argc, char **argv)
{
    assert(argc==2);
    uint8_t f[64]={0xf0,0,0,2,0x21,0x0a};
    uint16_t n=9;
    int valid=0, motion=0, short_field=0;
    em_init();
    if (!strcmp(argv[1],"valid-init")) valid=1;
    else if (!strcmp(argv[1],"valid-padding")) valid=1;
    else if (!strcmp(argv[1],"short-capability")) { f[5]=8; short_field=1; }
    else if (!strcmp(argv[1],"short-offer")) { f[5]=1; short_field=2; }
    else if (!strcmp(argv[1],"short-mode")) { f[3]=1; f[5]=4; short_field=3; }
    else if (!strcmp(argv[1],"short-aperture")) { f[3]=1; f[5]=3; short_field=4; }
    else if (!strcmp(argv[1],"valid-move") || !strcmp(argv[1],"bad-move")
             || !strcmp(argv[1],"truncated-move")) {
        n=!strcmp(argv[1],"truncated-move") ? 32 : 27;
        f[3]=1; f[5]=4; f[19]=0x1d;
        f[20]=0x34; f[21]=0x12; f[23]=0;
        motion=1; valid=!strcmp(argv[1],"valid-move");
    }
    seal(f,n);
    if (!strcmp(argv[1],"checksum") || !strcmp(argv[1],"bad-move")) f[n-3]^=1;
    else if (!strcmp(argv[1],"terminator")) f[n-1]=0;
    else if (!strcmp(argv[1],"length-zero")) f[1]=0;
    else if (!strcmp(argv[1],"length-high")) f[2]=1;
    else if (!strcmp(argv[1],"truncated")) n--;
    else if (!strcmp(argv[1],"header-only")) n=6;
    else if (!strcmp(argv[1],"truncated-move")) n=27;
    else if (!strcmp(argv[1],"valid-padding")) { memset(f+n,0x55,7); n+=7; }
    else assert(valid || motion || short_field);
    if (short_field) { memset(f+n,0x55,32u-n); n=32; }
    host_body_frame(f,n); em_poll();
    struct em_focus_cmd c;
    int got=em_take_focus_cmd(&c);
    int admitted=motion ? got : (sent_n!=0 || em_handshake_done);
    if (short_field==1) admitted=em_m08_n!=0;
    if (short_field==2) {
        admitted=0;
        for (unsigned i=0;i<8;i++) admitted|=em_body_offer[i]!=0;
    }
    if (short_field==3) admitted=em_mode_used!=0;
    if (short_field==4) admitted=em_m03_n!=0;
    int passed=admitted==valid;
    if (passed && valid && motion) passed=c.op==EM_OP_MOVE && c.target==0x1234;
    if (passed && valid && !motion) passed=sent_n==1 && sent[0][5]==0x0a && em_handshake_done;
    printf("%s: %s; admitted=%d expected=%d\n",argv[1],passed?"pass":"FAIL",admitted,valid);
    return passed ? 0 : 1;
}

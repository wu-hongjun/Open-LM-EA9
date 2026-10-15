#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "emount.h"
extern int sent_n;
extern uint8_t sent[][256];
void host_window_payload(const uint8_t *,uint16_t);
void host_early_payload(const uint8_t *,uint16_t);
void host_preload_rx(const uint8_t *,uint16_t);
int main(int argc,char **argv) {
    assert(argc==2); unsigned split=(unsigned)atoi(argv[1]); assert(split<=11);
    uint8_t f[11]={0xf0,11,0,2,0x11,1,0,0,0,0,0x55};
    unsigned sum=0; for (unsigned i=1;i<=7;i++) sum+=f[i];
    f[8]=(uint8_t)sum; f[9]=(uint8_t)(sum>>8);
    static const uint8_t noise[]={0x5a,0xa5,0xff,0x00};
    if (!split) host_preload_rx(noise,sizeof(noise));
    host_early_payload(f,(uint16_t)split);
    host_window_payload(f+split,(uint16_t)(sizeof(f)-split));
    em_init(); em_poll();
    int passed=sent_n==1 && sent[0][5]==1;
    printf("first-window prefix %u: %s\n",split,passed ? "pass" : "lost");
    return passed ? 0 : 1;
}

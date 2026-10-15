#define STORAGE_NO_MAIN
#include "test_storage.c"
#include "emount.h"
extern void host_body_frame(const uint8_t *,uint16_t);
int main(int argc,char **argv) {
    if(argc!=2) return 2;unsigned len=(unsigned)atoi(argv[1]);uint8_t p[32];memset(p,0xa5,sizeof(p));
    p[0]=0xf0;p[1]=len;p[2]=0;p[3]=2;p[4]=0x44;p[5]=8;p[6]=0;p[7]=255;
    unsigned sum=0;for(unsigned i=1;i<len-3;i++)sum+=p[i];
    p[len-3]=sum;p[len-2]=sum>>8;p[len-1]=0x55;
    em_init();reset();host_body_frame(p,sizeof(p));flush();
    uint8_t *q=summary();CHECK(q);CHECK(q[32]==(len>=11));
    if(len>=11) CHECK(q[28]==255);
    return 0;
}

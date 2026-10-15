#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "em_frame.h"

static unsigned long checks;
static void reject(const uint8_t *f,uint16_t n)
{
    struct em_frame_view view={f,99};
    assert(em_frame_open(f,n,&view)!=EM_FRAME_OK);
    assert(!view.data && !view.length); ++checks;
}
int main(int argc,char **argv)
{
    assert(argc==2);
    FILE *file=fopen(argv[1],"rb"); assert(file);
    unsigned frames=0, tails=0;
    uint8_t f[65535], original[256], header[2];
    struct em_frame_view view;
    reject(NULL,0); reject(NULL,65535);
    /* Full uint16_t length domain: no wrap in the checksum walk. */
    memset(f,255,sizeof(f)); f[0]=0xf0; f[1]=f[2]=255; f[65534]=0x55;
    uint16_t sum=0;
    for (unsigned i=1;i<=65531;i++) sum=(uint16_t)(sum+f[i]);
    f[65532]=(uint8_t)sum; f[65533]=(uint8_t)(sum>>8);
    assert(em_frame_open(f,65535,&view)==EM_FRAME_OK && view.length==65535); ++checks;
    f[65532]^=1; reject(f,65535);
    for (;;) {
        size_t got=fread(header,1,2,file);
        if (!got) { assert(feof(file)); break; }
        assert(got==2);
        uint16_t n=(uint16_t)header[0]|((uint16_t)header[1]<<8);
        assert(n>=9 && n<=256 && fread(original,1,n,file)==n);
        uint16_t length=(uint16_t)original[1]|((uint16_t)original[2]<<8);
        assert(em_frame_open(original,n,&view)==EM_FRAME_OK);
        assert(view.data==original && view.length==length); ++checks; ++frames;
        if (length<n) ++tails;
        /* Every strict prefix of a valid frame must fail, even if the omitted
         * portion is only checksum/terminator. Window padding is not required. */
        for (uint16_t i=0;i<length;i++) reject(original,i);
        memcpy(f,original,n); f[0]^=1; reject(f,n);
        memcpy(f,original,n); f[length-1]^=1; reject(f,n);
        memcpy(f,original,n); f[length-3]^=1; reject(f,n);
        memcpy(f,original,n); f[length-2]^=1; reject(f,n);
        memcpy(f,original,n); f[1]=f[2]=0; reject(f,n);
        memcpy(f,original,n); f[1]=255; f[2]=255; reject(f,n);
        /* Nonzero bytes after the frame are legal and never alter admission. */
        memcpy(f,original,length); memset(f+length,0xa5,256u-length);
        assert(em_frame_open(f,256,&view)==EM_FRAME_OK && view.length==length); ++checks;
        assert(em_frame_open(original,n,NULL)==EM_FRAME_OK); ++checks;
    }
    assert(!ferror(file)); fclose(file);
    printf("{\"captureFrames\":%u,\"paddedWindows\":%u,\"checks\":%lu}\n",frames,tails,checks);
    return 0;
}

/* Synthetic histories through the exact production trace serializer. */
#include "startup_trace.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned char flash[1024];
static unsigned call, cut_call, cut_bytes, locked;
uint32_t st_lock(void) { unsigned prior=locked; locked=1; return prior; }
void st_unlock(uint32_t prior) { locked=prior; }
int st_read_page(uint32_t address, uint8_t out[64]) {
    if(address<ST_FLASH_BASE || address>=ST_FLASH_END || (address&63)) abort();
    memcpy(out,flash+(address-ST_FLASH_BASE),64); return 1;
}
int st_write_page(uint32_t address,const uint8_t page[64]) {
    if(!locked || address<ST_FLASH_BASE || address>=ST_FLASH_END || (address&63)) abort();
    unsigned n=(++call==cut_call)?cut_bytes:64;
    for(unsigned i=0;i<64;i++) if(flash[address-ST_FLASH_BASE+i]!=255) abort();
    memcpy(flash+(address-ST_FLASH_BASE),page,n); return n==64;
}
void st_fail(uint8_t reason) { (void)reason; abort(); }
int main(int argc,char **argv) {
    int repeat=argc>1 && !strcmp(argv[1],"--repeat");
    argc-=repeat; argv+=repeat;
    if(argc<2 || (argc-2)%3) return 2;
    memset(flash,255,sizeof flash);
    unsigned used=(unsigned)strtoul(argv[1],0,10);
    if(used>16) return 2;
    if(used) flash[64*(used-1)]=0;
    for(int a=2;a<argc;a+=3) {
        unsigned n=(unsigned)strtoul(argv[a],0,10);
        cut_call=(unsigned)strtoul(argv[a+1],0,10);
        cut_bytes=(unsigned)strtoul(argv[a+2],0,10);
        if(cut_bytes>64) return 2;
        call=0; st_init();
        for(unsigned i=0;i<n;i++) st_note(i%2?ST_TX:ST_RX,(uint8_t)i,2,(uint8_t)i,11,0,i);
        st_flush(1,n+1,n*11,0,0,2);
        if(repeat) {
            st_flush(1,n+2,n*11,0,0,2);
            st_note(ST_RX,3,2,3,11,0,n+3);
            st_flush(1,n+4,(n+1)*11,0,0,2);
        }
    }
    return fwrite(flash,1,sizeof flash,stdout)==sizeof flash?0:1;
}

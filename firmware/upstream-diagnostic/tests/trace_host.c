#include "startup_trace.h"
#include <stdlib.h>
#include <string.h>
static uint8_t memory[1024];
static int initialized;
uint32_t st_lock(void) { return 0; }
void st_unlock(uint32_t k) { (void)k; }
int st_read_page(uint32_t a,uint8_t p[64]) {
    if (!initialized) { memset(memory,255,sizeof(memory)); initialized=1; }
    if (a<ST_FLASH_BASE || a>ST_FLASH_END-64 || (a&63)) abort();
    memcpy(p,memory+a-ST_FLASH_BASE,64); return 1;
}
int st_write_page(uint32_t a,const uint8_t p[64]) {
    if (a<ST_FLASH_BASE || a>ST_FLASH_END-64 || (a&63)) abort();
    for (unsigned i=0;i<64;i++) if (memory[a-ST_FLASH_BASE+i]!=255) abort();
    memcpy(memory+a-ST_FLASH_BASE,p,64); return 1;
}
void st_fail(uint8_t fault) { (void)fault; abort(); }

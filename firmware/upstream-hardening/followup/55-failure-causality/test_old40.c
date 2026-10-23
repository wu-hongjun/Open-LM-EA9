#include <assert.h>
#include <stdio.h>
#include "startup_trace.c"
static unsigned char flash[1024], motion[144];
static unsigned writes;
uint32_t st_lock(void) { return 0; }
void st_unlock(uint32_t key) { (void)key; }
const uint8_t *st_motion_data(void) { return motion; }
int st_read_page(uint32_t a, uint8_t *p) {
    assert(a>=ST_FLASH_BASE && a<=ST_FLASH_END-64 && !(a&63));
    memcpy(p,flash+(a-ST_FLASH_BASE),64); return 1;
}
int st_write_page(uint32_t a, const uint8_t *p) {
    (void)a; (void)p; writes++; return 1;
}
int main(void) {
    memset(flash,255,sizeof flash);
    for (unsigned i=0;i<32;i++) st_init();
    assert(!writes && r_next_page==0);
    memset(flash,0,sizeof flash); /* 4.0 scanner occupancy, not a valid camera record. */
    for (unsigned i=0;i<32;i++) st_init();
    assert(!writes && r_next_page==16);
    puts("PASS actual4.0 st_init returns with empty/full tail and consumes no pages; main caller has no boot-record gate");
    return 0;
}

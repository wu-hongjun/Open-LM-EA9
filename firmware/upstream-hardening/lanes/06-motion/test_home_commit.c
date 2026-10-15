#include <stdint.h>
#include <stdio.h>
static int g_homed,g_home_state,masked,pending,stop,before,after;
#define HOME_READY 2
static void interrupt(void) {stop=1;if(g_homed)after++;else before++;}
static uint32_t st_lock(void) {uint32_t old=masked;masked=1;return old;}
static void st_unlock(uint32_t old) {masked=old;if(!masked && pending){pending=0;interrupt();}}
static int home_cancel_requested(void) {return stop;}
static void host_boundary(void) {if(masked)pending=1;else interrupt();}
static void commit(void) {
#include "home_commit.inc"
    return;
cancelled: return;
}
int main(void) {
    commit();
    int good=!(before && g_homed) && after==1 && g_home_state==HOME_READY;
    printf("%s accepted_before=%d accepted_after=%d ready=%d\n",good?"PASS":"FAIL",before,after,g_homed);
    return !good;
}

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <stdlib.h>
#include "servo.h"
#include "emount.h"
static int g_homed=1,g_aborted,latch,shutdown;
volatile uint8_t em_handshake_done=1;
static uint32_t epoch=1;
static uint8_t g_abort_pending,g_abort_by_stop,g_last_op;
static unsigned g_stops_idle,g_focus_aborts,events,runs;
#ifndef FROZEN
static uint32_t g_focus_session;
#endif
static const struct servo_cfg STOCK={0};
static int mode,aborted,locked;
uint32_t em_session_generation(void) {return epoch;}
uint8_t em_shutdown_requested(void) {return shutdown;}
uint8_t motor_is_inhibited(void) {return latch;}
uint32_t st_lock(void) {uint32_t old=locked;if(mode==7 && runs && !locked)epoch++;locked=1;return old;}
void st_unlock(uint32_t old) {locked=old;}
void em_post_event(uint8_t c,uint8_t p) {(void)c;(void)p;events++;}
void em_set_scan_state(uint8_t s) {(void)s;}
static int focus_cmd_target(const struct em_focus_cmd *c,int32_t *p) {(void)c;*p=100;return 1;}
static void focus_scan(const struct em_focus_cmd *c) {(void)c;}
static void focus_drive(const struct em_focus_cmd *c) {(void)c;}
static uint8_t focus_abort(void);
static uint8_t focus_run(int32_t p,uint16_t t,const struct servo_cfg *cfg) {
    (void)p;(void)t;(void)cfg;runs++;
    if(mode==1)epoch++;
    if(mode==2)shutdown=1;
    if(mode==3)latch=1;
    if(mode==4)em_handshake_done=0;
    if(mode==5)g_aborted=1;
    if(mode==6)g_abort_pending=1;
    aborted=focus_abort();
    /* Final callback can change ownership even after a controller returned OK. */
    return mode==6?SERVO_ABORTED:SERVO_OK;
}
#include "main_test.inc"
int main(int argc,char **argv) {
    assert(argc==2);mode=atoi(argv[1]);
    struct em_focus_cmd c={.op=EM_OP_MOVE,.target=100};
    if(mode==8)epoch++;
#ifdef FROZEN
    focus_exec(&c);
#else
    focus_exec(&c,1);
#endif
    int good=mode==0?(events==1 && !aborted):mode==8?!runs:mode==7?!events:mode==6?aborted && !events:aborted && !events;
    printf("%s mode=%d events=%u aborted=%d runs=%u\n",good?"PASS":"FAIL",mode,events,aborted,runs);
    return !good;
}

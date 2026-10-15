/* Actual extracted 3.2 motor_home/home_still functions; supplied I/O boundaries.
 * No claim of real IRQ, time, voltage, encoder or mechanical behavior. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include <assert.h>
#define SERVO_TRACE_N 24
#define EM_DIAG_MAGIC 1
#define EM_DIAG_FORMAT 1
#define TAG_MOTR 1
#define MOTOR_PAGE0 0
#define TRACE_PAGE0 1
#define EM_OP_STOP 1
#define EM_OP_MOVE 2
#define EM_REC_STOP 1
#define PARK_ATTEMPTS 2
#define FHIST_PAGE 2
#define FOCUS_LAST_PAGE 3
struct servo_result { int32_t start,end; uint16_t duty_peak,duty_first,ms; uint8_t outcome; };
static const struct { int tolerance; } PARK={6};
static unsigned g_park_n, servo_calls;
static uint32_t diagnostic_calls;
struct em_focus_cmd { uint8_t op; };
static struct em_focus_cmd g_next, pending;
static uint8_t g_next_pending, has_pending;
static uint32_t g_next_session;
static int g_homed, g_aborted;
static uint16_t g_home_trace[SERVO_TRACE_N];
static uint8_t g_home_trace_n;
static uint32_t g_flash_boots, g_boot, em_t_handshake, em_frames_rx, em_frames_tx;
static uint8_t em_handshake_done=1;
static const struct { int dry; } STOCK={0};
static struct { struct { uint32_t reg; } RCAUSE; } pm;
#define PM (&pm)
static uint32_t now=0, generation=1, pumps, drive_pumps, settle_pumps;
static int duty, inhibited, shutdown_pending, attached, resets, stop_events, did_inject;
static int moving_after_off, jumped, post_disabled_pumps;
static const char *scenario;
static int32_t position;
static jmp_buf deadline;
static void motion_shutdown_inhibit(void);
static uint32_t millis(void) { return now; }
static int32_t abs_encoder_track(void) { return position; }
static uint16_t abs_encoder_raw(void) { return (uint16_t)position; }
static uint8_t em_shutdown_requested(void) { return shutdown_pending; }
static uint32_t em_session_generation(void) { return generation; }
static void motor_emergency_release(void) { attached=0; duty=0; }
static void motor_inhibit(void) { inhibited=1; motor_emergency_release(); }
static uint8_t motor_is_inhibited(void) { return inhibited; }
static void motor_attach_pins(void) { if (!inhibited) attached=1; }
static void motor_drive(int value) {
    if (inhibited) return;
    if (shutdown_pending && value) moving_after_off++;
    attached=1; duty=value;
}
static void motor_brake(void) { if (!inhibited) { attached=1; duty=0; } }
static void inject(const char *which) {
    did_inject=1;
    if (!strcmp(which,"stop")) { pending.op=EM_OP_STOP; has_pending=1; }
    if (!strcmp(which,"move")) { pending.op=EM_OP_MOVE; has_pending=1; }
    if (!strcmp(which,"session")) { generation++; em_handshake_done=0; }
    if (!strcmp(which,"shutdown")) {
        shutdown_pending=1;
#ifndef FROZEN
        motion_shutdown_inhibit();
#endif
    }
}
static void abs_encoder_track_reset(void) {
    resets++; position=0;
    if (!strcmp(scenario,"commit-stop")) inject("stop");
    if (!strcmp(scenario,"commit-session")) inject("session");
}
static uint8_t em_take_focus_cmd(struct em_focus_cmd *c) {
    if (!has_pending) return 0;
    has_pending=0; *c=pending; return 1;
}
static void em_post_event(uint8_t id, uint8_t param) { assert(id==EM_REC_STOP && param==1); stop_events++; }
static void vdd_read_burst(uint16_t *lo,uint16_t *hi,int ms) {
    *lo=*hi=3150;
    if (strcmp(scenario,"frozen-clock")) now+=(uint32_t)ms;
    if (!strcmp(scenario,"burst-stop")) inject("stop");
}
static void vdd_track_reset(void) {}
static void vdd_track_result(uint16_t *lo,uint16_t *hi) { *lo=*hi=3150; }
static void diag_page(unsigned page,const uint32_t *w,unsigned n) {diagnostic_calls++;(void)page;(void)w;(void)n;}
static void servo_move_rel(int32_t delta,const void *cfg,struct servo_result *r) {
    (void)delta; (void)cfg; memset(r,0,sizeof(*r)); servo_calls++;
}
static void trail_fhist(unsigned p) {(void)p;}
static void focus_hist_page(unsigned p) {(void)p;}
static void trace_page(unsigned p,unsigned n,const struct servo_result *r) {(void)p;(void)n;(void)r;}
static void norm_page(void) {}
static void pump(int32_t pos) {
    (void)pos;
    if (++pumps>1000010u) { jumped=1; longjmp(deadline,1); }
    if (shutdown_pending) post_disabled_pumps++;
    if (strcmp(scenario,"frozen-clock")) now++;
    if (duty) {
        drive_pumps++;
        if (!strcmp(scenario,"drive-timeout") ||
            (!strcmp(scenario,"travel-control") && drive_pumps<100)) position-=8;
        if (drive_pumps==5 && !did_inject) {
            if (!strcmp(scenario,"stop") || !strcmp(scenario,"retry") || !strcmp(scenario,"budget")) inject("stop");
            if (!strcmp(scenario,"session")) inject("session");
            if (!strcmp(scenario,"shutdown")) inject("shutdown");
            if (!strcmp(scenario,"move-control")) inject("move");
        }
    } else {
        settle_pumps++;
        if (!strcmp(scenario,"settle-timeout")) position+=8;
        if (settle_pumps==5 && !did_inject) {
            if (!strcmp(scenario,"settle-stop")) inject("stop");
            if (!strcmp(scenario,"settle-shutdown")) inject("shutdown");
            if (!strcmp(scenario,"settle-session")) inject("session");
        }
    }
}
#include "extracted.inc"
#ifdef FROZEN
static void motion_shutdown_inhibit(void) { motor_inhibit(); }
static void home_service(void) { motor_home(); }
#endif
int main(int argc,char **argv) {
    assert(argc==2); scenario=argv[1];
    if (strstr(scenario,"park")) {
        g_homed=1; position=1000;
        if (!strcmp(scenario,"shutdown-park")) shutdown_pending=1;
        else inhibited=1;
        park_to_infinity();
        int ok=servo_calls==0 && diagnostic_calls==0 && g_park_n==0;
        printf("%s: %s servo_calls=%u diagnostic_calls=%u\n",scenario,ok?"pass":"FAIL",servo_calls,diagnostic_calls);
        return ok ? 0 : 1;
    }
    if (!strcmp(scenario,"wrap-control")) now=UINT32_MAX-50u;
    if (!strcmp(scenario,"pre-stop")) inject("stop");
    if (!strcmp(scenario,"pre-shutdown")) inject("shutdown");
    if (!setjmp(deadline)) home_service();
    int control=strstr(scenario,"control")!=NULL;
    int ok=control ? g_homed && resets==1 && !duty : !g_homed && !duty && !jumped;
    if (control && !strcmp(scenario,"move-control")) ok &= g_next_pending || has_pending;
    if (!control && !strstr(scenario,"commit")) ok &= resets==0;
    if (strstr(scenario,"shutdown")) ok &= !attached && !moving_after_off;
    if (!strcmp(scenario,"pre-stop") || !strcmp(scenario,"burst-stop")) ok &= drive_pumps==0;
#ifndef FROZEN
    if (!control && !shutdown_pending) {
        uint32_t old_pumps=pumps;
        for (unsigned i=0;i<10;i++) home_service();
        ok &= old_pumps==pumps; /* no background retry */
    }
    if (!strcmp(scenario,"retry") || !strcmp(scenario,"budget")) {
        unsigned budget=!strcmp(scenario,"budget");
        if (budget) { did_inject=0; drive_pumps=0; }
        pending.op=EM_OP_MOVE; has_pending=1; home_service();
        ok &= g_home_attempts==2 && (!!g_homed != !!budget);
        if (budget) {
            pending.op=EM_OP_MOVE; has_pending=1;
            uint32_t old_pumps=pumps; home_service();
            ok &= !g_homed && old_pumps==pumps;
        }
    }
    if (!strcmp(scenario,"drive-timeout") || !strcmp(scenario,"settle-timeout") || !strcmp(scenario,"frozen-clock"))
        ok &= g_home_state==HOME_FAILED && inhibited;
#endif
    printf("%s: %s ready=%d reset=%d pumps=%u duty=%d attached=%d stops=%d\n",
           scenario,ok?"pass":"FAIL",g_homed,resets,pumps,duty,attached,stop_events);
    return ok ? 0 : 1;
}

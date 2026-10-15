#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "board.h"
#include "motor.h"
static int masked,pending,in_isr,cut,step,at,waits,clock_calls;
static int inhibited;
static unsigned fake_ms;
static int frozen_clock,seek_duty;
struct port_host port_mem;
struct tcc_host tcc_mem;
struct pm_host pm_mem;
struct gclk_host gclk_mem;
static int pins_on(void) { return PORT->Group[0].PINCFG[8].bit.PMUXEN || PORT->Group[0].PINCFG[9].bit.PMUXEN || PORT->Group[0].PINCFG[18].bit.PMUXEN || PORT->Group[0].PINCFG[19].bit.PMUXEN; }
#ifdef FROZEN
void motor_emergency_release(void) { PORT->Group[0].PINCFG[8].bit.PMUXEN=0;PORT->Group[0].PINCFG[9].bit.PMUXEN=0;PORT->Group[0].PINCFG[18].bit.PMUXEN=0;PORT->Group[0].PINCFG[19].bit.PMUXEN=0;PORT->Group[0].OUTSET.reg=1u<<19; }
void motor_inhibit(void) { inhibited=1;motor_emergency_release(); }
uint8_t motor_is_inhibited(void) { return inhibited; }
#endif
static void interrupt(void) { in_isr=1; motor_inhibit(); in_isr=0;cut=1; }
void host_boundary(void) {
    if (in_isr) return;
    if (cut && pins_on()) { puts("FAIL remux after sticky cutoff");exit(1); }
    if (++step==at) { if(masked) pending=1; else interrupt(); }
}
uint32_t st_lock(void) { host_boundary();uint32_t old=masked;masked=1;host_boundary();return old; }
void st_unlock(uint32_t old) { host_boundary();masked=old;if(!masked && pending) { pending=0;interrupt(); }host_boundary(); }
void host_wait(void) { assert(!masked);waits++;host_boundary(); }
uint32_t millis(void) { if(seek_duty && clock_calls==1 && (TCC0->CC[0].reg!=MOTOR_DUTY_MAX || TCC0->CC[2].reg!=MOTOR_DUTY_MAX || TCC0->CC[1].reg || TCC0->CC[3].reg)) { puts("FAIL uint16 duty reversed before clamp");exit(1); } if(++clock_calls>1000010) {puts("FAIL unbounded frozen clock");exit(1);}return frozen_clock?0:fake_ms++; }
int32_t abs_encoder_position(void) {return 0;}
#include "motor_test.inc"
int main(int argc,char **argv) {
    assert(argc==3);at=atoi(argv[2]);(void)inhibited;
    if(!strcmp(argv[1],"attach")) motor_attach_pins();
    else if(!strcmp(argv[1],"drive")) motor_drive(512);
    else if(!strcmp(argv[1],"reverse")) motor_drive(-512);
    else if(!strcmp(argv[1],"brake")) motor_brake();
    else if(!strcmp(argv[1],"release")) motor_release();
    else if(!strcmp(argv[1],"init")) motor_init();
    else if(!strcmp(argv[1],"seek-freeze")) {frozen_clock=1; motor_seek_end(1,400,10,10,30);if(!motor_is_inhibited())return 1;}
    else if(!strcmp(argv[1],"seek-duty")) {seek_duty=1;motor_seek_end(1,65535,0,0,1);/* capture in host_boundary before release below */}
    else if(!strcmp(argv[1],"sticky")) {motor_inhibit();cut=1;motor_init();motor_drive(500);motor_brake();motor_attach_pins();motor_coast();}
    else if(!strcmp(argv[1],"transient")) {motor_emergency_release();assert(!motor_is_inhibited());motor_drive(200);assert(pins_on());}
    else abort();
    host_boundary(); if(at && at<=step) assert(cut);
    printf("PASS boundaries=%d waits=%d\n",step,waits);return 0;
}

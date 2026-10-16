/* Fixed bounded collector checks, synthetic values, no production I/O. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "motion_trace.h"
#include "servo.h"
static uint32_t clock_ms;
uint32_t millis(void) {return clock_ms;}
int main(void) {
    const struct st_motion_trace *t=(const struct st_motion_trace *)st_motion_data();
    st_motion_sample(1,1);st_motion_leg(1,1,0);st_motion_finish(SERVO_WRONG_WAY);
    assert(!t->valid && !t->frozen);
    st_motion_command(1,0x4321);st_motion_begin(10,20,0xfffffff0u,1);
    assert(t->flags==ST_MF_DRY);
    for(unsigned i=0;i<65540;i++) {
        st_motion_sample(0xfffffff0u+i,(int32_t)i);
        st_motion_leg(20,10,0);
    }
    assert(t->sample_count==65535 && t->sample_next==0);
    for(unsigned i=0;i<4;i++)assert(t->samples[i].position==(int32_t)(65536+i));
    st_motion_completion(ST_MC_ATTEMPT,0x11d);
    assert(t->completion_state==ST_MC_ATTEMPT);
    st_motion_begin(500,1000,0xfffffff0u,0);
    assert(t->sample_count==0 && t->completion_state==0 && t->reserved[0]==0);
    st_motion_command(3,0x1234); /* Not yet an accepted servo retarget. */
    st_motion_sample(0xfffffff5u,500);st_motion_leg(1000,500,0);
    assert(t->accepted_op==1 && t->accepted_operand==0x4321);
    st_motion_sample(2,500);st_motion_leg(200,500,(1u<<8)|ST_MS_REBASE|ST_MS_HOLDING|ST_MS_NEGATIVE);
    assert(t->accepted_op==3 && t->accepted_operand==0x1234 && t->accepted_ms==2);
    st_motion_sample(7,621);st_motion_leg(200,500,(1u<<8)|ST_MS_NEGATIVE);
    st_motion_finish(SERVO_WRONG_WAY);
    assert(t->guard_ms==7 && t->guard_position==621 && t->frozen);
    struct st_motion_trace frozen=*t;
    for(unsigned i=0;i<64;i++) {
        st_motion_command(7,0xffff);st_motion_begin(1,2,3,1);
        st_motion_sample(4,5);st_motion_leg(6,7,0);st_motion_drive(999);st_motion_finish(SERVO_RUNAWAY);
    }
    assert(!memcmp(t,&frozen,sizeof frozen));
    clock_ms=9;st_motion_completion(ST_MC_SUPPRESSED,0);
    assert(t->completion_state==ST_MC_SUPPRESSED && t->completion_ms==9);
    frozen=*t;clock_ms=20;st_motion_completion(ST_MC_TX_RETURN,0x11c);
    assert(!memcmp(t,&frozen,sizeof frozen));
    puts("bounded ring saturation, clock wrap, ignored retarget, sticky first guard and completion: PASS");
    return 0;
}

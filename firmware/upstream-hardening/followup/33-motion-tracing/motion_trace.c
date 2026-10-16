#include "motion_trace.h"
#include "servo.h"
#include "startup_trace.h"
#include "delay.h"
static struct st_motion_trace trace;
static uint8_t pending_op;
static uint16_t pending_operand;
void st_motion_command(uint8_t op, uint16_t operand)
{
    pending_op=op; pending_operand=operand;
}
void st_motion_begin(int32_t start, int32_t target, uint32_t ms, uint8_t dry)
{
    if (trace.frozen) return;
    /* Fixed-size clear, no allocation and no sensor/NVM access. */
    trace=(struct st_motion_trace){0};
    trace.version=1; trace.valid=1; trace.flags=dry ? ST_MF_DRY : 0;
    trace.begin_ms=trace.accepted_ms=trace.last_ms=ms;
    trace.initial_start=trace.leg_start=start;
    trace.initial_target=trace.target=target;
    trace.direction=target>=start ? 1 : -1;
    trace.command_op=trace.accepted_op=pending_op;
    trace.command_operand=trace.accepted_operand=pending_operand;
}
void st_motion_sample(uint32_t ms, int32_t position)
{
    if (!trace.valid || trace.frozen) return;
    struct st_motion_sample *s=&trace.samples[trace.sample_next];
    s->ms=ms; s->position=position; s->duty=trace.duty;
    s->state=trace.state; s->retargets=trace.retargets;
    trace.last_ms=ms;
    trace.sample_next=(trace.sample_next+1u)&(ST_MOTION_SAMPLES-1u);
    if (trace.sample_count!=UINT16_MAX) trace.sample_count++;
}
void st_motion_leg(int32_t target, int32_t start, unsigned packed)
{
    if (!trace.valid || trace.frozen) return;
    uint8_t n=(uint8_t)(packed>>8);
    if (n!=trace.retargets) {
        trace.accepted_op=pending_op; trace.accepted_operand=pending_operand;
        trace.accepted_ms=trace.last_ms;
    }
    trace.target=target; trace.leg_start=start;
    trace.direction=(packed&ST_MS_NEGATIVE) ? -1 : 1;
    trace.retargets=n; trace.state=(uint8_t)packed;
    /* State interpreted by guards after command/rebase processing at this read. */
    if (trace.sample_count) {
        struct st_motion_sample *s=&trace.samples[(trace.sample_next-1u)&3u];
        s->state=trace.state; s->retargets=n;
    }
}
void st_motion_drive(int16_t duty)
{
    if (!trace.frozen) trace.duty=duty;
}
void st_motion_finish(uint8_t outcome)
{
    if (!trace.valid || trace.frozen) return;
    trace.outcome=outcome;
    if (outcome==SERVO_WRONG_WAY || outcome==SERVO_RUNAWAY) {
        trace.guard_ms=trace.last_ms;
        if (trace.sample_count)
            trace.guard_position=trace.samples[(trace.sample_next-1u)&3u].position;
        trace.fault=outcome==SERVO_RUNAWAY ? ST_SERVO_RUNAWAY : ST_SERVO_WRONG_WAY;
        trace.frozen=1;
    }
}
void st_motion_completion(uint8_t state, uint16_t event)
{
    if (!trace.valid || (trace.frozen && trace.completion_state)) return;
    trace.completion_ms=millis(); trace.completion_state=state;
    trace.completion_code=(uint8_t)event; trace.completion_param=(uint8_t)(event>>8);
}
const uint8_t *st_motion_data(void) { return (const uint8_t *)&trace; }

/* AF3.7 proposal: main-context, bounded RAM-only motion evidence. */
#ifndef EA9_MOTION_TRACE_H
#define EA9_MOTION_TRACE_H
#include <stdint.h>
#include <stddef.h>
#define ST_MOTION_BYTES 144u
#define ST_MOTION_SAMPLES 4u
#define ST_MS_REBASE 1u
#define ST_MS_HOLDING 2u
#define ST_MS_NEGATIVE 4u
#define ST_MF_DRY 1u
enum st_motion_completion {
    ST_MC_NONE=0, ST_MC_ATTEMPT=1, ST_MC_QUEUED=2, ST_MC_SUPPRESSED=3,
    ST_MC_QUEUE_FULL=4, ST_MC_TX_RETURN=5, ST_MC_ABORTED=6
};
struct st_motion_sample {
    uint32_t ms;
    int32_t position;
    int16_t duty; /* last motor_drive request before this read; zero while braking */
    uint8_t state, retargets;
};
/* Serialized directly only on the little-endian SAMD21. No pointers/padding.
 * Guard position is the read used by the guard, never the later final read.
 * Frozen guard fields cannot be replaced by a later leg/command/shutdown.
 * Completion fields separately record the first subsequent disposition.
 * All timestamps are wrapping uint32 millis, not a wall-clock/shutter clock. */
struct st_motion_trace {
    uint8_t version, valid, frozen, flags;
    uint32_t begin_ms;
    int32_t initial_start, initial_target, target, leg_start;
    uint32_t guard_ms;
    int32_t guard_position;
    int16_t duty;
    uint16_t command_operand;
    uint8_t command_op, accepted_op;
    uint16_t accepted_operand;
    int8_t direction;
    uint8_t retargets, state, outcome;
    uint16_t sample_count; /* saturates; ring retains latest min(count,4) */
    uint8_t sample_next, fault;
    uint32_t completion_ms;
    uint8_t completion_code, completion_param, completion_state, completion_reason;
    uint32_t last_ms, accepted_ms;
    struct st_motion_sample samples[ST_MOTION_SAMPLES];
    uint8_t reserved[32];
};
_Static_assert(sizeof(struct st_motion_sample)==12, "sample wire size");
_Static_assert(sizeof(struct st_motion_trace)==ST_MOTION_BYTES, "motion wire size");
_Static_assert(offsetof(struct st_motion_trace, samples)==64, "sample wire offset");
_Static_assert(offsetof(struct st_motion_trace, completion_ms)==48, "completion offset");
_Static_assert(offsetof(struct st_motion_trace, reserved)==112, "reserved offset");
void st_motion_command(uint8_t op, uint16_t operand);
void st_motion_begin(int32_t start, int32_t target, uint32_t ms, uint8_t dry);
void st_motion_sample(uint32_t ms, int32_t position);
/* packed = retarget count <<8 | ST_MS_*; called after retarget/rebase processing. */
void st_motion_leg(int32_t target, int32_t start, unsigned packed);
void st_motion_drive(int16_t duty);
void st_motion_finish(uint8_t outcome);
void st_motion_completion(uint8_t state, uint16_t event);
const uint8_t *st_motion_data(void);
#endif

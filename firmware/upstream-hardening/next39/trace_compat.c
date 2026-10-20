/* Observation-only inert hooks for retained control regression harnesses.
 * Their frozen peripheral shims do not link motion_trace.c or the new terminal
 * writer. Dedicated lanes33/34/35 test the real observation paths separately.
 * Weak definitions never override a production implementation linked by a test.
 */
#include <stdint.h>
#define MOCK __attribute__((weak))
MOCK void st_motion_command(uint8_t op, uint16_t operand) { (void)op; (void)operand; }
MOCK void st_motion_begin(int32_t start, int32_t target, uint32_t ms, uint8_t dry)
{ (void)start; (void)target; (void)ms; (void)dry; }
MOCK void st_motion_sample(uint32_t ms, int32_t position) { (void)ms; (void)position; }
MOCK void st_motion_leg(int32_t target, int32_t start, unsigned state)
{ (void)target; (void)start; (void)state; }
MOCK void st_motion_drive(int16_t duty) { (void)duty; }
MOCK void st_motion_finish(uint8_t outcome) { (void)outcome; }
MOCK void st_motion_completion(uint8_t state, uint16_t event) { (void)state; (void)event; }
MOCK const uint8_t *st_motion_data(void) { static uint32_t empty[36]; return (const uint8_t *)empty; }
MOCK void st_terminal(uint8_t kind, uint8_t value, uint32_t ms)
{ (void)kind; (void)value; (void)ms; }
MOCK void st_summary(uint8_t kind, uint8_t id, uint32_t ms)
{ (void)kind; (void)id; (void)ms; }
MOCK void st_record(uint32_t ms, uint32_t identity, uint32_t payload)
{ (void)ms; (void)identity; (void)payload; }

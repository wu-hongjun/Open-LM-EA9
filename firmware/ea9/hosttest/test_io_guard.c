#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "io_guard.h"
static uint32_t tick, step;
static unsigned releases;
uint32_t millis(void) { uint32_t t = tick; tick += step; return t; }
void motor_emergency_release(void) { releases++; }
int main(int argc, char **argv) {
    assert(argc == 2); unsigned polls = 0;
    if (!strcmp(argv[1], "ready")) {
        assert(EA9_IO_WAIT(1, EA9_IO_ENCODER));
        assert(EA9_IO_WAIT(++polls == 7, EA9_IO_ENCODER));
        assert(!ea9_io_faults() && !releases && polls == 7);
    } else {
        step = !strcmp(argv[1], "frozen") ? 0 : 1;
        if (!strcmp(argv[1], "wrap")) tick = UINT32_MAX;
        assert(!EA9_IO_WAIT((++polls, 0), EA9_IO_ENCODER));
        assert(ea9_io_faults() == EA9_IO_ENCODER && releases == 1);
        assert(polls <= EA9_IO_POLL_LIMIT);
        assert(!EA9_IO_WAIT(1, EA9_IO_ADC));
        ea9_io_trip(EA9_IO_ADC);
        assert(ea9_io_faults() == (EA9_IO_ENCODER | EA9_IO_ADC));
    }
    puts("bounded peripheral wait case passed"); return 0;
}

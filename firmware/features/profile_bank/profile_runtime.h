#ifndef OLA_PROFILE_RUNTIME_H
#define OLA_PROFILE_RUNTIME_H
#include "profile_bank.h"
/* Must complete before em_init, sensor/motor init, or E-mount interrupts. */
int profile_runtime_init(void);
/* Kept separate from hardware so the actual packet mutation is host tested. */
void profile_apply_record(const uint8_t *record);
extern uint16_t em_startup_aperture_av;
#endif

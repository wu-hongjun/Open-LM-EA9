/* Bounded candidate reference admission; not factory persistence.
 * SPDX-License-Identifier: MIT */
#ifndef AF_READINESS_H
#define AF_READINESS_H
#include "af_reference.h"
#define EA9_HOME_ATTEMPTS 2u
static inline uint8_t ea9_reference_admit(enum ea9_home_phase phase, uint8_t *attempts, uint8_t fresh_motion)
{
    if (*attempts >= EA9_HOME_ATTEMPTS ||
        !(phase == EA9_HOME_UNKNOWN || (phase == EA9_HOME_CANCELLED && fresh_motion))) return 0;
    ++*attempts;
    return 1;
}
#endif

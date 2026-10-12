/* Explicit experimental mechanical-reference policy. No flash or peripheral I/O.
 * SPDX-License-Identifier: MIT */
#ifndef EA9_AF_REFERENCE_H
#define EA9_AF_REFERENCE_H
#include <stdint.h>

enum ea9_home_phase { EA9_HOME_UNKNOWN, EA9_HOME_DRIVING, EA9_HOME_SETTLING,
                     EA9_HOME_READY, EA9_HOME_FAILED, EA9_HOME_CANCELLED };
struct ea9_home {
    enum ea9_home_phase phase;
    uint32_t phase_at, last_motion_at, samples;
    int32_t start, still_at;
    uint8_t outcome;
};
/* Drive/settle timing and noise band inherited upstream; not unit calibration. */
#define EA9_HOME_DRIVE_CAP_MS 300u
#define EA9_HOME_SETTLE_CAP_MS 500u
#define EA9_HOME_MIN_DRIVE_MS 40u
#define EA9_HOME_MIN_SETTLE_MS 20u
#define EA9_HOME_STILL_MS 40u
#define EA9_HOME_NOISE_COUNTS 6
#define EA9_HOME_WRONG_WAY_COUNTS 120
/* New conservative bound: settling must not become another travel operation. */
#define EA9_HOME_SETTLE_LIMIT_COUNTS 120

void ea9_home_begin(struct ea9_home *home, int32_t sample, uint32_t now);
enum ea9_home_phase ea9_home_sample(struct ea9_home *home, int32_t sample, uint32_t now);
void ea9_home_cancel(struct ea9_home *home);
/* READY establishes a software reference after drive and settle. A stationary
 * sensor alone cannot prove an electrical connection or a physical end stop. */
#endif

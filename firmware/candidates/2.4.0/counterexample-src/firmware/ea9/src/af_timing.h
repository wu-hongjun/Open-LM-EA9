/* Clock policy: recovered stock timing is evidence, not the runtime controller.
 * SPDX-License-Identifier: MIT */
#ifndef EA9_AF_TIMING_H
#define EA9_AF_TIMING_H
#include <stdint.h>
#define EA9_AF_CONTROL_STEP_MS 5u
#define EA9_AF_MAX_CONTROL_GAP_MS 40u
/* Exact nominal rationals at 48 MHz: overflow 60008/48 us, PID 660088/48 us.
 * They are configuration-derived; no hardware period has been measured here. */
#define EA9_STOCK_OVERFLOW_US_NUM 60008u
#define EA9_STOCK_PERIOD_US_DEN 48u
#define EA9_STOCK_PID_DIVIDER 11u
#define EA9_STOCK_TIMEOUT_CALLBACKS 301u
/* Polled controller uses elapsed time, never multiple catch-up steps at once. */
static inline uint32_t ea9_af_elapsed(uint32_t now, uint32_t previous) { return now - previous; }
#endif

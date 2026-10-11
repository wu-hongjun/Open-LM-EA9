/* Open LM-EA9 profile format v1. SPDX-License-Identifier: MIT */
#ifndef EA9_LENS_PROFILE_H
#define EA9_LENS_PROFILE_H
#include <stdint.h>
#define EA9_PROFILE_BYTES 256u
#ifndef EA9_PROFILE_ADDRESS
#define EA9_PROFILE_ADDRESS 0xa000u
#endif
extern const volatile uint8_t ea9_profile_blob[EA9_PROFILE_BYTES];
int ea9_profile_validate(const volatile uint8_t *p);
int ea9_profile_load(void);
int ea9_profile_load_from(const volatile uint8_t *p);
uint16_t ea9_profile_focal(void);
void ea9_profile_apply(void);
#endif

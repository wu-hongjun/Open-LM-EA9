/* Fixed camera aperture declaration; physical passive iris is unknown.
 * SPDX-License-Identifier: MIT */
#ifndef EA9_LENS_APERTURE_H
#define EA9_LENS_APERTURE_H
#include <stdint.h>
void lens_aperture_set(uint16_t declared_av);
uint16_t lens_aperture_value(void);
/* Foreground packet owner only. Negotiated EXIF omission is not iris sensing. */
void lens_aperture_publish(uint8_t include_exif);
#endif

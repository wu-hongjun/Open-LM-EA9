/* User-selected aperture reporting for a mechanically controlled lens. */
#ifndef REPORTED_APERTURE_H
#define REPORTED_APERTURE_H

#include <stdint.h>

void reported_aperture_init(void);
void reported_aperture_offer(const uint8_t *frame, uint16_t available);
void reported_aperture_commit(void);

#endif

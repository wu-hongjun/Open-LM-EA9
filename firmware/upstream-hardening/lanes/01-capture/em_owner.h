#ifndef EM_OWNER_H
#define EM_OWNER_H
#include <stdint.h>
#define EM_OWNER_CAPACITY 256u
struct em_owned_request {
    uint16_t length;
    uint8_t raw;
    uint8_t bytes[EM_OWNER_CAPACITY];
};
/* One active immutable frame + one first-wins pending frame. The caller must
 * mask interrupts for take/cancel. offer/cs/vd run in the serialized EIC ISR.
 * CS may invalidate a future send, but cannot retract bytes already shifted. */
struct em_owner {
    struct em_owned_request slot[2];
    volatile uint8_t active, pending, ready;
    volatile uint8_t phase, interrupted, receiving, capture;
    volatile uint8_t status_enabled;
    volatile uint16_t overflow;
};
void em_owner_cs(struct em_owner *, int level);
void em_owner_vd(struct em_owner *);
int em_owner_offer(struct em_owner *, const uint8_t *, uint16_t);
const struct em_owned_request *em_owner_take(struct em_owner *);
void em_owner_cancel(struct em_owner *);
int em_owner_status_begin(struct em_owner *);
int em_owner_status_valid(const struct em_owner *);
#endif

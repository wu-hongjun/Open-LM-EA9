#include "em_owner.h"
void em_owner_cs(struct em_owner *o, int level)
{
    o->receiving = (uint8_t)(level != 0);
    if (level) {
        o->capture = (uint8_t)(o->phase && o->status_enabled);
        o->interrupted = 1;
    }
}
void em_owner_vd(struct em_owner *o)
{
    if (o->pending && !o->receiving) o->ready = 1;
}
int em_owner_offer(struct em_owner *o, const uint8_t *p, uint16_t n)
{
    struct em_owned_request *r;
    uint16_t i;
    if (!p || n < 9u || n > EM_OWNER_CAPACITY) return 0;
    if (o->pending) {
        if (o->overflow != UINT16_MAX) o->overflow++;
        return 0;
    }
    r = &o->slot[o->active ^ 1u];
    for (i = 0; i < n; i++) r->bytes[i] = p[i];
    r->length = n;
    r->raw = o->capture;
    o->ready = (uint8_t)!r->raw;
    o->pending = 1;
    return 1;
}
const struct em_owned_request *em_owner_take(struct em_owner *o)
{
    if (!o->pending || !o->ready || o->receiving) return 0;
    o->active ^= 1u;
    o->pending = 0;
    return &o->slot[o->active];
}
void em_owner_cancel(struct em_owner *o)
{
    o->pending = o->ready = o->capture = o->phase = 0;
    o->interrupted = 1;
    o->status_enabled = 0;
}
int em_owner_status_begin(struct em_owner *o)
{
    if (!o->status_enabled || o->pending || o->receiving || o->phase) return 0;
    o->interrupted = 0;
    o->phase = 1;
    return 1;
}
int em_owner_status_valid(const struct em_owner *o)
{
    return o->phase && !o->interrupted && !o->receiving && !o->pending;
}

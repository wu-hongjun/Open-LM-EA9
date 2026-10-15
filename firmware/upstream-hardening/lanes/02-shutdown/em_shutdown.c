#include "em_shutdown.h"
#include "em_frame.h"
uint8_t em_shutdown_accept(struct em_shutdown *s, const uint8_t *p, uint16_t n)
{
    struct em_frame_view v;
    if (s->state != EM_SD_IDLE || em_frame_open(p,n,&v) != EM_FRAME_OK
        || v.length > EM_SHUTDOWN_CAP || p[3] != 2u || p[5] != 0x16u)
        return 0;
    for (uint16_t i=0;i<v.length;i++) s->request[i]=p[i];
    s->length=v.length;
    __asm__ volatile ("" ::: "memory"); /* publish snapshot before latch */
    s->state=EM_SD_PENDING;
    return 1;
}
uint8_t em_shutdown_begin(struct em_shutdown *s)
{
    if (s->state != EM_SD_PENDING) return 0;
    s->state=EM_SD_ACTIVE;
    return 1;
}

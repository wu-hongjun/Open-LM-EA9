#include "startup_trace.h"
#include <string.h>

struct event { uint32_t ms; uint8_t kind, id, cls, seq; uint16_t length, operand; };
static struct event events[ST_EVENTS];
static uint16_t dropped, rx_count, tx_count, fault;
static uint8_t count, flushed, next_page, boot, stage, connected, failed;
static uint8_t first_rx, last_rx, first_tx, last_tx, capability, capability_seen;
static uint32_t last_rx_ms;

static void put16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void put32(uint8_t *p, uint32_t v) { for (unsigned i=0;i<4;i++) p[i]=(uint8_t)(v>>(8*i)); }
uint32_t st_crc32(const uint8_t *p, unsigned n) {
    uint32_t crc=0xffffffffu;
    for (unsigned i=0;i<n;i++) {
        crc ^= p[i];
        for (unsigned k=0;k<8;k++) crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);
    }
    return crc^0xffffffffu;
}
static int erased(const uint8_t *p) {
    for (unsigned i=0;i<ST_PAGE_BYTES;i++) if (p[i]!=255) return 0;
    return 1;
}
void st_init(void) {
    uint8_t p[ST_PAGE_BYTES];
    count=flushed=next_page=0; dropped=rx_count=tx_count=fault=0;
    stage=connected=first_rx=last_rx=first_tx=last_tx=failed=capability_seen=0; capability=0;
    last_rx_ms=0;
    /* Skip every occupied/torn page. Never erase, repair or reprogram it. */
    for (unsigned i=0;i<ST_PAGE_COUNT;i++) {
        if (!st_read_page(ST_FLASH_BASE+i*ST_PAGE_BYTES,p)) { next_page=ST_PAGE_COUNT; break; }
        if (!erased(p)) next_page=(uint8_t)(i+1);
    }
    boot=(uint8_t)(next_page+1);
}
void st_note(uint8_t kind, uint8_t id, uint8_t cls, uint8_t seq,
             uint16_t length, uint16_t operand, uint32_t ms) {
    uint32_t key=st_lock();
    if (kind==ST_STAGE) stage=id;
    if (kind==ST_HANDSHAKE) { connected=1; stage=ST_CONNECTED; }
    if (kind==ST_FAULT) fault=id;
    if (kind==ST_RX) {
        if (!rx_count) first_rx=id;
        if (rx_count!=65535) rx_count++;
        last_rx=id; last_rx_ms=ms;
        if (id==8 && cls==2 && length>7) { capability=(uint8_t)(operand>>8); capability_seen=1; }
    }
    if (kind==ST_TX) {
        if (!tx_count) first_tx=id;
        if (tx_count!=65535) tx_count++;
        last_tx=id;
    }
    if (count<ST_EVENTS) events[count++]=(struct event){ms,kind,id,cls,seq,length,operand};
    else if (dropped!=65535) dropped++;
    st_unlock(key);
}
static int append(uint8_t p[ST_PAGE_BYTES], uint8_t type, uint8_t n) {
    uint8_t old[ST_PAGE_BYTES];
    if (failed || next_page>=ST_PAGE_COUNT) return 0;
    uint32_t address=ST_FLASH_BASE+next_page*ST_PAGE_BYTES;
    if (address<ST_FLASH_BASE || address+ST_PAGE_BYTES>ST_FLASH_END) return 0;
    unsigned index=next_page++;
    if (!st_read_page(address,old) || !erased(old)) { failed=1; return 0; }
    memcpy(p,"E9S2",4); p[4]=1; p[5]=type; p[6]=boot; p[7]=n;
    put16(p+8,(uint16_t)index); p[10]=p[11]=0;
    put32(p+60,st_crc32(p,60));
    /* The slot is consumed even if the write fails. No retry. */
    if (!st_write_page(address,p)) { failed=1; return 0; }
    return 1;
}
void st_flush(int allowed, uint32_t ms, uint32_t rx_bytes,
              uint16_t errors, uint16_t status, uint8_t pins) {
    if (!allowed || failed || next_page>=ST_PAGE_COUNT) return;
    uint8_t p[ST_PAGE_BYTES];
    uint32_t key=st_lock();
    /* At most twelve event pages and one summary; sixteen writes per image. */
    while (flushed<count && next_page<ST_PAGE_COUNT) {
        memset(p,0,sizeof(p));
        uint8_t n=0;
        while (n<4 && flushed<count) {
            struct event *e=&events[flushed++]; uint8_t *q=p+12+12*n++;
            put32(q,e->ms); q[4]=e->kind; q[5]=e->id; q[6]=e->cls; q[7]=e->seq;
            put16(q+8,e->length); put16(q+10,e->operand);
        }
        if (!append(p,2,n)) break;
    }
    memset(p,0,sizeof(p));
    uint8_t *q=p+12;
    q[0]=stage; q[1]=connected; put16(q+2,fault); put32(q+4,ms);
    put16(q+8,rx_count); put16(q+10,tx_count); put32(q+12,rx_bytes);
    put16(q+16,errors); put16(q+18,status); put32(q+20,last_rx_ms);
    q[24]=first_rx; q[25]=last_rx; q[26]=first_tx; q[27]=last_tx;
    q[28]=capability; q[29]=pins; put16(q+30,dropped);
    q[32]=capability_seen;
    (void)append(p,1,1);
    st_unlock(key);
}
int st_preserve_first_window(const uint8_t *p, unsigned n) {
    if (!n || p[0]!=0xf0) return 0;
    if (n>1 && p[1]<9) return 0;
    if (n>2 && p[2]!=0) return 0;
    if (n>3 && p[3]!=2) return 0;
    if (n>1 && n>=p[1]) {
        unsigned length=p[1]; uint16_t sum=0;
        if (p[length-1]!=0x55) return 0;
        for (unsigned i=1;i<=length-4;i++) sum+=p[i];
        if (sum!=(uint16_t)(p[length-3]|((uint16_t)p[length-2]<<8))) return 0;
    }
    return 1;
}

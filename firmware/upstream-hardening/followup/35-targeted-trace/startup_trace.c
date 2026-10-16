#define STARTUP_TRACE_IMPLEMENTATION
#include "startup_trace.h"
#include "motion_trace.h"
#include <stddef.h>
#include <string.h>

#include "trace_format.h"
static struct {
    struct summary summary;
    uint8_t count,tail,sealed,next_page,cohort,failed,terminal_count;
    struct event events[ST_EVENTS];
} ram;
#define s ram.summary
#define events ram.events
#define r_count ram.count
#define r_tail ram.tail
#define r_sealed ram.sealed
#define r_next_page ram.next_page
#define r_cohort ram.cohort
#define r_failed ram.failed
#define r_terminal_count ram.terminal_count
static void inc(uint16_t *p) { if (*p!=65535) ++*p; }
uint32_t st_crc32(const uint8_t *p, unsigned n) {
    uint32_t crc=0xffffffffu;
    while (n--) { crc^=*p++; for (unsigned k=0;k<8;k++) crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u); }
    return crc^0xffffffffu;
}
static int erased(const uint8_t *p) { for (unsigned i=0;i<64;i++) if (p[i]!=255) return 0; return 1; }
void st_init(void) {
    uint8_t p[64];
    memset(&ram,0,sizeof(ram));
    for (unsigned i=0;i<16;i++) {
        if (!st_read_page(ST_FLASH_BASE+i*64,p)) { r_next_page=16; break; }
        if (!erased(p)) r_next_page=(uint8_t)(i+1);
    }
    r_cohort=r_next_page+1;
}
void st_summary(uint8_t kind,uint8_t id,uint32_t ms) {
    uint32_t key=st_lock();
    if (kind==ST_STAGE) s.stage=id;
    if (kind==ST_RX) { if (!s.rx_count) s.first_rx=id; inc(&s.rx_count); s.last_rx=id; s.last_rx_ms=ms; }
    if (kind==ST_TX) { if (!s.tx_count) s.first_tx=id; inc(&s.tx_count); s.last_tx=id; }
    if (kind==ST_CAPABILITY) { s.capability=id; s.capability_seen=1; }
    inc(&s.filtered);
    st_unlock(key);
}
void st_record(uint32_t ms,uint32_t identity,uint32_t payload) {
    uint8_t kind=identity, id=identity>>8, cls=identity>>16;
    uint32_t key=st_lock();
    if (kind==ST_HANDSHAKE) { s.connected=1; s.stage=ST_CONNECTED; }
    if (kind==ST_FAULT) s.fault=id;
    if (kind==ST_SHUTDOWN) s.shutdown=1;
    if (((kind==ST_OWNER_CS || kind==ST_OWNER_PHASE) && !(cls&1u))
        || ((kind==ST_TX_START || kind==ST_TX_RETURN) && !(cls&6u))) inc(&s.filtered);
    else if (!r_sealed) {
        uint32_t words[3]={ms,identity,payload};
        memcpy(&events[r_tail],words,12);
        r_tail=(r_tail+1)&31u;
        if (r_count<32) ++r_count; else inc(&s.dropped);
    }
    st_unlock(key);
}
void st_note(uint8_t kind,uint8_t id,uint8_t cls,uint8_t seq,uint16_t length,uint16_t operand,uint32_t ms) {
    if (kind==ST_STAGE || kind==ST_CS || kind==ST_RX || kind==ST_TX || kind==ST_CAPABILITY)
        st_summary(kind,id,ms);
    else st_record(ms,(uint32_t)kind|((uint32_t)id<<8)|((uint32_t)cls<<16)|((uint32_t)seq<<24),
        (uint32_t)length|((uint32_t)operand<<16));
}
static int append(struct page *p) {
    uint8_t old[64];
    if (r_failed || r_next_page>=16) return 0;
    uint32_t address=ST_FLASH_BASE+r_next_page*64u;
    p->slot=r_next_page++; /* Consume even a r_failed or torn write, never retry. */
    if (!st_read_page(address,old) || !erased(old)) { r_failed=1; return 0; }
    memcpy(p->magic,"E9S3",4); p->version=3; p->cohort=r_cohort;
    p->crc=st_crc32((const uint8_t *)p,60);
    if (!st_write_page(address,(const uint8_t *)p)) { r_failed=1; return 0; }
    return 1;
}
void st_flush(int allowed,uint32_t ms,uint32_t rx_bytes,uint16_t errors,uint16_t status,uint8_t pins) {
    if (!allowed || r_failed || r_sealed || r_next_page>=16) return;
    uint32_t key=st_lock();
    r_sealed=1;
    /* Keep four append slots for three shutdown boundaries and a later fault. */
    unsigned budget=r_next_page<11 ? 11-r_next_page : 0;
    s.motion_chunks=budget>=3 ? 3 : 0;
    budget-=s.motion_chunks;
    s.retained=r_count; s.planned=budget*4<r_count ? budget*4 : r_count;
    s.ms=ms; s.rx_bytes=rx_bytes; s.errors=errors; s.status=status; s.pins=pins;
    struct page p={.type=1,.n=1};
    memcpy(p.data,&s,48);
    if (!append(&p)) { st_unlock(key); return; }
    for (unsigned i=0;i<s.motion_chunks;i++) {
        memset(&p,0,64); p.type=3; p.n=1; p.chunk=i;
        memcpy(p.data,st_motion_data()+48*i,48);
        if (!append(&p)) { st_unlock(key); return; }
    }
    /* Retain latest planned slice, chronologically; capacity omission is explicit. */
    for (unsigned i=0;i<s.planned;) {
        memset(&p,0,64); p.type=2; p.chunk=i/4;
        while (p.n<4 && i<s.planned) {
            unsigned slot=(r_tail+32-s.planned+i++)&31u;
            memcpy(p.data+12*p.n++,&events[slot],12);
        }
        if (!append(&p)) break;
    }
    st_unlock(key);
}
void st_terminal(uint8_t kind,uint8_t value,uint32_t ms) {
    if (!r_sealed) return;
    uint32_t key=st_lock();
    struct page p={.type=4,.n=1};
    p.data[0]=kind; p.data[1]=value; p.data[2]=s.fault; p.data[3]=++r_terminal_count;
    memcpy(p.data+4,&ms,4);
    append(&p);
    st_unlock(key);
}
void st_inhibit_fault(uint8_t reason) { uint32_t key=st_lock(); if (!s.fault) s.fault=reason; st_unlock(key); }
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


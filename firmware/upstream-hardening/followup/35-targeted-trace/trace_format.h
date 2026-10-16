#ifndef EA9_TRACE_FORMAT_H
#define EA9_TRACE_FORMAT_H
#include <stdint.h>
#include <stddef.h>
/* Typed little-endian wire layout; the target and host tests assert it. */
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error trace_v3_requires_little_endian
#endif
struct event { uint32_t ms; uint8_t kind,id,cls,seq; uint16_t length,operand; };
struct summary {
    uint32_t ms,rx_bytes,last_rx_ms;
    uint16_t rx_count,tx_count,errors,status,dropped,filtered;
    uint8_t stage,connected,fault,pins,first_rx,last_rx,first_tx,last_tx;
    uint8_t capability,capability_seen,shutdown,retained,planned,motion_chunks,reserved[10];
};
struct page { uint8_t magic[4],version,type,cohort,n; uint16_t slot; uint8_t chunk,reserved; uint8_t data[48]; uint32_t crc; };
typedef char layout[(sizeof(struct event)==12 && sizeof(struct summary)==48 && sizeof(struct page)==64 && offsetof(struct page,data)==12 && offsetof(struct page,crc)==60 && offsetof(struct summary,rx_count)==12 && offsetof(struct summary,stage)==24 && offsetof(struct summary,planned)==36 && offsetof(struct event,length)==8)?1:-1];

#endif

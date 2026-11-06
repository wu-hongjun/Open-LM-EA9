#include "probe.h"
#include "stock_packets.h"
#include <string.h>

static uint16_t get16(const uint8_t *s)
{
    return (uint16_t)(s[0] | (uint16_t)s[1] << 8);
}

static void put16(uint8_t *d, uint16_t value)
{
    d[0] = (uint8_t)value;
    d[1] = (uint8_t)(value >> 8);
}

static void put32(uint8_t *d, uint32_t value)
{
    put16(d, (uint16_t)value);
    put16(d + 2, (uint16_t)(value >> 16));
}

static uint16_t checksum(const uint8_t *frame, uint16_t length)
{
    uint16_t sum = 0;
    for (uint16_t i = 1; i < length - 3; ++i) sum += frame[i];
    return sum;
}

static bool valid_frame(const uint8_t *bytes, uint16_t count, uint16_t length)
{
    return length >= 9 && length <= count && count <= PROBE_WINDOW && bytes[0] == 0xf0
        && bytes[length - 1] == 0x55 && checksum(bytes, length) == get16(bytes + length - 3);
}

void probe_count(uint16_t *counter)
{
    if (*counter != UINT16_MAX) ++*counter;
}

void probe_open(struct probe *p, bool preserved_prefix)
{
    if (preserved_prefix) p->flags |= FIRST_PREFIX;
    p->flags |= CS_RISE;
}

static bool init_shape(uint8_t id, uint16_t length)
{
    switch (id) {
    case 0x01: return length >= 41;
    case 0x03: case 0x04: case 0x05: case 0x06: return false;
    case 0x07: case 0x0c: case 0x0d: case 0x10: case 0x3f: return length >= 10;
    case 0x08: return length >= 17;
    case 0x09: return length >= 13;
    case 0x0a: return length == 25;
    case 0x0b: case 0x34: return length >= 11;
    case 0x3d: return length >= 32;
    default: return true; /* Unknown well-framed requests are useful evidence. */
    }
}

void probe_close(struct probe *p, const uint8_t *bytes, uint16_t count, bool invalid, uint32_t now)
{
    p->flags |= CS_FALL;
    if (!count && !invalid) return;

    uint16_t length = count >= 3 ? get16(bytes + 1) : 0;
    if (invalid || !valid_frame(bytes, count, length)) {
        probe_count(&p->invalid);
        return;
    }
    struct probe_mark mark = { now, length, bytes[5] };
    if (bytes[3] == 1 && ((mark.id == 3 && (length == 29 || length == 32))
                          || (mark.id == 4 && length >= 22))) {
        if (p->flags & FINAL_ECHO) {
            if (!p->first_normal.length) p->first_normal = mark;
            p->status_seq = (uint8_t)(bytes[4] + 1u);
            p->activity_ms = now;
            p->has_activity = true;
        }
        return;
    }
    if (bytes[3] != 2) return;

    /* Known queries need the documented minimum shape before dispatch. */
    if (!init_shape(mark.id, length)) {
        probe_count(&p->invalid);
        return;
    }
    if (!(p->flags & FINAL_ECHO) && mark.id != 0x16) p->last_rx = mark;
    p->activity_ms = now;
    p->has_activity = true;
    if (p->pending.mark.length) {
        probe_count(&p->drops);
        return;
    }
    p->pending.mark = mark;
    memcpy(p->pending.frame, bytes, length);
}

bool probe_take(struct probe *p, struct probe_request *request)
{
    if (!p->pending.mark.length) return false;
    request->mark = p->pending.mark;
    memcpy(request->frame, p->pending.frame, request->mark.length);
    p->pending.mark.length = 0;
    return true;
}

static uint16_t packet(uint8_t id, uint8_t *reply)
{
    for (unsigned i = 0; i < sizeof(stock_packets) / sizeof(stock_packets[0]); ++i) {
        const struct stock_packet *p = &stock_packets[i];
        if (p->bytes[5] == id) {
            memcpy(reply, p->bytes, p->length);
            return p->length;
        }
    }
    return 0;
}

static void seal(uint8_t *frame, uint16_t length)
{
    put16(frame + 1, length);
    put16(frame + length - 3, checksum(frame, length));
    frame[length - 1] = 0x55;
}

uint16_t probe_reply(const struct probe_request *request, uint8_t reply[PROBE_REPLY])
{
    uint8_t id = request->mark.id;
    uint16_t n = request->mark.length;
    switch (id) {
    case 0x0a:
        if (n != 25) return 0;
        /* The final echo preserves the entire validated request. */
        memcpy(reply, request->frame, n);
        return n;
    case 0x16:
        if (n < 9 || n > PROBE_REPLY) return 0;
        memcpy(reply, request->frame, n);
        return n;
    case 0x05: case 0x06:
        return 0; /* Only the VD schedule produces these. */
    default:
        break;
    }

    uint16_t length = packet(id, reply);
    if (!length) return 0;
    if (id == 0x0c) reply[6] = 0; /* Stock refuses the speed change. */
    if (id == 0x1b) {
        put16(reply + 6, 4608);
        put16(reply + 8, 4608);
    }
    if (id == 0x34) {
        if (n < 11) return 0;
        reply[7] = request->frame[6];
        reply[8] = request->frame[7];
    }
    seal(reply, length);
    return length;
}

bool probe_sent(struct probe *p, const struct probe_request *request, uint16_t length,
                enum probe_tx outcome, uint32_t txc_ms)
{
    uint8_t id = request->mark.id;
    if (outcome < TX_SHIFTED) {
        probe_count(&p->drops);
        return false;
    }
    struct probe_mark tx = { txc_ms, length, id };
    if (!(p->flags & FINAL_ECHO) && id != 0x16) p->last_txc = tx;
    if (outcome != TX_RELEASED) return false;
    if (id == 0x16) return true;
    if (!(p->flags & FINAL_ECHO)) {
        p->paired_rx = request->mark;
        p->paired_tx = tx;
        if (id == 1) p->flags |= CAPABILITIES;
        if (id == 7) p->flags |= IDENTITY;
        if (id == 0x0a) {
            p->flags |= FINAL_ECHO;
            p->status_seq = (uint8_t)(request->frame[4] + 1u);
        }
    }
    return false;
}

void probe_vd(struct probe *p)
{
    probe_count(&p->vd);
    if (p->flags & FINAL_ECHO) p->status_due = true;
}

uint16_t probe_status(uint8_t id, uint8_t seq, uint8_t reply[PROBE_REPLY])
{
    uint16_t length = packet(id, reply);
    if (!length) return 0;
    reply[4] = seq;
    if (id == 5) {
        put16(reply + 6, 4608);
        put16(reply + 8, 4608);
    } else {
        put16(reply + 0x20, 620);
        put16(reply + 0x22, 0x2006);
        /* Fixed placeholders at the stock lower travel bound. */
        put16(reply + 0x08, 4144);
        put16(reply + 0x1a, 4144);
    }
    seal(reply, length);
    return length;
}

enum probe_reason probe_timeout(const struct probe *p, uint32_t now, uint32_t ready_ms)
{
    if (!(p->flags & BUS_READY)) return now >= 8000 ? FIRST_CLOSE_TIMEOUT : 0;
    if (!(p->flags & FINAL_ECHO) && now - ready_ms >= 12000) return INIT_DEADLINE;
    uint32_t last = p->has_activity && p->activity_ms >= ready_ms ? p->activity_ms : ready_ms;
    return now - last >= 4000 ? INACTIVITY : 0;
}

static void mark(uint8_t *d, const struct probe_mark *m)
{
    d[0] = m->id;
    put16(d + 2, m->length);
    put32(d + 4, m->ms);
}

void probe_encode(const struct probe *p, uint8_t slot, enum probe_reason reason,
                  uint32_t now, uint8_t page[PROBE_PAGE])
{
    memset(page, 0, PROBE_PAGE);
    memcpy(page, "E9SP", 4);
    page[4] = 1;
    page[5] = slot;
    page[6] = (uint8_t)reason;
    page[7] = p->flags;
    put32(page + 8, now);
    mark(page + 12, &p->last_rx);
    mark(page + 20, &p->paired_rx);
    mark(page + 28, &p->paired_tx);
    mark(page + 36, &p->last_txc);
    mark(page + 44, &p->first_normal);
    put16(page + 52, p->invalid);
    put16(page + 54, p->drops);
    put16(page + 56, p->uart_errors);
    put16(page + 58, p->vd);

    uint32_t crc = UINT32_MAX;
    for (unsigned i = 0; i < 60; ++i) {
        crc ^= page[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1u) ? 0xedb88320u : 0);
    }
    put32(page + 60, ~crc);
}

bool probe_persist(const struct probe *p, enum probe_reason reason, uint32_t now)
{
    /* No page for a silent cap boot. An observed VD edge or CS edge suffices. */
    if (!(p->flags & (CS_RISE | CS_FALL)) && !p->vd) return false;
    uint8_t page[PROBE_PAGE];
    /* Append after the highest non-erased page, including a torn one. */
    for (uint32_t end = PROBE_END; end > PROBE_BASE; end -= PROBE_PAGE) {
        if (!probe_read_page(end - PROBE_PAGE, page)) return false;
        unsigned i = 0;
        while (i < PROBE_PAGE && page[i] == UINT8_MAX) ++i;
        if (i == PROBE_PAGE && end > PROBE_BASE + PROBE_PAGE) continue;
        uint32_t address = i == PROBE_PAGE ? PROBE_BASE : end;
        if (address == PROBE_END) return false;
        probe_encode(p, (uint8_t)((address - PROBE_BASE) / PROBE_PAGE), reason, now, page);
        return probe_write_page(address, page);
    }
    return false;
}

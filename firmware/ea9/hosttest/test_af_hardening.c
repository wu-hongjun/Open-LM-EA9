/* Offline regressions of the production command boundary and motion owner.
 * This includes main.c to exercise dispatch rather than only pure policy. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define main ea9_firmware_entry
#include "../src/main.c"
#undef main
#include "emount_packets.h"

struct host_pm host_pm;
extern void sim_reset(void);
extern double sim_pos;
extern int sim_noise, sim_stop_lo, sim_stop_hi;
extern int16_t sim_current_duty(void);
extern uint32_t host_millis;
extern void host_body_frame(const uint8_t *, uint16_t);
extern void host_frame_sync(void);
extern int host_pad_to, sent_n;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
static int scenario, samples, injected;
extern void (*sim_read_hook)(void);
static void fault_after_admission(void) { if (g_af_state.active) ea9_io_trip(EA9_IO_ENCODER); }
static void invalid_after_admission(void) { if (g_af_state.active) sim_pos = INT32_MIN; }
static uint32_t irq_mask;
static unsigned irq_entries;
static unsigned query_refills;
static void (*irq_deferred)(void);

uint32_t host_get_primask(void) { return irq_mask; }
void host_disable_irq(void) { irq_mask = 1; ++irq_entries; }
void host_set_primask(uint32_t state)
{
    irq_mask = state;
    if (!state && irq_deferred) {
        void (*callback)(void) = irq_deferred;
        irq_deferred = NULL;
        callback();
    }
}

/* Only the declared frame is checksummed; the shim supplies bus padding. */
static void seal(uint8_t *frame, uint16_t len)
{
    uint16_t sum = 0;
    frame[1] = (uint8_t)len;
    frame[2] = (uint8_t)(len >> 8);
    for (uint16_t i = 1; i <= len - 4; ++i) sum += frame[i];
    frame[len - 3] = (uint8_t)sum;
    frame[len - 2] = (uint8_t)(sum >> 8);
    frame[len - 1] = 0x55;
}
static void command(uint8_t op, uint16_t target)
{
    uint8_t frame[27] = {0xF0, 0, 0, 1, 0, 4};
    uint16_t len = op == EM_OP_STOP ? 23 : 27;
    frame[19] = op == EM_OP_STOP ? EM_REC_STOP : EM_REC_MOVE;
    frame[20] = (uint8_t)target; frame[21] = (uint8_t)(target >> 8);
    seal(frame, len); host_body_frame(frame, len);
}
static void deferred_stop(void) { command(EM_OP_STOP, 0); injected = 1; }
static void count_park(void) { ++injected; }
static void deferred_query(void)
{
    uint8_t frame[25] = {0xF0, 0, 0, 1, 0, 4};
    frame[19] = EM_REC_Q_D2POS; frame[20] = 0xCD; frame[21] = 0xAB;
    seal(frame, sizeof frame); host_body_frame(frame, sizeof frame); injected = 1;
}
static uint16_t query_operand(unsigned index)
{
    return (uint16_t)(FOCUS_EM06_LO + index * 100u);
}
static void numbered_query(unsigned index)
{
    uint8_t frame[25] = {0xF0, 0, 0, 1, 0, 4};
    uint16_t operand = query_operand(index);
    frame[19] = EM_REC_Q_POS2D;
    frame[20] = (uint8_t)operand; frame[21] = (uint8_t)(operand >> 8);
    seal(frame, sizeof frame); host_body_frame(frame, sizeof frame);
}
static void refill_queries(void)
{
    /* Keep the producer armed until the foreground function returns.  The
     * assertion makes the old unbounded drain fail instead of hanging. */
    assert(query_refills < EM_QUERY_Q);
    numbered_query(EM_QUERY_Q + query_refills++);
    if (query_refills == 1) deferred_stop();
    irq_deferred = refill_queries;
}
static void expect_query_answers(unsigned first)
{
    unsigned seen = 0;
    em_handshake_done = 1;
    for (unsigned n = 0; n < EM_QUERY_Q && seen < EM_QUERY_Q; n++) {
        int before = sent_n;
        host_frame_sync(); em_poll();
        assert(sent_n == before + 2);
        const uint8_t *frame = sent[before + 1];
        for (unsigned offset = 45; offset < sent_len[before + 1] - 3u;) {
            if (frame[offset] == EM_REC_STOP) { offset += 2; continue; }
            assert(seen < EM_QUERY_Q && frame[offset] == EM_REC_Q_POS2D);
            uint16_t answer = (uint16_t)frame[offset + 1] | (uint16_t)frame[offset + 2] << 8;
            assert(answer == focus_distance_code(focus_em06_to_counts(query_operand(first + seen)),
                                                 ea9_profile_focal()));
            seen++; offset += 3;
        }
    }
    assert(seen == EM_QUERY_Q);
}

void em_uart_disable(void) {}
void vdd_init(void) {}
uint16_t vdd_read_mv(void) { return 3150; }
void vdd_read_burst(uint16_t *lo, uint16_t *hi, uint16_t ms)
{ (void)ms; *lo = *hi = 3150; }
void vdd_track_reset(void) {}
void vdd_track_result(uint16_t *lo, uint16_t *hi) { *lo = *hi = 3150; }
void vdd_track_sample(void)
{
    ++samples;
    if (!injected && samples == 4 && (scenario == 8 || scenario == 9)) {
        command(EM_OP_MOVE, focus_counts_to_em06(1300)); injected = 1;
    }
    if (!injected && samples == 4 && scenario == 10) deferred_stop();
}

int main(int argc, char **argv)
{
    assert(argc == 2); scenario = atoi(argv[1]); sim_reset(); sim_noise = 0;
    sim_stop_lo = 0; sim_stop_hi = 5952; em_init();
    if (scenario <= 5) {
        struct em_focus_cmd result;
        uint8_t frame[40] = {0xF0, 0, 0, 1, 0, 4};
        frame[19] = EM_REC_MOVE; frame[20] = 0xEC; frame[21] = 0x12;
        seal(frame, 27);
        uint16_t supplied = 27;
        if (scenario == 0) frame[24] ^= 0x01;  /* checksum corruption */
        if (scenario == 1) { frame[1] = 40; supplied = 28; } /* complete record, incomplete frame */
        if (scenario == 2) { frame[3] = 3; seal(frame, 27); } /* unsupported class */
        if (scenario == 3) frame[26] = 0;       /* missing terminator */
        if (scenario == 4) frame[2] = 1;       /* nonzero high length */
        if (scenario == 5) host_pad_to = 48;   /* valid frame with non-frame trailing bytes */
        host_body_frame(frame, supplied);
        if (scenario == 5) {
            assert(em_take_focus_cmd(&result));
            assert(result.op == EM_OP_MOVE && result.target == 0x12EC);
        } else assert(!em_take_focus_cmd(&result));
    } else if (scenario == 6 || scenario == 11) {
        struct em_focus_cmd first, second;
        command(EM_OP_MOVE, 4400);
        irq_deferred = deferred_stop;
        if (scenario == 11) irq_mask = 1;
        assert(em_take_focus_cmd(&first));
        assert(first.op == EM_OP_MOVE && first.target == 4400 && irq_entries);
        if (scenario == 11) {
            assert(irq_mask == 1 && !injected);
            host_set_primask(0);
        }
        assert(injected && em_take_focus_cmd(&second) && second.op == EM_OP_STOP);
        assert(!em_take_focus_cmd(&second));
    } else if (scenario == 7) {
        g_af_state.fault_reason = SERVO_STALL;
        command(EM_OP_STOP, 0); focus_service();
        assert(g_af_state.fault_reason == SERVO_STALL && sim_current_duty() == 0);
        em_handshake_done = 1; int before = sent_n; host_frame_sync(); em_poll();
        assert(sent_n == before + 2 && sent_len[before + 1] == 50);
        assert(sent[before + 1][45] == EM_REC_STOP);
    } else if (scenario == 8 || scenario == 9) {
        g_homed = 1; sim_pos = 0; abs_encoder_track_reset();
        struct em_focus_cmd first = { .op = scenario == 8 ? EM_OP_SCAN : EM_OP_DRIVE,
            .scan_a = FOCUS_EM06_LO + 250, .scan_b = FOCUS_EM06_LO + 450,
            .scan_speed = 40, .drive_vel = 5000 };
        focus_exec(&first);
        assert(injected && g_next_pending && g_next.op == EM_OP_MOVE);
        assert(!ea9_af_faulted(&g_af_state) && !g_af_state.active);
        assert(ea9_data[EA9_OFF_06 + 0x1F] == EM_SCAN_IDLE);
        em_handshake_done = 1; int before = sent_n; host_frame_sync(); em_poll();
        assert(sent_len[before + 1] == 48); /* replaced operation has no success event */
        focus_service(); before = sent_n; host_frame_sync(); em_poll();
        assert(sent_len[before + 1] == 50 && sent[before + 1][45] == EM_REC_MOVE);
    } else if (scenario == 10) {
        g_homed = 1; sim_pos = 0; abs_encoder_track_reset(); g_last_op = EM_OP_MOVE;
        struct servo_cfg capped = UPSTREAM_PROFILE; capped.retarget_max = 0;
        assert(focus_run(1500, focus_counts_to_em06(1500), &capped) == SERVO_ABORTED);
        assert(injected && g_abort_by_stop && !ea9_af_faulted(&g_af_state));
        assert(sim_current_duty() == 0 && samples <= 6);
    } else if (scenario == 12) {
        uint8_t frame[25] = {0xF0, 0, 0, 1, 0, 4}, tag; uint16_t operand;
        frame[19] = EM_REC_Q_POS2D; frame[20] = 0x34; frame[21] = 0x12;
        seal(frame, sizeof frame); host_body_frame(frame, sizeof frame);
        irq_deferred = deferred_query;
        assert(em_take_query(&tag, &operand) && tag == EM_REC_Q_POS2D && operand == 0x1234);
        assert(injected && em_take_query(&tag, &operand) && tag == EM_REC_Q_D2POS && operand == 0xABCD);
        assert(!em_take_query(&tag, &operand));
    } else if (scenario == 13) {
        uint8_t reply[11] = {0xF0, 0, 0, 2, 5, 0x08, 0xA5, 0x80};
        seal(reply, sizeof reply); host_body_frame(reply, sizeof reply);
        command(EM_OP_MOVE, 4500); /* a normal frame must not replace the init request bytes */
        int before = sent_n; em_poll();
        assert(sent_n == before + 1 && sent[before][5] == 0x08);
        assert(!em_m08_aperture_on); /* capability comes from the init snapshot */
    } else if (scenario == 14) {
        g_homed = 1; sim_pos = 0; abs_encoder_track_reset();
        g_next = (struct em_focus_cmd){ .op = EM_OP_MOVE, .target = focus_counts_to_em06(1300) };
        g_next_pending = 1;
        command(EM_OP_STOP, 0); focus_service();
        assert(!g_next_pending && g_focus_moves == 0 && g_stops_idle == 1);
        assert(sim_current_duty() == 0 && samples == 0);
    } else if (scenario == 15) {
        em_vd_edges = 1; focus_report_at(12);
        uint8_t first[7]; memcpy(first, &ea9_data[EA9_OFF_06 + 0x26], sizeof first);
        for (unsigned i = 0; i < 7; ++i) assert(!first[i]); /* Seed, not a jump from zero. */
        for (int position = 16; position <= 100; position += 4) focus_report_at(position);
        assert(!memcmp(first, &ea9_data[EA9_OFF_06 + 0x26], sizeof first));
        em_vd_edges = 2; focus_report_at(100);
        for (unsigned i = 0; i < 7; ++i) assert(!ea9_data[EA9_OFF_06 + 0x26 + i]);
        for (unsigned i = 0; i < 17; ++i) focus_report_at(100);
        em_vd_edges = 3; focus_report_at(108);
        assert(ea9_data[EA9_OFF_06 + 0x2B] == 0 && ea9_data[EA9_OFF_06 + 0x2C] == 2);
    } else if (scenario == 16) {
        uint8_t frame[65] = {0xF0, 0, 0, 2, 0, EM_ID_SHUTDOWN};
        seal(frame, sizeof frame); em_set_park_handler(count_park);
        int before = sent_n; host_body_frame(frame, sizeof frame); em_poll();
        assert(!injected && sent_n == before && !em_shutdown_acked);
    } else if (scenario == 17) {
        g_homed = 1; sim_pos = 0; abs_encoder_track_reset();
        for (unsigned i = 0; i < EM_QUERY_Q; i++) numbered_query(i);
        unsigned before = irq_entries;
        irq_deferred = refill_queries;
        focus_answer_queries();
        assert(query_refills == EM_QUERY_Q && irq_entries - before == EM_QUERY_Q);
        assert(irq_deferred == refill_queries); /* producer has not run dry */
        irq_deferred = NULL;
        focus_service();
        assert(injected && g_stops_idle == 1 && g_focus_moves == 0 && sim_current_duty() == 0);
        expect_query_answers(0);
        before = irq_entries;
        focus_answer_queries(); /* the refilled FIFO remains for the next pass */
        assert(irq_entries - before == EM_QUERY_Q);
        expect_query_answers(EM_QUERY_Q);
        uint8_t tag; uint16_t operand;
        assert(!em_take_query(&tag, &operand));
    } else if (scenario == 18) {
        g_homed = 1; sim_pos = 0; abs_encoder_track_reset();
        sim_read_hook = fault_after_admission;
        struct em_focus_cmd move = { .op = EM_OP_MOVE, .target = 4500 };
        focus_exec(&move); sim_read_hook = NULL;
        assert(g_af_state.fault_reason == SERVO_IO_FAULT && !g_af_state.active);
        assert(sim_current_duty() == 0);
        struct em_focus_cmd stop = { .op = EM_OP_STOP }; focus_exec(&stop);
        assert(g_stops_idle == 1);
    } else if (scenario == 19) {
        g_homed = 1; sim_pos = 0; abs_encoder_track_reset();
        sim_read_hook = invalid_after_admission;
        struct em_focus_cmd move = { .op = EM_OP_MOVE, .target = 4500 };
        focus_exec(&move); sim_read_hook = NULL;
        assert(g_af_state.fault_reason == SERVO_IO_FAULT && !g_af_state.active);
        assert(sim_current_duty() == 0);
    } else if (scenario == 20) {
        em_vd_edges = 1;
        uint8_t before[48]; memcpy(before, &ea9_data[EA9_OFF_06], sizeof before);
        focus_report_at(INT32_MIN);
        assert(ea9_io_faults() && g_af_state.fault_reason == SERVO_IO_FAULT);
        assert(!memcmp(before, &ea9_data[EA9_OFF_06], sizeof before));
    } else return 2;
    printf("AF hardening scenario %d passed\n", scenario); return 0;
}

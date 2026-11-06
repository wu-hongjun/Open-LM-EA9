/* SAMD21E17A transport for the motor-disabled startup probe. */
#include "sam.h"
#include "probe.h"

#define PORTA (PORT->Group[0])
#define USART (SERCOM1->USART)
#define CS_BODY (1u << 2)
#define VD_BODY (1u << 3)
#define CS_LENS (1u << 10)
#define MOTOR_PADS ((1u << 8) | (1u << 9) | (1u << 18) | (1u << 19))
#define CPU_HZ 48000000u
#define SYNC_BUDGET 262144u
#define TX_BUDGET 524288u

#define WAIT_SYNC(condition) do { \
    uint32_t left = SYNC_BUDGET; \
    while (condition) if (!--left) return false; \
} while (0)

static struct probe state;
static volatile uint32_t ticks;
static uint8_t rx[2][PROBE_WINDOW];
static unsigned rx_bank;
static uint16_t rx_length;
static bool rx_bad;
static volatile bool rx_fault;
static volatile uint32_t edge_generation;
static bool window_open;
static bool uart_configured;

static uint32_t lock(void)
{
    uint32_t key = __get_PRIMASK();
    __disable_irq();
    return key;
}

void SysTick_Handler(void)
{
    ++ticks;
}

static void pins_init(void)
{
    /* Clear GPIO output enables first, then detach any inherited mux/pull. */
    PORTA.DIRCLR.reg = MOTOR_PADS;
    PORTA.PINCFG[8].reg = 0;
    PORTA.PINCFG[9].reg = 0;
    PORTA.PINCFG[18].reg = 0;
    PORTA.PINCFG[19].reg = 0;

    PORTA.OUTSET.reg = (1u << 7) | (1u << 11);
    PORTA.OUTCLR.reg = CS_LENS | (1u << 16) | (1u << 23);
    static const uint8_t outputs[] = {7, 10, 11, 16, 23};
    for (unsigned i = 0; i < sizeof(outputs); ++i) {
        PORTA.PINCFG[outputs[i]].reg = 0;
        PORTA.DIRSET.reg = 1u << outputs[i];
    }
}

static bool clock_init(void)
{
    NVMCTRL->CTRLB.bit.RWS = 1;
    SYSCTRL->DFLLCTRL.reg = SYSCTRL_DFLLCTRL_ENABLE;
    WAIT_SYNC(!SYSCTRL->PCLKSR.bit.DFLLRDY);
    SYSCTRL->DFLLMUL.reg = SYSCTRL_DFLLMUL_CSTEP(1) | SYSCTRL_DFLLMUL_FSTEP(1);
    uint32_t coarse = (*(volatile const uint32_t *)0x00806024u >> 26) & 63u;
    SYSCTRL->DFLLVAL.reg = SYSCTRL_DFLLVAL_COARSE(coarse == 63 ? 31 : coarse)
                        | SYSCTRL_DFLLVAL_FINE(512);
    SYSCTRL->DFLLCTRL.reg = SYSCTRL_DFLLCTRL_ENABLE;
    WAIT_SYNC(!SYSCTRL->PCLKSR.bit.DFLLRDY);
    GCLK->GENDIV.reg = GCLK_GENDIV_ID(0) | GCLK_GENDIV_DIV(1);
    WAIT_SYNC(GCLK->STATUS.bit.SYNCBUSY);
    GCLK->GENCTRL.reg = GCLK_GENCTRL_ID(0) | GCLK_GENCTRL_SRC_DFLL48M | GCLK_GENCTRL_GENEN;
    WAIT_SYNC(GCLK->STATUS.bit.SYNCBUSY);

    NVIC_SetPriority(SysTick_IRQn, 3);
    SysTick->LOAD = CPU_HZ / 1000u - 1u;
    SysTick->VAL = 0;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_TICKINT_Msk
                  | SysTick_CTRL_ENABLE_Msk;
    return true;
}

static bool eic_init(void)
{
    PM->APBAMASK.reg |= PM_APBAMASK_EIC;
    GCLK->CLKCTRL.reg = GCLK_CLKCTRL_ID_EIC | GCLK_CLKCTRL_CLKEN;
    WAIT_SYNC(GCLK->STATUS.bit.SYNCBUSY);

    PORTA.PMUX[1].reg = PORT_PMUX_PMUXE(MUX_PA02A_EIC_EXTINT2)
                     | PORT_PMUX_PMUXO(MUX_PA03A_EIC_EXTINT3);
    PORTA.PINCFG[2].reg = PORT_PINCFG_PMUXEN | PORT_PINCFG_INEN;
    PORTA.PINCFG[3].reg = PORT_PINCFG_PMUXEN | PORT_PINCFG_INEN;
    EIC->CTRL.reg = EIC_CTRL_SWRST;
    WAIT_SYNC(EIC->CTRL.bit.SWRST || EIC->STATUS.bit.SYNCBUSY);
    EIC->CONFIG[0].reg = (0xbu << 8) | (0x9u << 12); /* Both CS edges, VD rising. */
    EIC->INTFLAG.reg = CS_BODY | VD_BODY;
    EIC->INTENSET.reg = CS_BODY | VD_BODY;
    EIC->CTRL.reg = EIC_CTRL_ENABLE;
    WAIT_SYNC(EIC->STATUS.bit.SYNCBUSY);
    NVIC_SetPriority(EIC_IRQn, 1);
    return true;
}

static bool uart_init(void)
{
    PM->APBCMASK.reg |= PM_APBCMASK_SERCOM1;
    GCLK->CLKCTRL.reg = GCLK_CLKCTRL_ID_SERCOM1_CORE | GCLK_CLKCTRL_CLKEN;
    WAIT_SYNC(GCLK->STATUS.bit.SYNCBUSY);

    PORTA.OUTSET.reg = 1u << 1; /* RX pull-up */
    PORTA.PMUX[0].reg = PORT_PMUX_PMUXE(MUX_PA00D_SERCOM1_PAD0)
                     | PORT_PMUX_PMUXO(MUX_PA01D_SERCOM1_PAD1);
    PORTA.PINCFG[0].reg = PORT_PINCFG_PMUXEN;
    PORTA.PINCFG[1].reg = PORT_PINCFG_PMUXEN | PORT_PINCFG_INEN | PORT_PINCFG_PULLEN;
    USART.CTRLA.reg = SERCOM_USART_CTRLA_SWRST;
    WAIT_SYNC(USART.CTRLA.bit.SWRST || USART.SYNCBUSY.bit.SWRST);
    USART.CTRLA.reg = 0x40100004u;
    USART.CTRLB.reg = SERCOM_USART_CTRLB_TXEN | SERCOM_USART_CTRLB_RXEN;
    WAIT_SYNC(USART.SYNCBUSY.reg);
    USART.BAUD.reg = 0xc000u; /* 48 MHz, 16x arithmetic, 750000 baud. */
    uart_configured = true;
    USART.INTENSET.reg = SERCOM_USART_INTENSET_RXC;
    NVIC_SetPriority(SERCOM1_IRQn, 0);
    NVIC_EnableIRQ(SERCOM1_IRQn);
    USART.CTRLA.reg |= SERCOM_USART_CTRLA_ENABLE;
    WAIT_SYNC(USART.SYNCBUSY.reg);
    return true;
}

/* Called by the USART IRQ or with interrupts masked at an EIC edge. */
static void drain(void)
{
    for (unsigned i = 0; i < 4 && USART.INTFLAG.bit.RXC; ++i) {
        uint8_t value = (uint8_t)USART.DATA.reg;
        if (rx_length < PROBE_WINDOW) rx[rx_bank][rx_length++] = value;
        else rx_bad = true;
    }
    if (USART.INTFLAG.bit.ERROR) {
        uint16_t errors = USART.STATUS.reg;
        rx_bad = true;
        probe_count(&state.uart_errors);
        USART.STATUS.reg = errors;
        USART.INTFLAG.reg = SERCOM_USART_INTFLAG_ERROR;
    }
    if (USART.INTFLAG.bit.RXC) {
        rx_bad = rx_fault = true;
        USART.INTENCLR.reg = SERCOM_USART_INTENCLR_RXC;
    }
}

void SERCOM1_Handler(void)
{
    drain();
}

static void cs_open(void)
{
    /* At the first rise, the RX IRQ may already have the opener's prefix. */
    bool preserve = !(state.flags & (CS_RISE | CS_FALL))
                 && !rx_bad && rx_length && rx[rx_bank][0] == 0xf0;
    if (!preserve) {
        rx_length = 0;
        rx_bad = false;
    }
    window_open = true;
    probe_open(&state, preserve);
}

void EIC_Handler(void)
{
    uint32_t flags = EIC->INTFLAG.reg;
    if (flags & CS_BODY) {
        uint32_t key = lock();
        EIC->INTFLAG.reg = CS_BODY;
        ++edge_generation;
        drain();
        if (PORTA.IN.reg & CS_BODY) {
            if (window_open) rx_bad = true; /* At least one edge coalesced. */
            else cs_open();
        } else {
            /* Permit a first latched fall that occurred before IRQ delivery. */
            bool missed_open = !window_open && (state.flags & CS_FALL);
            const uint8_t *closed = rx[rx_bank];
            uint16_t count = rx_length;
            bool bad = rx_bad || missed_open;
            uint32_t closed_ms = ticks;
            rx_bank ^= 1u;
            rx_length = 0;
            rx_bad = false;
            window_open = false;
            /* Allow RX to continue in the other bank during checksum/copy. */
            __set_PRIMASK(key);
            probe_close(&state, closed, count, bad, closed_ms);
            key = lock();
        }
        __set_PRIMASK(key);
    }
    if (flags & VD_BODY) {
        EIC->INTFLAG.reg = VD_BODY;
        probe_vd(&state);
    }
}

static bool delay_us(uint32_t us)
{
    uint32_t left = SYNC_BUDGET;
    uint32_t cycles = us * (CPU_HZ / 1000000u);
    uint32_t last = SysTick->VAL;
    while (cycles) {
        if (!--left) return false;
        uint32_t now = SysTick->VAL;
        uint32_t elapsed = last >= now ? last - now : last + SysTick->LOAD + 1u - now;
        if (elapsed >= cycles) return true;
        cycles -= elapsed;
        last = now;
    }
    return true;
}

static bool receiving(void)
{
    return (PORTA.IN.reg & CS_BODY) || (EIC->INTFLAG.reg & CS_BODY);
}

static enum probe_tx send(const uint8_t *data, uint16_t count, uint32_t *txc)
{
    uint32_t key = lock();
    if (receiving()) {
        __set_PRIMASK(key);
        return TX_BUSY;
    }
    uint32_t edge = edge_generation;
    PORTA.OUTSET.reg = CS_LENS;
    __set_PRIMASK(key);

    enum probe_tx result = TX_ABORTED;
    uint32_t left = TX_BUDGET;
    USART.INTFLAG.reg = SERCOM_USART_INTFLAG_TXC;
    for (uint16_t i = 0; i < count; ++i) {
        while (!USART.INTFLAG.bit.DRE) if (!--left) goto release;
        if (receiving() || edge_generation != edge || rx_fault) goto release;
        USART.DATA.reg = data[i];
    }
    while (!USART.INTFLAG.bit.TXC) if (!--left) goto release;
    *txc = ticks;
    result = TX_SHIFTED;
    if (!delay_us(100)) goto release;
    key = lock();
    if (!receiving() && edge_generation == edge && !rx_fault) result = TX_RELEASED;
    PORTA.OUTCLR.reg = CS_LENS;
    __set_PRIMASK(key);
    return result;

release:
    PORTA.OUTCLR.reg = CS_LENS;
    return result;
}

static void stop(enum probe_reason reason)
{
    __disable_irq();
    NVIC_DisableIRQ(EIC_IRQn);
    NVIC_DisableIRQ(SERCOM1_IRQn);
    PORTA.OUTCLR.reg = CS_LENS;
    PORTA.DIRCLR.reg = 1u;
    PORTA.PINCFG[0].reg = 0;
    if (uart_configured) {
        USART.INTENCLR.reg = SERCOM_USART_INTENCLR_RXC;
        USART.CTRLA.reg &= ~SERCOM_USART_CTRLA_ENABLE;
    }
    SysTick->CTRL = 0;
    (void)probe_persist(&state, reason, ticks);
    for (;;) __WFI();
}

static void startup(void)
{
    if (!clock_init() || !eic_init() || !uart_init()) stop(PERIPHERAL_FAULT);
    uint32_t key = lock();
    /* Arm reception before raising lens CS. Do not clear an already latched edge. */
    if (!(EIC->INTFLAG.reg & CS_BODY) && (PORTA.IN.reg & CS_BODY)) {
        drain();
        cs_open();
    }
    PORTA.OUTSET.reg = CS_LENS;
    NVIC_EnableIRQ(EIC_IRQn);
    __set_PRIMASK(key);
}

int main(void)
{
    __disable_irq();
    pins_init();
    NVIC_DisableIRQ(SERCOM1_IRQn);
    NVIC_DisableIRQ(EIC_IRQn);
    __enable_irq();
    startup();

    struct probe_request request;
    uint8_t reply[PROBE_REPLY];
    uint32_t ready_ms = 0, first_close_ms = 0, loop_ticks = ticks, work = 0;
    bool saw_close = false, have_request = false;
    for (;;) {
        uint32_t key = lock();
        uint32_t now = ticks;
        if (now != loop_ticks) {
            loop_ticks = now;
            work = 0;
        }
        if (++work >= SYNC_BUDGET || rx_fault) stop(PERIPHERAL_FAULT);
        if (!saw_close && (state.flags & CS_FALL)) {
            saw_close = true;
            first_close_ms = now;
        }
        if (!(state.flags & BUS_READY) && saw_close && now - first_close_ms >= 50u && !receiving()) {
            PORTA.OUTCLR.reg = CS_LENS;
            state.flags |= BUS_READY;
            ready_ms = now;
        }
        enum probe_reason reason = probe_timeout(&state, now, ready_ms);
        if (reason) stop(reason);
        bool idle = (state.flags & BUS_READY) && !receiving();
        if (idle && !have_request) have_request = probe_take(&state, &request);
        bool status = idle && !have_request && state.status_due;
        uint8_t seq = state.status_seq;
        if (status) state.status_due = false;
        __set_PRIMASK(key);

        if (idle && have_request) {
            uint16_t n = probe_reply(&request, reply);
            uint32_t txc = 0;
            enum probe_tx outcome = n ? send(reply, n, &txc) : TX_BUSY;
            if (n && outcome == TX_BUSY) continue; /* Try once the window closes. */
            have_request = false;
            if (!n) continue;
            key = lock();
            bool shutdown = probe_sent(&state, &request, n, outcome, txc);
            if (shutdown) stop(SHUTDOWN);
            if (outcome != TX_RELEASED) stop(TX_FAULT);
            __set_PRIMASK(key);
        } else if (status) {
            if (!delay_us(10)) stop(PERIPHERAL_FAULT);
            uint32_t txc;
            uint16_t n = probe_status(5, seq, reply);
            enum probe_tx outcome = send(reply, n, &txc);
            if (outcome == TX_BUSY) continue;
            if (outcome != TX_RELEASED) stop(TX_FAULT);
            if (!delay_us(300)) stop(PERIPHERAL_FAULT);
            n = probe_status(6, seq, reply);
            outcome = send(reply, n, &txc);
            if (outcome == TX_BUSY) continue;
            if (outcome != TX_RELEASED) stop(TX_FAULT);
            key = lock();
            state.flags |= STATUS_PAIR;
            __set_PRIMASK(key);
        }
    }
}

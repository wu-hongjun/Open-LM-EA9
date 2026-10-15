#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "board.h"
#include "em_uart.h"
#include "em_eic.h"
#include "em_frame.h"
#include "emount.h"
#include "startup_trace.h"

void host_window_payload(const uint8_t *, uint16_t);
void host_set_cs_pin(int);
uint32_t millis(void);
unsigned startup_snapshot(uint8_t *);
unsigned startup_receiving(void);

#define SERCOM_USART_INTFLAG_ERROR 128u
#define SERCOM_USART_INTENCLR_RXC 4u
struct reg { uint32_t reg; struct { uint8_t RXC, ERROR; } bit; };
static struct { struct { struct reg INTFLAG, DATA, STATUS, INTENCLR; } USART; } uart;
#define EMSERCOM (&uart)
struct eic_reg { uint32_t reg; struct { unsigned SWRST, SYNCBUSY; } bit; };
static struct { struct eic_reg CTRL, STATUS, CONFIG[1], WAKEUP, INTFLAG, INTENSET; } eic;
#define EIC (&eic)
static struct { struct eic_reg APBAMASK; } pm;
static struct { struct eic_reg CLKCTRL, STATUS; } gclk;
#define PM (&pm)
#define GCLK (&gclk)
#define PM_APBAMASK_EIC 1u
#define GCLK_CLKCTRL_ID(x) (x)
#define GCLK_CLKCTRL_ID_EIC_Val 5u
#define GCLK_CLKCTRL_GEN_GCLK0 0u
#define GCLK_CLKCTRL_CLKEN 0x4000u
#define PORT_PMUX_PMUXE(x) (x)
#define PORT_PMUX_PMUXO(x) ((x)<<4)
#define MUX_PA02A_EIC_EXTINT2 0u
#define MUX_PA03A_EIC_EXTINT3 0u
#define EIC_CTRL_SWRST 1u
#define EIC_CTRL_ENABLE 2u
#define EIC_CONFIG_BOTH_FILT 0xbu
#define EIC_CONFIG_RISE_FILT 0x9u
#define EIC_IRQn 4u
static void (*g_cs_edge)(int);
static void (*g_vd_edge)(void);
static unsigned mask, in_irq, armed, cut, deliveries, prior_set;
static unsigned eic_enabled = 1; /* Exercise inherited enabled state too. */
static uint8_t fifo[2];
static unsigned fifo_n;
static const char *event;
static uint8_t first[11];
void handoff_hook(unsigned);
static void service(void);
void NVIC_DisableIRQ(unsigned irq) { if (irq != EIC_IRQn) abort(); eic_enabled = 0; }
static void NVIC_EnableIRQ(unsigned irq) { if (irq != EIC_IRQn) abort(); eic_enabled = 1; service(); }
static void NVIC_SetPriority(unsigned irq, unsigned prio) { if (irq != EIC_IRQn || prio != 1) abort(); }
static uint8_t probe_data(void)
{
    uint8_t b = fifo[0];
    if (fifo_n == 2) fifo[0] = fifo[1];
    if (fifo_n) fifo_n--;
    uart.USART.INTFLAG.bit.RXC = fifo_n != 0;
    return b;
}
static void probe_clear_error(void) { uart.USART.INTFLAG.bit.ERROR = 0; }
void motor_inhibit(void) {}
#include "uart.inc"
#include "eic.inc"
#include "eic_setup.inc"

static void service(void)
{
    if (mask || in_irq) return;
    in_irq = 1;
    /* Priority zero SERCOM is serviced before priority one EIC. */
    if (fifo_n || uart.USART.INTFLAG.bit.ERROR) SERCOM1_Handler();
    if (eic_enabled && eic.INTFLAG.reg) { deliveries++; EIC_Handler(); }
    in_irq = 0;
}
uint32_t st_lock(void) { unsigned prior = mask; mask = 1; return prior; }
void st_unlock(uint32_t prior) { mask = prior; service(); }
static void byte_arrives(uint8_t b)
{
    if (fifo_n == 2) {
        uart.USART.INTFLAG.bit.ERROR = 1;
        uart.USART.STATUS.reg = 4; /* Synthetic BUFOVF fact, not register timing. */
    } else fifo[fifo_n++] = b;
    uart.USART.INTFLAG.bit.RXC = 1;
    service();
}
void host_rx_load(const uint8_t *p, unsigned n)
{
    for (unsigned i = 0; i < n; i++) byte_arrives(p[i]);
}
int em_eic_receive_pending(void) { return !!(eic.INTFLAG.reg & 4u); }
void handoff_hook(unsigned point)
{
    if (point == 4 && !strcmp(event, "prior-mask")) { mask = 1; prior_set = 1; }
    if (!armed || point != cut) return;
    armed = 0;
    if (!strcmp(event, "rise") || !strcmp(event, "prior-mask") || !strcmp(event, "rise-uart1")) {
        host_set_cs_pin(1); eic.INTFLAG.reg |= 4u;
    } else if (!strcmp(event, "fall") || !strcmp(event, "rise-fall")) {
        /* Two transitions coalesce to the same one-bit pending fact. */
        host_set_cs_pin(0); eic.INTFLAG.reg |= 4u;
    } else if (!strcmp(event, "vd")) eic.INTFLAG.reg |= 8u;
    else if (!strcmp(event, "both")) { host_set_cs_pin(0); eic.INTFLAG.reg |= 12u; }
    if (!strcmp(event, "uart1") || !strcmp(event, "uart2") || !strcmp(event, "overflow") || !strcmp(event, "rise-uart1")) {
        byte_arrives(0x42);
        if (!strcmp(event, "uart2") || !strcmp(event, "overflow")) byte_arrives(0x43);
        if (!strcmp(event, "overflow")) byte_arrives(0x44);
    } else if (!strcmp(event, "tail")) byte_arrives(first[10]);
    service();
}
static void seal(uint8_t *p, unsigned n)
{
    unsigned sum = 0;
    p[0]=0xf0; p[1]=n; p[3]=2; p[4]=0x11; p[5]=8; p[n-1]=0x55;
    for (unsigned i=1;i<n-3;i++) sum += p[i];
    p[n-3]=sum; p[n-2]=sum>>8;
}
int main(int argc, char **argv)
{
    if (argc != 4) return 2;
    const char *initial = argv[1]; event = argv[2]; cut = (unsigned)atoi(argv[3]);
    armed = cut != 0;
    seal(first, sizeof(first));
    if (!strcmp(initial,"valid")) host_window_payload(first, sizeof(first));
    else if (!strcmp(initial,"truncated")) host_window_payload(first, 6);
    else if (!strcmp(initial,"tail-missing")) host_window_payload(first, 10);
    else if (!strcmp(initial,"noise")) { uint8_t noise[8] = {1,2,3,4,5,6,7,8}; host_window_payload(noise,8); }
    em_init();
    unsigned return_mask=mask, return_deliveries=deliveries;
    if (prior_set) st_unlock(0);
    uint8_t owned[256] = {0}; unsigned n = startup_snapshot(owned);
    struct em_frame_view view;
    unsigned valid = n && em_frame_open(owned,n,&view)==EM_FRAME_OK;
    unsigned whole = n==sizeof(first) && !memcmp(owned,first,n);
    printf("{\"initial\":\"%s\",\"event\":\"%s\",\"cut\":%u,\"ownedBytes\":%u,"
           "\"validOwned\":%s,\"wholeFirst\":%s,\"receiving\":%u,\"maskAtReturn\":%u,"
           "\"deliveriesAtReturn\":%u,\"deliveries\":%u,\"uartErrors\":%u,\"rxLength\":%u}\n",
           initial,event,cut,n,valid?"true":"false",whole?"true":"false",startup_receiving(),
           return_mask,return_deliveries,deliveries,(unsigned)em_rx_errors,em_uart_rx_len());
    return 0;
}

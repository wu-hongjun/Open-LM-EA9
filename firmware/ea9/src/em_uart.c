/* em_uart.c -- SERCOM1 at 750 kbaud, 8N1, LSB first.
 *
 * The stock firmware runs this port through ASF4's async USART driver with the
 * DMAC moving both directions (a 16-byte RX ring plus DMAC channel 1 into a
 * 255-byte buffer at 0x20000694).  This does the same job with an RX interrupt
 * and a polled transmitter, which is a deliberate simplification:
 *
 *   - RX: one byte every 13.3 us at 750 kbaud is ~640 cycles at 48 MHz, so a
 *     handler must admit a byte within that budget. It includes buffer/error
 *     bookkeeping and a bounded drain guard; no worst-case cycle measurement
 *     or complete hardware scheduling proof has been established here.
 *   - TX: the longest frame is message 0x08 at 210 bytes = 2.8 ms, and it is
 *     sent once during init.  The recurring frames are 105 and 48 bytes, i.e.
 *     1.4 ms and 0.6 ms at the nominal upstream 16.6 ms frame period. Blocking
 *     waits for TXC before releasing chip select; it also delays foreground
 *     control, and its actual camera timing still needs qualification.
 *
 * If the servo loop later turns out to be starved by the 1.4 ms send, this is
 * the file to put DMA back into -- nothing above it depends on the blocking.
 */
#include "board.h"
#include "clock.h"
#include "delay.h"
#include "em_uart.h"
#ifdef EA9_AF_BUILD
#include "io_guard.h"
#endif

#define EMSERCOM ((Sercom *)EM_SERCOM_ADDR)

static volatile uint8_t  g_rx[EM_RX_BUF_LEN];
static volatile uint16_t g_rx_len;
static volatile uint8_t  g_disabled;

volatile uint32_t em_rx_bytes;
volatile uint32_t em_rx_errors;
volatile uint16_t em_rx_status;
volatile uint32_t em_t_first_byte;

static void em_uart_sync(void)
{
#ifdef EA9_AF_BUILD
	(void)EA9_IO_WAIT_MASK(!EMSERCOM->USART.SYNCBUSY.reg, EA9_IO_UART, EA9_IO_LINK_FAULTS);
#else
	while (EMSERCOM->USART.SYNCBUSY.reg) {
	}
#endif
}

void em_uart_init(void)
{
	clock_enable_peripheral(GCLK_CLKCTRL_ID_SERCOM1_CORE_Val, PM_APBCMASK_SERCOM1);
#ifdef EA9_AF_BUILD
	if (ea9_io_faults() & EA9_IO_LINK_FAULTS) return;
#endif

	/* PA00 = PAD[0] = TX, PA01 = PAD[1] = RX, both mux D.  PA01 needs its
	 * input buffer enabled or the receiver sees a constant high. */
	PORT->Group[0].PINCFG[EM_PIN_TX].reg = PORT_PINCFG_PMUXEN;
	/* PULL-UP on RX.  A UART idle line is high, and the receiver is now
	 * enabled before the body starts driving PA01 (emount.c), so without a
	 * pull the line floats and the SERCOM manufactures start bits out of
	 * noise.  That is a hazard this file's own change introduced, and it
	 * would show up as bytes arriving from a body that never spoke. */
	PORT->Group[0].OUTSET.reg = (1u << EM_PIN_RX);
	PORT->Group[0].PINCFG[EM_PIN_RX].reg = PORT_PINCFG_PMUXEN | PORT_PINCFG_INEN
	                                       | PORT_PINCFG_PULLEN;
	PORT->Group[0].PMUX[EM_PIN_TX / 2].reg =
	        PORT_PMUX_PMUXE(EM_MUX_UART) | PORT_PMUX_PMUXO(EM_MUX_UART);

	EMSERCOM->USART.CTRLA.reg = SERCOM_USART_CTRLA_SWRST;
#ifdef EA9_AF_BUILD
	if (!EA9_IO_WAIT_MASK(!(EMSERCOM->USART.CTRLA.bit.SWRST || EMSERCOM->USART.SYNCBUSY.bit.SWRST), EA9_IO_UART, EA9_IO_LINK_FAULTS)) return;
#else
	while (EMSERCOM->USART.CTRLA.bit.SWRST || EMSERCOM->USART.SYNCBUSY.bit.SWRST) {
	}
#endif

	EMSERCOM->USART.CTRLA.reg = EM_CTRLA;      /* recovered verbatim */
	EMSERCOM->USART.CTRLB.reg = EM_CTRLB;
	em_uart_sync();
#ifdef EA9_AF_BUILD
	if (ea9_io_faults() & EA9_IO_LINK_FAULTS) return;
#endif
	EMSERCOM->USART.BAUD.reg  = EM_BAUD;

	EMSERCOM->USART.INTENSET.reg = SERCOM_USART_INTENSET_RXC;

	/* NVIC first, THEN the peripheral.  The other order leaves a gap in
	 * which the SERCOM can receive with nobody to service it, and its
	 * two-byte buffer overflows -- BUFOVF was set on both failing boots.
	 * SERCOM1 is IRQ 10 and the stock leaves it at reset priority 0, above
	 * the TC4 servo tick at 2 and TCC1 at 3, which is what keeps bus traffic
	 * ahead of the control loop (NOTES.md §13). */
	NVIC_EnableIRQ(SERCOM1_IRQn);

	EMSERCOM->USART.CTRLA.reg |= SERCOM_USART_CTRLA_ENABLE;
	em_uart_sync();
}

void SERCOM1_Handler(void)
{
#ifdef EA9_AF_BUILD
	unsigned rx_budget = 512;
#endif
	while (EMSERCOM->USART.INTFLAG.bit.RXC) {
#ifdef EA9_AF_BUILD
		if (!--rx_budget) {
			EMSERCOM->USART.INTENCLR.reg = SERCOM_USART_INTENCLR_RXC;
			ea9_io_trip(EA9_IO_UART); return;
		}
#endif
		uint8_t b = (uint8_t)EMSERCOM->USART.DATA.reg;

		em_rx_bytes++;
		if (!em_t_first_byte) {
			em_t_first_byte = millis();
		}
		if (g_rx_len < EM_RX_BUF_LEN) {
			g_rx[g_rx_len++] = b;
		}
	}
	/* An overrun or framing error latches ERROR and stalls nothing, but the
	 * flag must be cleared or STATUS keeps reporting it. */
	if (EMSERCOM->USART.INTFLAG.bit.ERROR) {
		uint16_t st = EMSERCOM->USART.STATUS.reg;

		em_rx_errors++;
		em_rx_status |= st;
		EMSERCOM->USART.INTFLAG.reg = SERCOM_USART_INTFLAG_ERROR;
		EMSERCOM->USART.STATUS.reg  = st;
	}
}

void em_uart_rx_reset(void)
{
	/* Poison the head of the buffer at the start of every window.
	 *
	 * The length counter says every window delivers 32 bytes regardless of
	 * what the frame declares, and the bytes past the frame are sometimes
	 * zero and sometimes look like the tail of another frame.  Three
	 * explanations fit that and they predict different bytes; a counter
	 * cannot separate them.  With the buffer pre-filled, anything still
	 * reading EM_RX_POISON was never received, and the question is settled
	 * by looking rather than by arguing.
	 *
	 * 64 byte writes in an interrupt that fires every 8 ms, on a 48 MHz
	 * part: under 3 us, against a 16 ms frame period. */
	for (unsigned i = 0; i < EM_RX_POISON_LEN; i++) {
		g_rx[i] = EM_RX_POISON;
	}
	g_rx_len = 0;
}

uint16_t em_uart_rx_len(void)
{
	return g_rx_len;
}

const uint8_t *em_uart_rx_buf(void)
{
	return (const uint8_t *)g_rx;
}

void em_uart_disable(void)
{
	g_disabled = 1;
	EMSERCOM->USART.CTRLA.reg &= ~(uint32_t)SERCOM_USART_CTRLA_ENABLE;
	em_uart_sync();
}

uint8_t em_uart_send(const uint8_t *buf, uint16_t len)
{
	if (g_disabled) {
		return 0;
	}
	EMSERCOM->USART.INTFLAG.reg = SERCOM_USART_INTFLAG_TXC;

	for (uint16_t i = 0; i < len; i++) {
#ifdef EA9_AF_BUILD
		if (!EA9_IO_WAIT_MASK(EMSERCOM->USART.INTFLAG.bit.DRE, EA9_IO_UART, EA9_IO_LINK_FAULTS)) return 0;
#else
		while (!EMSERCOM->USART.INTFLAG.bit.DRE) {
		}
#endif
		EMSERCOM->USART.DATA.reg = buf[i];
	}
#ifdef EA9_AF_BUILD
	return EA9_IO_WAIT_MASK(EMSERCOM->USART.INTFLAG.bit.TXC, EA9_IO_UART, EA9_IO_LINK_FAULTS);
#else
	while (!EMSERCOM->USART.INTFLAG.bit.TXC) {
	}
	return 1;
#endif
}

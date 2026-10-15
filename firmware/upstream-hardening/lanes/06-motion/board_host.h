#ifndef BOARD_H
#define BOARD_H
#include <stdint.h>
typedef union { uint32_t reg; struct { unsigned PMUXEN:1;unsigned INEN:1;unsigned SWRST:1;unsigned RXC:1;unsigned DRE:1;unsigned SYNCBUSY:1;unsigned PMUXE:4; } bit; } host_reg;
struct port_host { struct { host_reg PINCFG[32],PMUX[16],OUTSET,OUTCLR,DIRSET,DIRCLR; } Group[1]; };
struct tcc_host {host_reg SYNCBUSY,CC[4],CTRLA,WAVE,PER;};
struct pm_host {host_reg APBCMASK;};
struct gclk_host {host_reg CLKCTRL,STATUS;};
extern struct port_host port_mem;
extern struct tcc_host tcc_mem;
extern struct pm_host pm_mem;
extern struct gclk_host gclk_mem;
#define PORT (&port_mem)
#define TCC0 (&tcc_mem)
#define PM (&pm_mem)
#define GCLK (&gclk_mem)
#define MOTOR_PIN_WO0 8
#define MOTOR_PIN_WO1 9
#define MOTOR_PIN_WO2 18
#define MOTOR_PIN_WO3 19
#define MOTOR_MUX_WO01 4
#define MOTOR_MUX_WO23 5
#define PORT_PINCFG_PMUXEN 1
#define PORT_PINCFG_INEN 2
#define PORT_PMUX_PMUXE(x) (x)
#define PORT_PMUX_PMUXO(x) ((x)<<4)
#define PM_APBCMASK_TCC0 1
#define GCLK_CLKCTRL_ID(x) (x)
#define GCLK_CLKCTRL_ID_TCC0_TCC1_Val 1
#define GCLK_CLKCTRL_GEN_GCLK0 1
#define GCLK_CLKCTRL_CLKEN 1
#define TCC_CTRLA_SWRST 1
#define MOTOR_TCC_CTRLA_STOCK 1
#define TCC_CTRLA_PRESCALER(x) (x)
#define MOTOR_PWM_PRESCALER 1
#define TCC_WAVE_WAVEGEN_NPWM 1
#define MOTOR_PWM_PERIOD 2000
#define TCC_CTRLA_ENABLE 2
#define ENC_COUNTS 16384
#define ENC_POS_OFFSET 4096
#endif

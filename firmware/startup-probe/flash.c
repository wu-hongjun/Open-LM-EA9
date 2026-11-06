/* Bounded PBC/WP-only writer, adapted from upstream-diagnostic. */
#include "sam.h"
#include "probe.h"

#define NVM_ERRORS (NVMCTRL_STATUS_PROGE | NVMCTRL_STATUS_LOCKE | NVMCTRL_STATUS_NVME)

static bool address_ok(uint32_t address)
{
    return address >= PROBE_BASE && address <= PROBE_END - PROBE_PAGE
        && address % PROBE_PAGE == 0;
}

bool probe_read_page(uint32_t address, uint8_t page[PROBE_PAGE])
{
    if (!address_ok(address)) return false;
    const volatile uint8_t *flash = (const volatile uint8_t *)address;
    for (unsigned i = 0; i < PROBE_PAGE; ++i) page[i] = flash[i];
    return true;
}

static bool ready(void)
{
    uint32_t budget = 4194304u;
    while (!(NVMCTRL->INTFLAG.reg & NVMCTRL_INTFLAG_READY)) {
        if (!--budget) return false;
    }
    return true;
}

bool probe_write_page(uint32_t address, const uint8_t page[PROBE_PAGE])
{
    if (!address_ok(address) || !ready() || (NVMCTRL->STATUS.reg & NVM_ERRORS)) return false;
    const volatile uint8_t *flash = (const volatile uint8_t *)address;
    for (unsigned i = 0; i < PROBE_PAGE; ++i) {
        if (flash[i] != UINT8_MAX) return false;
    }

    NVMCTRL->CTRLB.bit.MANW = 1;
    NVMCTRL->ADDR.reg = address / 2;
    NVMCTRL->CTRLA.reg = NVMCTRL_CTRLA_CMDEX_KEY | NVMCTRL_CTRLA_CMD_PBC;
    if (!ready() || (NVMCTRL->STATUS.reg & NVM_ERRORS)) return false;

    volatile uint32_t *buffer = (volatile uint32_t *)address;
    for (unsigned i = 0; i < PROBE_PAGE / 4; ++i) {
        uint32_t word = 0;
        for (unsigned k = 0; k < 4; ++k) word |= (uint32_t)page[4 * i + k] << (8 * k);
        buffer[i] = word;
    }
    /* SAM D21 manual-write sequence: AHB read after filling the buffer. */
    (void)*buffer;
    NVMCTRL->ADDR.reg = address / 2;
    NVMCTRL->CTRLA.reg = NVMCTRL_CTRLA_CMDEX_KEY | NVMCTRL_CTRLA_CMD_WP;
    (void)*buffer;
    if (!ready() || (NVMCTRL->STATUS.reg & NVM_ERRORS)) return false;
    for (unsigned i = 0; i < PROBE_PAGE; ++i) {
        if (flash[i] != page[i]) return false;
    }
    return true;
}

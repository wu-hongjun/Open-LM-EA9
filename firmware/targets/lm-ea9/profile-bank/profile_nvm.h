#ifndef OLA_PROFILE_NVM_H
#define OLA_PROFILE_NVM_H
#include "profile_bank.h"
#include "profile_layout.h"
/* Sole hardware port; no unlock, fuses, user row, metadata or boot writes. */
const pb_io *pb_samd21_io(void);
int pb_journal_range(unsigned offset, unsigned bytes, unsigned alignment);
#endif

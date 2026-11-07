#ifndef OLA_PROFILE_BANK_H
#define OLA_PROFILE_BANK_H
#include <stddef.h>
#include <stdint.h>

/* Wire formats use explicit little-endian bytes, never packed native structs. */
#define PB_BANK_BYTES 4096u
#define PB_RECORD_BYTES 256u
#define PB_MAX_PROFILES 15u
#define PB_JOURNAL_ROWS 16u
#define PB_JOURNAL_BYTES (PB_JOURNAL_ROWS * 256u)
#define PB_PAGE_BYTES 64u
#define PB_ROW_BYTES 256u
#define PB_MAILBOX_OFFSET 32u
#define PB_MAILBOX_BYTES 26u

enum pb_result { PB_OK = 0, PB_UNCHANGED = 1, PB_PENDING = 2,
                 PB_INVALID = -1, PB_IO = -2, PB_EXHAUSTED = -3 };
typedef struct { uint32_t fingerprint; uint8_t count, default_slot; } pb_bank;
typedef struct { uint32_t sequence, generation; uint8_t slot, row; } pb_setting;
typedef struct {
    void *context;
    /* Relative journal offsets only. Each commit erases another row, then
     * programs exactly one page. Erased-looking torn pages are never reused. */
    int (*read)(void *, unsigned, uint8_t *, unsigned);
    int (*program)(void *, unsigned, const uint8_t *);
    int (*erase)(void *, unsigned);
} pb_io;

uint32_t pb_crc32(const uint8_t *, size_t);
uint16_t pb_u16(const uint8_t *);
uint32_t pb_u32(const uint8_t *);
int pb_validate_bank(const uint8_t *, pb_bank *);
const uint8_t *pb_profile(const uint8_t *, uint8_t);
int pb_load(const pb_bank *, const pb_io *, pb_setting *);
int pb_store(const pb_bank *, const pb_io *, uint8_t, uint32_t, pb_setting *);
int pb_boot(const uint8_t *, const uint8_t *, const pb_io *, pb_setting *);
/* Pure record encoder also used to seed a new bank installation. */
void pb_encode_setting(uint8_t *, const pb_bank *, const pb_setting *);
#endif

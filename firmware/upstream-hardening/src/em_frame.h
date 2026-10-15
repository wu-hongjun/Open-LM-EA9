/* E-mount frame admission. No hardware, allocation or mutable global state. */
#ifndef EA9_EM_FRAME_H
#define EA9_EM_FRAME_H
#include <stdint.h>

enum em_frame_error {
    EM_FRAME_OK = 0, EM_FRAME_SHORT, EM_FRAME_START, EM_FRAME_LENGTH,
    EM_FRAME_TRUNCATED, EM_FRAME_TERMINATOR, EM_FRAME_CHECKSUM
};
struct em_frame_view {
    const uint8_t *data;
    uint16_t length; /* Frame only; a chip-select window may contain a tail. */
};
/* On failure, clear out. The caller owns the stable receive-window snapshot.
 * Padding, including nonzero padding, is outside the frame and is not parsed.
 * This checks framing only; message semantics and interrupt ownership are
 * separate responsibilities. Never use a failed view to dispatch a command. */
enum em_frame_error em_frame_open(const uint8_t *window, uint16_t available,
                                  struct em_frame_view *out);
#endif

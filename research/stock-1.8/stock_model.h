#ifndef STOCK_MODEL_H
#define STOCK_MODEL_H
#include <stddef.h>
#include <stdint.h>
/* Host analysis only. No startup, vector table, MMIO or flash-writing code. */
typedef struct {
  uint16_t sample, pad02, initial_sample, protocol_position, reference, pad0a;
  int32_t relative;
  int16_t velocity;
  uint16_t pad12;
  int16_t target;
  uint16_t pad16;
  int32_t unused18;
  uint8_t direction, armed, pid_enabled, pad1f;
  uint16_t timeout, unused22;
  uint8_t completed, pad25;
  uint16_t focal_mm;
  uint8_t park, menu, boundary, pad2b;
} stock_settings;
_Static_assert(sizeof(stock_settings) == 44, "settings size");
_Static_assert(offsetof(stock_settings, relative) == 12, "relative offset");
_Static_assert(offsetof(stock_settings, target) == 20, "target offset");
_Static_assert(offsetof(stock_settings, direction) == 28, "direction offset");
_Static_assert(offsetof(stock_settings, focal_mm) == 38, "focal offset");
typedef void (*stock_event_sink)(void *context, uint32_t address,
                                 uint32_t argument);
typedef struct {
  uint8_t ram[0x800];
  stock_event_sink sink;
  void *context;
} stock_model;
void stock_restore(stock_model *m, const uint8_t settings[44]);
int stock_frame(stock_model *m, uint32_t offset, uint32_t length);
void stock_init(
    stock_model *m); /* All zero synthetic state, NOT factory initialization. */
/* Routine address selects reconstructed semantics. Sensor argument is raw
   sample. Returns 0 except sensor position/aperture/speed/PID/completion; -2 unsupported division, -1
   unknown entry. */
int32_t stock_run(stock_model *m, uint32_t address, int32_t argument);
#endif

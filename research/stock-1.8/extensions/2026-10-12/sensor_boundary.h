#ifndef STOCK_SENSOR_BOUNDARY_H
#define STOCK_SENSOR_BOUNDARY_H

#include <stdint.h>

/* Offline, synthetic RAM and recorded boundaries only. No device interface. */
enum sensor_event_kind {
  SENSOR_MMIO_WRITE = 1,
  SENSOR_ASSERT = 2,
  SENSOR_SPI_ENABLE = 3,
  SENSOR_BUSY_LOOP = 4,
  SENSOR_SPI_TRANSFER = 5
};

typedef struct {
  uint32_t kind;
  uint32_t args[5];
} sensor_event;

typedef struct {
  uint8_t ram[0xc00];
  sensor_event events[16];
  uint32_t event_count;
  uint16_t spi_word;
  int32_t enable_status;
  int32_t transfer_status;
} sensor_boundary;

/* New entries: 0x89a4, 0x8c64 and 0x8c80. Existing 0x8ae4, 0x8cc0 and 0x8a8c
 * compose through the unchanged public stock_model implementation. */
uint32_t sensor_run(sensor_boundary *m, uint32_t entry, uint32_t arg0,
                    uint32_t arg1);
void sensor_restore(sensor_boundary *m, const uint8_t settings[44]);

#endif

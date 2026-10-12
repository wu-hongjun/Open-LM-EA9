#include "sensor_boundary.h"
#include "stock_model.h"

#include <assert.h>
#include <string.h>

static void write_value(sensor_boundary *m, unsigned off, uint32_t value,
                        unsigned width) {
  assert(off + width <= sizeof(m->ram));
  for (unsigned i = 0; i < width; i++)
    m->ram[off + i] = (uint8_t)(value >> (8u * i));
}

static void event(sensor_boundary *m, uint32_t kind, uint32_t a, uint32_t b,
                  uint32_t c, uint32_t d, uint32_t e) {
  assert(m->event_count < sizeof(m->events) / sizeof(m->events[0]));
  sensor_event *out = &m->events[m->event_count++];
  out->kind = kind;
  out->args[0] = a;
  out->args[1] = b;
  out->args[2] = c;
  out->args[3] = d;
  out->args[4] = e;
}

/* 0x89a4, with the original valid-descriptor paths through 0x6be4 and
 * 0x6c0c included. The lower SPI driver supplies two response bytes; its
 * return status and the enable return status do not affect this result.
 * Assert events record condition/line, not a recovered filename pointer.
 * Stack buffer addresses are normalized to their observable byte contents. */
static uint32_t sample(sensor_boundary *m, uint32_t selector) {
  uint32_t mask = selector == 1u ? 0x80u : 0x800u;
  event(m, SENSOR_MMIO_WRITE, 0x60000014u, mask, 4, 0, 0);
  event(m, SENSOR_ASSERT, 1, 0x57, 0, 0, 0);
  event(m, SENSOR_SPI_ENABLE, 0x20000868u, (uint32_t)m->enable_status, 0, 0, 0);
  event(m, SENSOR_BUSY_LOOP, 1, 0, 0, 0, 0);
  event(m, SENSOR_ASSERT, 1, 0xb3, 0, 0, 0);
  event(m, SENSOR_SPI_TRANSFER, 0x20000868u, 2, 0, m->spi_word,
        (uint32_t)m->transfer_status);
  event(m, SENSOR_BUSY_LOOP, 1, 0, 0, 0, 0);
  event(m, SENSOR_MMIO_WRITE, 0x60000018u, mask, 4, 0, 0);
  return (uint32_t)(m->spi_word >> 2);
}

/* 0x8c64: retained state named an unused filter by the static inventory.
 * The naming and whether this is reached elsewhere are separate claims. */
static void filter_init(sensor_boundary *m, uint32_t arg0, uint32_t arg1) {
  write_value(m, 0xaa8, 0, 4);
  write_value(m, 0xaac, 0, 4);
  write_value(m, 0xa9c, 0, 4);
  write_value(m, 0xaa0, 0, 4);
  write_value(m, 0xaa4, arg0, 4);
  write_value(m, 0xa90, arg1, 4);
  write_value(m, 0xa94, arg1, 4);
  write_value(m, 0xa98, arg1, 4);
}

static void encoder_init(sensor_boundary *m) {
  filter_init(m, 60, 0);
  uint32_t raw = sample(m, 1);
  write_value(m, 0x494, raw, 2);
  write_value(m, 0x49c, raw, 2);
  write_value(m, 0x498, raw, 2);
  write_value(m, 0x4a4, 0, 2);
  write_value(m, 0x49a, 4096, 2);
  write_value(m, 0x4b0, 3, 1);
  write_value(m, 0x4b1, 0, 1);
  write_value(m, 0x4a0, 0, 4);
  write_value(m, 0x4ac, 0, 4);
}

void sensor_restore(sensor_boundary *m, const uint8_t settings[44]) {
  stock_model base;
  stock_init(&base);
  memcpy(base.ram, m->ram, sizeof(base.ram));
  stock_restore(&base, settings);
  memcpy(m->ram, base.ram, sizeof(base.ram));
}

uint32_t sensor_run(sensor_boundary *m, uint32_t entry, uint32_t arg0,
                    uint32_t arg1) {
  switch (entry) {
  case 0x89a4:
    return sample(m, arg0);
  case 0x8c64:
    filter_init(m, arg0, arg1);
    return 0;
  case 0x8c80:
    encoder_init(m);
    return 0;
  case 0x8cc0:
  case 0x8a8c: {
    uint32_t raw = entry == 0x8cc0 ? sample(m, 1) : 0;
    stock_model base;
    stock_init(&base);
    memcpy(base.ram, m->ram, sizeof(base.ram));
    int32_t result = stock_run(&base, entry, (int32_t)raw);
    memcpy(m->ram, base.ram, sizeof(base.ram));
    return (uint32_t)result;
  }
  default:
    assert(!"unsupported sensor-boundary entry");
    return 0;
  }
}

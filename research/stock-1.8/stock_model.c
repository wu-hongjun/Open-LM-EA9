#include "stock_model.h"
#include <string.h>
/* Reconstructed from official 1.8.0 bytes, not upstream experimental
 * controller. Address constants below are SRAM offsets from 0x20000000. Byte
 * accessors preserve packed/unaligned fields and leave unknown bytes untouched.
 * Each modeled routine has a finite original-instruction oracle in validate.py.
 */
static uint32_t r(const stock_model *m, unsigned a, unsigned n) {
  uint32_t v = 0;
  for (unsigned i = 0; i < n; i++)
    v |= (uint32_t)m->ram[a + i] << (8 * i);
  return v;
}
static void w(stock_model *m, unsigned a, uint32_t v, unsigned n) {
  for (unsigned i = 0; i < n; i++)
    m->ram[a + i] = (uint8_t)(v >> (8 * i));
}
/* Explicit two's-complement conversions avoid implementation-defined narrowing.
 */
static int32_t s32(uint32_t v) {
  return v <= INT32_MAX ? (int32_t)v : -1 - (int32_t)(UINT32_MAX - v);
}
static int32_t s16(uint32_t v) {
  v &= 65535;
  return v < 32768 ? (int32_t)v : (int32_t)v - 65536;
}
static int32_t sr(stock_model *m, unsigned a) { return s32(r(m, a, 4)); }
static void event(stock_model *m, uint32_t a, uint32_t v) {
  if (m->sink)
    m->sink(m->context, a, v);
}
void stock_init(stock_model *m) { memset(m, 0, sizeof(*m)); }
/* 0x8e28: register effects become an event; software flags remain modeled. */
static void stop(stock_model *m) {
  event(m, 0x8e28, 0);
  w(m, 0x4b2, 0, 1);
  w(m, 0x4b1, 0, 1);
  w(m, 0x4b8, 1, 1);
  w(m, 0x4be, 0, 1);
}
/* 0x8dd4: narrow before direction selection; do not reset PID history. */
static void target(stock_model *m, int32_t t) {
  int32_t q = s16(((uint32_t)s16((uint32_t)t) - 4096u) * 4u);
  w(m, 0x4b1, 1, 1);
  w(m, 0x4a8, (uint32_t)q, 2);
  w(m, 0x4b2, 1, 1);
  w(m, 0x4b4, 0, 4);
  w(m, 0x4b8, 0, 1);
  w(m, 0x4b0, sr(m, 0x4a0) < q ? 1 : sr(m, 0x4a0) > q ? 2 : 3, 1);
}
/* 0x8d20: signed asymmetric threshold branches, including wrong-sign error. */
static int32_t speed(stock_model *m, int32_t e) {
  uint32_t d = r(m, 0x4b0, 1);
  if (d == 1)
    return e > 600 ? 250 : e > 300 ? 100 : e > 100 ? 50 : e / 2;
  if (d == 2)
    return e < -600 ? -250 : e < -300 ? -100 : e < -100 ? -50 : e / 2;
  return 0;
}
/* 0x8bfc: unsigned intermediates implement ARM modulo-2^32 arithmetic. */
static int32_t pid(stock_model *m, int32_t e) {
  uint32_t x = (uint32_t)e, old = r(m, 0x4d0, 4), old2 = r(m, 0x4d4, 4);
  w(m, 0x4cc, x, 4);
  w(m, 0x4d4, old, 4);
  w(m, 0x4d0, x, 4);
  uint32_t a = r(m, 0x4c0, 4) * (x - old) + r(m, 0x4c4, 4) * x +
               r(m, 0x4c8, 4) * (x - 2u * old + old2) + r(m, 0x4f4, 4);
  w(m, 0x4f4, a, 4);
  int32_t den = sr(m, 0x4f0);
  if (!den)
    return -2;
  int32_t v = s32((uint32_t)((int64_t)s32(a) / den));
  int32_t floor = sr(m, 0x4ec), nf = s32(0u - (uint32_t)floor),
          limit = sr(m, 0x4e8), nl = s32(0u - (uint32_t)limit);
  if (v > 0 && v < floor)
    v = floor;
  if (v < 0 && v > nf)
    v = nf;
  return v > limit ? limit : v < nl ? nl : v;
}
/* 0x8fc8: second velocity history overwrites callback velocity; emit both
 * drivers. */
static void control(stock_model *m) {
  uint32_t pos = r(m, 0x4a0, 2);
  w(m, 0x4a4, pos - r(m, 0x638, 2), 2);
  w(m, 0x638, pos, 2);
  if (r(m, 0x4b2, 1)) {
    int32_t v =
        pid(m, speed(m, s16(r(m, 0x4a8, 2) - pos)) - s16(r(m, 0x4a4, 2)));
    w(m, 0x63c, (uint32_t)v, 4);
    uint32_t magnitude = (v > 0 ? (uint32_t)v : 0u - (uint32_t)v) & 65535;
    event(m, v > 0 ? 0x8e88 : 0x8ed8, magnitude);
    event(m, v > 0 ? 0x8f28 : 0x8f78, magnitude);
  }
}
/* 0x5308: operates on existing RX memory; deliberately adds no validation. */
static void extract(stock_model *m) {
  w(m, 0x526, 1, 1);
  w(m, 0x527, 1, 1);
  w(m, 0x528, 1, 1);
  if (r(m, 0x69d, 1) == 0x81) {
    if (r(m, 0x529, 1) == 10)
      w(m, 0x52a, 1, 1);
    else
      w(m, 0x529, r(m, 0x529, 1) + 1, 1);
  } else {
    w(m, 0x52a, 0, 1);
    w(m, 0x529, 0, 1);
  }
  uint32_t len = r(m, 0x695, 1);
  if (len != 22) {
    w(m, 0x52b, 1, 1);
    w(m, 0x7a0, len, 1);
    w(m, 0x690, r(m, 0x79f, 1), 1);
    w(m, 0x79f, len, 1);
    if (len == 27) {
      w(m, 0x7a2, r(m, 0x6a8, 2), 2);
      w(m, 0x7a4, r(m, 0x6aa, 2), 2);
    } else if (len == 36)
      w(m, 0x7a2, r(m, 0x6af, 2), 2);
  }
}
static void state(stock_model *m, unsigned v) { w(m, 0x52e, v, 1); }
/* 0x5a94/0x5c08: both comparisons use the ORIGINAL signed request. */
static void clamped_target(stock_model *m) {
  uint32_t lo = r(m, 0xd, 2), hi = r(m, 0xf, 2), v = r(m, 0x7a2, 2);
  int32_t original = s16(v);
  if (original < (int32_t)lo)
    v = lo;
  if (original > (int32_t)hi)
    v = hi;
  w(m, 0x4be, v == lo || v == hi, 1);
  target(m, s16(v));
}
static void response(stock_model *m, unsigned kind) {
  if (kind == 0x1d || kind == 0x24 || kind == 0x1c) {
    w(m, 0x1f, 0, 1);
    w(m, 0x30, kind == 0x24 ? 0x1f : kind, 1);
    w(m, 0x31, 0, 1);
    w(m, 0x655, 50, 1);
  }
}
/* 0x5a94/0x5b98/0x5c08: caller-paced states, no invented motor completion. */
static void command(stock_model *m, unsigned kind) {
  unsigned s = r(m, 0x52e, 1);
  if (kind == 27) {
    if (s == 0) {
      w(m, 0x34, 1, 1);
      clamped_target(m);
      state(m, 1);
    } else if (s == 1 && r(m, 0x4b8, 1)) {
      w(m, 0x655, 50, 1);
      w(m, 0x34, 0, 1);
      w(m, 0x30, 29, 1);
      state(m, 2);
    } else if (s == 2) {
      stop(m);
      state(m, 10);
    }
  } else if (kind == 36) {
    switch (s) {
    case 0:
      w(m, 0x1f, 16, 1);
      state(m, 1);
      break;
    case 1:
      clamped_target(m);
      state(m, 2);
      break;
    case 2:
      if (r(m, 0x4b8, 1)) {
        w(m, 0x1f, 32, 1);
        target(m, s16(r(m, 0x7a4, 2)));
        state(m, 4);
      }
      break;
    case 4:
      w(m, 0x1f, r(m, 0x4b8, 1) ? 48 : 32, 1);
      if (r(m, 0x4b8, 1))
        state(m, 5);
      break;
    case 5:
      response(m, 36);
      state(m, 10);
      break;
    case 6:
      if (r(m, 0x52f, 1) == 3) {
        stop(m);
        state(m, 5);
      }
      w(m, 0x52f, r(m, 0x52f, 1) + 1, 1);
      break;
    }
  } else if (kind == 23) {
    if (s == 0) {
      state(m, 1);
      stop(m);
      w(m, 0x655, 50, 1);
      if (r(m, 0x690, 1) == 36)
        w(m, 0x30, 31, 1);
      if (r(m, 0x690, 1) == 27)
        w(m, 0x30, 29, 1);
    } else if (s == 1) {
      w(m, 0x655, 50, 1);
      w(m, 0x30, 28, 1);
      state(m, 2);
    }
  }
}

/* 0x51d4: finite host contract requires a frame wholly in modeled RAM and
 * length 4..255. Stock itself does not perform these host-interface checks. */
int stock_frame(stock_model *m, uint32_t off, uint32_t len) {
  if (len < 4 || len > 255 || off > sizeof(m->ram) - len)
    return -2;
  w(m, 0x524, 0, 1);
  event(m, 0x51c8, 0);
  w(m, off + 1, len, 1);
  w(m, off + len - 1, 0x55, 1);
  uint32_t sum = 0;
  for (uint32_t i = 1; i < len - 3; i++)
    sum += r(m, off + i, 1);
  w(m, off + len - 3, sum, 2);
  event(m, 0x9180, len);
  return 0;
}
/* 0x66b8, 0x567c, 0x56cc: stock metadata/menu semantics. */
static int32_t aperture(int32_t v) {
  return (int32_t)((((uint32_t)s16((uint32_t)v) - 8u) * 32u + 4096u) & 65535u);
}
static void focal_step(stock_model *m) {
  uint32_t f = r(m, 0x680, 2);
  w(m, 0x13,
    f >= 70   ? 6
    : f >= 50 ? 8
    : f >= 35 ? 10
    : f >= 24 ? 14
    : f >= 16 ? 16
              : 20,
    1);
}
static void menu(stock_model *m, unsigned off) {
  static const uint16_t focal[8][3] = {
      {12, 15, 18}, {21, 24, 28},    {35, 40, 45},    {50, 60, 75},
      {80, 85, 90}, {135, 150, 180}, {200, 250, 300}, {400, 600, 800}};
  unsigned hi = r(m, off + 7, 1), lo = r(m, off + 6, 1);
  if (hi >= 0x13 && hi <= 0x1b) {
    if (hi < 0x1b) {
      int col = lo == 0 ? 0 : lo == 0x55 ? 1 : lo == 0xaa ? 2 : -1;
      if (col >= 0)
        w(m, 0x680, focal[hi - 0x13][col], 2);
    } else if (lo == 0)
      w(m, 0x4bc, r(m, 0x4bc, 1) == 0, 1);
    else if (lo == 0x55)
      w(m, 0x4bd, 0, 1);
    else if (lo == 0xaa)
      w(m, 0x4bd, 1, 1);
    w(m, 0x608, 1, 1);
  }
  focal_step(m);
}
/* 0x8a8c: retain the assembly data dependency. The 0x18 immediate at
 * 0x8aa6 supplies both descriptor bytes AND later address/value arithmetic. */
static void boot_metadata(stock_model *m) {
  w(m, 0x1ae, (uint32_t)aperture(0x18), 2);
  w(m, 0x1b0, (uint32_t)aperture(0x18), 2);
  const unsigned descriptor = 0x18;
  w(m, 0x1da, descriptor, 1);
  w(m, 0x1e1, descriptor, 1);
  w(m, 0x1a8 + descriptor + 0x22, 0x70, 1);
  w(m, descriptor + 8, 0x6c, 1);
  w(m, 0x21, 2, 1);
  w(m, 0x22, 6, 1);
  w(m, 0x23, descriptor + 8, 1);
  focal_step(m);
}
static int focal_update(stock_model *m) {
  if (r(m, 0x527, 1)) {
    uint32_t ptr = r(m, 0x678, 4);
    if (ptr < 0x20000000u || ptr > 0x200007deu)
      return -2;
    unsigned off = ptr - 0x20000000u;
    w(m, 0x527, 0, 1);
    uint32_t f = r(m, 0x680, 2) * 10u;
    w(m, 0x36e, f, 2);
    w(m, 0x370, f, 2);
    w(m, off + 0x20, f, 2);
    w(m, off + 0x1e, f, 2);
  }
  return 0;
}
/* 0x58a4: reply dispatch with final transmit represented as an event. */
static int dispatch(stock_model *m) {
  w(m, 0x523, 0, 1);
  if (r(m, 0x51f, 1) != 1 || r(m, 0x697, 1) != 2)
    return 0;
  unsigned id = r(m, 0x699, 1), off = 0, len = 0, slot = 0;
  switch (id) {
  case 1:
    slot = 0x64c;
    len = 41;
    break;
  case 7:
    slot = 0x650;
    len = 43;
    break;
  case 8:
    slot = 0x65c;
    len = 210;
    break;
  case 9:
    slot = 0x664;
    len = 20;
    break;
  case 10:
    off = 0x334;
    len = 25;
    break;
  case 11:
    slot = 0x68c;
    len = 11;
    break;
  case 12:
    slot = 0x670;
    len = 10;
    break;
  case 13:
    off = 0xa8;
    len = 10;
    break;
  case 16:
    slot = 0x658;
    len = 10;
    break;
  case 22:
    w(m, 0x52c, 1, 1);
    w(m, 0x52d, 0, 1);
    return 0;
  case 25:
    off = 0x328;
    len = 10;
    break;
  case 27:
    off = 0x350;
    len = 19;
    w(m, 0x356, r(m, 0x69a, 2), 2);
    w(m, 0x358, r(m, 0x69a, 2), 2);
    menu(m, off);
    break;
  case 40:
    off = 0x364;
    len = 44;
    break;
  case 50:
    off = 0x214;
    len = 16;
    break;
  case 52:
    off = 0x308;
    len = 32;
    w(m, 0x30e, 0, 1);
    w(m, 0x30f, r(m, 0x69a, 2), 2);
    break;
  case 61:
    off = 0x280;
    len = 72;
    break;
  case 63:
    off = 0x234;
    len = 74;
    break;
  case 76:
    off = 0x224;
    len = 16;
    break;
  case 90:
    off = 0x2c8;
    len = 64;
    break;
  default:
    return 0;
  }
  if (slot) {
    uint32_t p = r(m, slot, 4);
    if (p < 0x20000000u || p > 0x20000800u - len)
      return -2;
    off = p - 0x20000000u;
  }
  if (id == 12)
    w(m, off + 6, 0, 1);
  int result = stock_frame(m, off, len);
  if (id == 10) {
    w(m, 0x654, 0x69, 1);
    w(m, 0x51f, 4, 1);
    w(m, 0x51e, 0, 1);
    w(m, 0x520, 0, 1);
  }
  return result;
}

/* Application orchestration boundaries: timers, DMA, NVM and delays produce
 * events. No event implies completion of its physical operation. */
static void schedule(stock_model *m, unsigned delay, unsigned callback) {
  event(m, 0x609c, (callback << 16) | delay);
}
static void persist(stock_model *m) {
  event(m, 0x6a38, 1);
  event(m, 0x6918, 44);
  event(m, 0x69b0, 1);
}
static void persist_reference(stock_model *m) {
  if (r(m, 0x608, 1)) {
    w(m, 0x608, 0, 1);
    w(m, 0x49c, r(m, 0x494, 2), 2);
    persist(m);
  }
}
void stock_restore(stock_model *m, const uint8_t settings[44]) {
  memcpy(m->ram + 0x494, settings, 44);
  w(m, 0x680, r(m, 0x4ba, 2), 2);
  w(m, 0xd, 0x1030, 2);
}
static int pointer_frame(stock_model *m, unsigned slot, unsigned length) {
  uint32_t p = r(m, slot, 4);
  if (p < 0x20000000u || p > 0x20000800u)
    return -2;
  return stock_frame(m, p - 0x20000000u, length);
}
static void reinitialize(stock_model *m) {
  w(m, 0x51f, 1, 1);
  w(m, 0x520, 0, 1);
  w(m, 0x523, 1, 1);
  w(m, 0x697, 0, 1);
  w(m, 0x51e, 0, 1);
}
static int copy_event(stock_model *m) {
  uint32_t p = r(m, 0x660, 4);
  if (p < 0x20000000u || p > 0x200007d1u)
    return -2;
  unsigned off = p - 0x20000000u;
  w(m, off + 0x2d, r(m, 0x30, 1), 1);
  w(m, off + 0x2e, 0, 1);
  return 0;
}
static int handshake(stock_model *m, unsigned a, int32_t arg) {
  switch (a) {
  case 0x5120:
    if (r(m, 0x51c, 1) == 1) {
      w(m, 8, r(m, 0x49a, 2), 2);
      w(m, 0x1a, r(m, 0x49a, 2), 2);
      w(m, 0x51d, 1, 1);
      if (!r(m, 0x51e, 1)) {
        w(m, 0x520, 13, 1);
        w(m, 0x521, 1, 1);
      } else {
        w(m, 0x51f, 5, 1);
        w(m, 0x51e, 0, 1);
        w(m, 0x51c, 0, 1);
        schedule(m, 10, 0x5261);
      }
    } else if (r(m, 0x51f, 1) == 4)
      w(m, 0x51c, 1, 1);
    break;
  case 0x5188:
    if (r(m, 0x522, 1))
      schedule(m, 100, 0x5281);
    break;
  case 0x51ac:
    reinitialize(m);
    break;
  case 0x5238:
    w(m, 0x520, 2, 1);
    return pointer_frame(m, 0x678, r(m, 0x654, 1));
  case 0x5260:
    return stock_frame(m, 0x694, r(m, 0x695, 1));
  case 0x5274:
    w(m, 0x655, 48, 1);
    break;
  case 0x5280:
    if (r(m, 0x51f, 1) != 1 && r(m, 0x51f, 1) != 5) {
      if (r(m, 0x520, 1) == 2) {
        w(m, 0x520, 3, 1);
        schedule(m, 300, 0x54d9);
      } else if (r(m, 0x520, 1) == 5) {
        w(m, 0x520, 6, 1);
        w(m, 0x655, 48, 1);
      }
    }
    if (r(m, 0x51f, 1) == 5)
      reinitialize(m);
    event(m, 0x60000014, 0x400);
    break;
  case 0x52e8:
    w(m, 0x525, (r(m, 0x6a1, 1) & 4) == 0, 1);
    break;
  case 0x54b8:
    return copy_event(m);
  case 0x54d8:
    if (!r(m, 0x51e, 1)) {
      w(m, 0x520, 5, 1);
      if (copy_event(m))
        return -2;
      return pointer_frame(m, 0x660, r(m, 0x655, 1));
    }
    break;
  case 0x53a4:
    if (r(m, 0x522, 1)) {
      unsigned mode = r(m, 0x51f, 1), phase = r(m, 0x520, 1);
      if (((uint32_t)arg & 4) != 0) {
        event(m, 0x91c4, 255);
        if (mode != 1 && mode != 5) {
          switch (phase) {
          case 0:
            w(m, 0x520, 8, 1);
            w(m, 0x51c, 1, 1);
            break;
          case 2:
          case 3:
          case 5:
          case 12:
          case 13:
            w(m, 0x51e, 1, 1);
            break;
          case 6:
            w(m, 0x520, 8, 1);
            break;
          case 9:
            w(m, 0x520, 11, 1);
            break;
          }
        }
      } else {
        event(m, 0x91ac, 0);
        w(m, 0x523, 1, 1);
        if (mode != 1 && mode != 5) {
          uint32_t p = r(m, 0x660, 4), q = r(m, 0x678, 4);
          if (p < 0x20000000u || p > 0x200007fbu || q < 0x20000000u ||
              q > 0x200007fbu)
            return -2;
          w(m, p - 0x20000000u + 4, r(m, 0x698, 1) + 1, 1);
          w(m, q - 0x20000000u + 4, r(m, 0x698, 1) + 1, 1);
          if (r(m, 0x697, 1) == 2 && r(m, 0x699, 1) == 10)
            w(m, 0x51e, 1, 1);
          else if (phase == 8) {
            w(m, 0x520, 9, 1);
            handshake(m, 0x52e8, 0);
          } else if (phase == 11) {
            w(m, 0x520, 12, 1);
            extract(m);
          } else
            w(m, 0x51e, 1, 1);
        }
      }
    }
    break;
  default:
    return -1;
  }
  return 0;
}
/* 0x5e00: bounded input scenario: every sensor read returns arg, and shutdown
 * input PA3 remains low for both reads. WFI is an event with simulated wake.
 * Busy waits with a held-high PA3 require a scheduler and are NOT modeled. */
static int main_state(stock_model *m, int32_t sample) {
  if (!r(m, 0x52a, 1))
    w(m, 0x390, 1, 1);
  else if (r(m, 0x390, 1)) {
    w(m, 0x390, 0, 1);
    target(m, s16(r(m, 0xd, 2)));
  }
  if (r(m, 0x530, 1)) {
    event(m, 0x8ed8, 800);
    event(m, 0x8f78, 800);
    event(m, 0x66fc, 300);
    stop(m);
    event(m, 0x66fc, 500);
    stock_run(m, 0x8cc0, sample);
    w(m, 0x49c, r(m, 0x494, 2), 2);
    stock_run(m, 0x8cc0, sample);
    w(m, 0x608, 1, 1);
    persist_reference(m);
    w(m, 0x530, 0, 1);
  }
  if (r(m, 0x521, 1)) {
    w(m, 0x521, 0, 1);
    schedule(m, 10, 0x5239);
  }
  if (r(m, 0x52c, 1)) {
    unsigned state = r(m, 0x52d, 1);
    if (state == 1) {
      if (r(m, 0x4b8, 1))
        w(m, 0x52d, 2, 1);
    } else if (state == 0) {
      if (r(m, 0x4bc, 1)) {
        w(m, 0x4be, 0, 1);
        target(m, s16(r(m, 0xd, 2)));
      }
      w(m, 0x52d, 1, 1);
    } else if (state == 2) {
      w(m, 0x52c, 0, 1);
      if (stock_frame(m, 0x694, r(m, 0x695, 1)))
        return -2;
      event(m, 0x66fc, 50);
      event(m, 0x70d0, 0x20000898);
      event(m, 0x66fc, 1);
      event(m, 0x66fc, 1);
      event(m, 0x60000018, 0x800000);
      event(m, 0x66fc, 100);
      event(m, 0x7a70, 2);
      event(m, 0x5f7e, 0);
    }
  }
  if (r(m, 0x604, 1)) {
    w(m, 0x604, 0, 1);
    w(m, 0x532, r(m, 0x49a, 2), 2);
    stock_run(m, 0x8cc0, sample);
    w(m, 0x4b8, (uint32_t)stock_run(m, 0x8d94, 0), 1);
    if (!r(m, 0x51d, 1)) {
      unsigned index = r(m, 0x674, 1);
      w(m, 0x668 + index, r(m, 0x532, 1) - r(m, 0x49a, 1), 1);
      if (index < 6)
        w(m, 0x674, index + 1, 1);
    } else {
      w(m, 0x51d, 0, 1);
      w(m, 8, r(m, 0x49a, 2), 2);
      w(m, 0x674, 0, 1);
    }
  }
  if (r(m, 0x608, 1)) {
    w(m, 0x608, 0, 1);
    w(m, 0x4ba, r(m, 0x680, 2), 2);
    persist(m);
  }
  return 0;
}
int32_t stock_run(stock_model *m, uint32_t a, int32_t arg) {
  switch (a) {
  case 0x5120:
  case 0x5188:
  case 0x51ac:
  case 0x5238:
  case 0x5260:
  case 0x5274:
  case 0x5280:
  case 0x52e8:
  case 0x53a4:
  case 0x54b8:
  case 0x54d8:
    return handshake(m, a, arg);
  case 0x5d68:
    persist(m);
    break;
  case 0x5da8:
    persist_reference(m);
    break;
  case 0x5dd4:
    if (r(m, 0x523, 1) == 1) {
      if (dispatch(m))
        return -2;
    }
    stock_run(m, 0x5cc8, 0);
    return focal_update(m);
  case 0x5e00:
    return main_state(m, arg);
  case 0x66b8:
    return aperture(arg);
  case 0x567c:
    focal_step(m);
    break;
  case 0x56cc:
    if ((uint32_t)arg > 0x7f8)
      return -2;
    menu(m, (unsigned)arg);
    break;
  case 0x8a8c:
    boot_metadata(m);
    break;
  case 0x5d2c:
    return focal_update(m);
  case 0x5510:
    w(m, 0x608, 1, 1);
    break;
  case 0x58a4:
    return dispatch(m);
  case 0x8cc0: {
    uint32_t ref = r(m, 0x49c, 2);
    int32_t d = s16((uint32_t)arg - ref);
    w(m, 0x494, (uint32_t)arg, 2);
    if (ref < 8192) {
      if (d > 10000)
        d = 16383 - d;
    } else if (d < 0)
      d += 16383;
    w(m, 0x4a0, (uint32_t)d, 4);
    int32_t shifted = d >= 0 ? d / 4 : -1 - ((-1 - d) / 4);
    w(m, 0x49a, (uint32_t)(shifted + 4096), 2);
    return (int32_t)r(m, 0x49a, 2);
  }
  case 0x8dd4:
    target(m, arg);
    break;
  case 0x8d20:
    return speed(m, arg);
  case 0x8bfc:
    return pid(m, arg);
  case 0x8d94: {
    int32_t p = sr(m, 0x4a0), t = s16(r(m, 0x4a8, 2));
    unsigned d = r(m, 0x4b0, 1), done = r(m, 0x4b8, 1);
    return done ? (int32_t)done : d == 1 ? p >= t : d == 2 ? p <= t : 1;
  }
  case 0x8e28:
    stop(m);
    break;
  case 0x8fc8:
    control(m);
    break;
  case 0x8a2c:
    w(m, 0x604, 1, 1);
    if (r(m, 0x4b1, 1)) {
      if (r(m, 0x4b4, 2) == 300)
        stop(m);
      else
        w(m, 0x4b4, r(m, 0x4b4, 2) + 1, 2);
    }
    if (r(m, 0x605, 1) == 10) {
      w(m, 0x605, 0, 1);
      w(m, 0x4a4, r(m, 0x4a0, 2) - r(m, 0x606, 2), 2);
      w(m, 0x606, r(m, 0x4a0, 2), 2);
      control(m);
    } else
      w(m, 0x605, r(m, 0x605, 1) + 1, 1);
    break;
  case 0x5308:
    extract(m);
    break;
  case 0x5a94:
    command(m, 36);
    break;
  case 0x5b98:
    command(m, 23);
    break;
  case 0x5c08:
    command(m, 27);
    break;
  case 0x5a2c:
    response(m, (unsigned)arg);
    break;
  case 0x5cc8:
    if (r(m, 0x52b, 1)) {
      state(m, 0);
      stop(m);
      w(m, 0x52b, 0, 1);
    }
    if (r(m, 0x526, 1)) {
      command(m, r(m, 0x79f, 1));
      w(m, 0x526, 0, 1);
    }
    break;
  default:
    return -1;
  }
  return 0;
}

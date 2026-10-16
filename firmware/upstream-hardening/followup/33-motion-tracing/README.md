# AF3.7 motion evidence lane

Read [the audit](../../../../docs/audits/astra-33-motion-tracing-2026-10-15.md).

`apply.py <private-tree>/src` accepts only pinned 3.6 `main.c`/`servo.c` and adds
bounded RAM observation hooks. Add `motion_trace.c` to the composed units with
`-Os`; preserve every existing compiler flag. Root/lane35 own whole-image fit
and safe persistence; this lane does not publish a firmware image.

`motion_trace.h` defines the fixed 144-byte little-endian snapshot ABI and
completion enums. `st_motion_data()` is read only from a safe main/fault flush
with IRQs masked by the shared writer; no UART IRQ writes motion state. Before
any begin, its all-zero BSS record means no observed motion. The first wrong-way
or runaway guard freezes control context; the next completion disposition may
be recorded once. There is no runtime fault clear.

`run.py` compiles exact production source bodies with ASan/UBSan and compares
synthetic observable control/protocol bytes, including six deliberately broken
observers. `measure.py` reproduces ARM object sizes/stack and checks all boolean
assignments plus 2,048 equivalent trace-state packings. Both require fresh
private output directories; public `results.json` and `measurement.json` contain
synthetic evidence only. No hardware qualification is claimed.

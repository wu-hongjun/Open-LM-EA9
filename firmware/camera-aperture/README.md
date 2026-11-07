# Camera-selected aperture reporting

Small overlay for [candidate 4.5.0](../candidates/4.5.0/README.md), built from
the pinned 4.4.0 C sources. `reported_aperture_offer` validates and stages
body requests in the receive callback; `reported_aperture_commit` publishes
the latest accepted value in foreground protocol code. `reported_aperture_init`
sets the declared boot value. The module has no iris or motor actuator and
does not persist selections.

The [builder](../../scripts/build-camera-aperture.py) verifies the base source
pins, adds the two source files and three call sites, and freezes the image,
source hashes and diff. The [test runner](../../scripts/test-camera-aperture.py)
executes the generated production sources with sanitizers and deliberately
broken controls. Its host IRQ model checks preservation/interleaving without
claiming to emulate ARM instruction timing or physical USB/camera behavior.

# Release-only ADC dependency removal

AF 3.9 omits unused supply telemetry when `EA9_NO_LOG` is defined. Four
`main.c` call sites are guarded: startup initialization and its ADC stage note,
per-pump sampling, and home tracking reset/result. Full legacy logging retains
the original ADC behavior. Driver, encoder, motor and protocol modules are
unchanged. The guard does not disable a current limit: the measured logic IOVCC
value has no control or protection consumer in this source.

[Astra47's independent consumer audit](../../../../docs/audits/astra-47-factory-origin-2026-10-20.md)
checks ADC clocks, initialization and every caller. This eliminates an unnecessary
blocking peripheral dependency and reduces release code/data by 412 bytes
before adding the home observations. It does not establish that ADC stalled on
hardware or caused the recorded phase 17 fault. Communication and sampling
cadence change; physical timing remains unmeasured.

```sh
python3 firmware/upstream-hardening/followup/48-release-adc/run.py --candidate artifacts/private/homing39-repeat --output artifacts/private/new-adc-check
```

The runner checks all 49 frozen source pins before/after and extracts the exact
startup/pump blocks. Candidate mode independently checks its manifest/image,
49 source hashes and host shim, then requires its pump/startup bodies to equal
the tested proposal. The real `vdd.c` conversion and 4,194,304-iteration bounded
wait execute under ASan/UBSan. An explicit peripheral-boundary hook models
RESRDY W1C semantics and completed/stuck conversions. A supplied protocol
scheduler checks two queries and shutdown acknowledgement across two pumps;
this is not a full wire-traffic or electrical-timing replay.

Twelve executions produce six expected passes and six specific failures. Frozen
release and retained legacy builds fail at the production ADC fault boundary
when a conversion stalls; the proposal progresses without any conversion.
A resampling mutant fails both the zero-conversion assertion and the stalled
capture progress assertion. Failure controls require the exact ADC fault,
scheduler state and failed predicate, not an arbitrary crash. The healthy
legacy control retains eight startup and two pump conversions and the stage
marker. Release controls require no conversion and no misleading ADC stage.

[Receipt](results.json) is sanitized and source-bound. No device was enumerated,
opened or flashed. Physical homing, optical focus, shutter acceptance and
factory parity remain unproved.

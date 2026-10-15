# Original boot entry contract into C 3.5

Read [audit 24](../../../../docs/audits/astra-24-boot-entry-2026-10-15.md) for the
contract, explicit MMIO model and physical limitations. This lane changes no
production source or artifact. It retains original boot data privately and emits
only hashes, addresses, contracts and synthetic observations.

```sh
tools/rea-analysis/venv/bin/python \
  firmware/upstream-hardening/followup/24-boot-entry/run.py \
  --output artifacts/private/astra-24-entry-recheck.json
```

The runner needs the retained private factory dump and exact frozen
`artifacts/private/absolute35a` build. It verifies their pins rather than
refreshing them. Eight path/state cases, two separately invoked application
initializer fixtures and nine negative controls are recorded in `result.json`.
No hardware, network or application-state access is present.

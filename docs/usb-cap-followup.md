# USB-cap read-only follow-up

October 10, 2026. Continued from [the initial investigation](usb-cap-investigation.md)
after the user requested proceeding with the recommended actions and documenting
everything. This run completed the feasible USB memory checks and an offline
management-entry proposal. No device programming, erase, unlock, reset, debug
attachment or custom code execution was performed.

Subsequent update: the user reports an unplug event and USB-only equipment.
The adapter re-enumerated with the same identity and a new USB registry entry.
A complete post-reconnect flash read and repeated vectors/register/fuse/
calibration snapshots match the baseline. The
[reconnect evidence](evidence/usb-cap-reconnect-2026-10-10.json) verifies 7 CHECK
and 2,055 READ exchanges. This supports restart/reconnect repeatability; power
and reset timing were not instrumented. See the
[USB-only development boundary](usb-only-next-steps.md).

## Confirmed results

**The connected unit is an ATSAMD21E17A, die revision D, with 128 KiB main
flash. Two complete flash reads match. Boot protection and region locks are
disabled, and the security bit is clear.** The original cap still enters the
stock bootloader, whose inspected USB branch supplies no application launch.

The [verified evidence summary](evidence/usb-cap-followup-2026-10-10.json)
contains report counts, hashes, decoded fields and limitations. Raw binaries,
transcripts, tool versions and private identity are under
`references/private/usb-cap-followup-2026-10-10/`, excluded from Git.

| Check | Measured result |
| --- | --- |
| Identity continuity | Exactly one matching device; product, serial, report descriptor and report sizes match the previous investigation |
| Chip identity | DSU.DID `0x1001030B`; ATSAMD21E17A, revision D |
| Flash capacity | NVMCTRL.PARAM `0x00030800`: 2,048 pages of 64 bytes, 131,072 bytes total; no separate RWWEE pages |
| Full flash | Two identical `[0x0000, 0x20000)` reads; both earlier boot/application spans match |
| Installed application | All cached 20,172 bytes of stock 1.8.0 match at `0x5000` |
| Boot protection | User-row BOOTPROT = 7, zero protected boot bytes |
| Region locks | Live LOCK and user-row LOCK both `0xFFFF`, all regions unlocked |
| Security bit | NVMCTRL.STATUS.SB = 0; this USB read is an internal CPU access, not a test of external debug access |
| NVM health/configuration | Repeated status identical, error bits zero, manual-write control MANW = 1 |
| User configuration | Two identical 64-byte windows at `0x00804000`, including all documented fuse bits; EEPROM emulation disabled |
| Calibration | Two identical 64-byte AUX1 windows at `0x00806000`; USB TRANSN=5, TRANSP=29, TRIM=3, DFLL coarse=23 |
| PA23 | Both snapshots: DIR=0/input, OUT=0, IN=1/high, PINCFG=`0x06`/input and pull enabled, mux disabled |
| Transactions | 12 CHECK and 4,108 READ, 4,120 matched exchanges across 12 memory-read sessions |

Full-flash SHA-256:

```
1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01
```

Identity/revision decoding uses Microchip's
[silicon errata, Table 1](https://ww1.microchip.com/downloads/en/DeviceDoc/SAM-D21DA1-Family-Silicon-Errata-and-Data-Sheet-Clarification-DS80000760G.pdf).
Capacity, fuse, lock and calibration decoding uses the saved
[family datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/SAM-D21DA1-Family-Data-Sheet-DS40001882G.pdf),
sections 10.3, 13.13.9 and 22.6/22.8. These documents are archived under
`references/documents/audit/` with URL, size and hash provenance.

## How register reads were qualified

Tracing `0x25FC–0x2624` showed READ calls `0x3528–0x3538`, a loop of 64 byte
loads and stores into reply RAM. The loader does not perform a 32-bit atomic
register snapshot. The datasheet's DSU, NVMCTRL and PORT register descriptions
permit byte access to register quarters/halves. The read windows were reviewed
before the probe was extended.

| Named snapshot | Complete source window | Qualification |
| --- | --- | --- |
| `device-id` | `[0x41002018, 0x41002058)` | DID plus reserved offsets; starts after DCC0/DCC1, which have read side effects |
| `nvm-status` | `[0x41004000, 0x41004040)` | Control, capacity, interrupt/status, address and lock registers plus reserved bytes; commands and flag clears require writes |
| `user-row` | `[0x00804000, 0x00804040)` | Auxiliary memory read; first eight bytes contain the documented user fuses |
| `calibration` | `[0x00806000, 0x00806040)` | Documented AUX1 block, including software calibration at offset `0x20` |
| `port-a` | `[0x41004400, 0x41004480)` | Direction/output aliases, synchronized input, control, mux and pin configuration; no GPIO writes |

Reserved bytes are preserved without interpretation. No generic MMIO-address
mode was added. Reading the DSU from its base would include debug mailboxes, so
that range is deliberately excluded. NVM status registers were inspected for
read effects; this probe never writes their command, flag or lock fields.
The loader flash driver's `0xE20/0xE24` functions hard-code 64-byte pages and
2,048 pages; those constants were not used as physical-capacity proof.

Port A's APB clock is already enabled by the recovered loader and exercised by
its startup. Reading IN synchronizes digital sampling; it is not a voltage or
source-impedance measurement. Each register is assembled from consecutive byte
reads, so a changing input may produce a non-atomic value. The observed complete
Port A snapshots happened to be identical.

The [native probe](../tools/ea9_readonly_probe.c) retains a command whitelist,
exact device/report checks, one outstanding request, no timeout retries and
exclusive output-file creation. Memory sessions require a stock `1.8.0` CHECK
reply. Unknown versions stop before READ. This adds protection against an
upload-state echo, but cannot prevent the first CHECK from being treated as data
if someone has already armed an upload. An idle adapter and no concurrent
updater remain prerequisites. The official updater was checked and not running.

The final probe compiles with `-Wall -Wextra -Werror`; nine invalid operation,
address, name and length cases exit before IOKit opens. Private copies preserve
the earlier probe and both versions used in this run, with per-session version
provenance. The [offline verifier](../tools/verify_ea9_backup.py) checks every
transmitted byte, paired reply, address, dump length and reconstructed file,
then compares the backup and known application. It never accesses hardware.

## Additional upper-flash contents

The complete read shows data beyond the installed application's padded span:

| Location | Observed contents |
| --- | --- |
| `0x5000` | Active application vector base and matching cached stock image |
| `0xA000` | A 64-byte block beginning `95 27 68 18 02 02`, shaped like CHECK |
| `0xA040` | A block beginning `95 27 68 18 01 01 01 08 00`, shaped like START/version 1.8.0 |
| `0xA080` | Another complete, byte-identical copy of the cached 20,172-byte application |
| `0xF080` through `0x1FFFF` | All bytes `0xFF`; last non-`0xFF` byte is at `0xF07F` |

These contents match across both full reads. Their origin is unknown. The
pattern is consistent with further reports/uploads having been consumed as
data while a previous stock upload remained armed; that is an inference, not a
captured historical transaction. The inspected startup still jumps to `0x5000`,
and no role for the second copy has been established. Do not label it a recovery
slot or erase it as presumed unused space.

A future profile-store layout must reserve explicit erase rows outside its
linked application and measured upload footprint. All-`0xFF` bytes alone do not
establish ownership. Versioned manifests, linker limits and install/read-back
tests must define that boundary.

## Next steps and physical measurement record

The [management-entry proposal](management-entry-design.md) now describes the
launch extension, alternative cap arrangement, handoff ownership and acceptance
checks. Prefer investigating the small launch extension after independent
recovery is qualified. The stock uploader is not a demonstrated programmer for
the bootloader region.

The remaining checks require physical access or instruments. These are pending,
not implied by the successful memory reads:

1. **Cold boot/reconnect — subsequently checked:** the user reports unplugging;
   a matching device re-enumerated with a new registry entry. CHECK, application
   vectors, named snapshots and one complete flash read match this baseline.
   Supply removal and reset timing remain unmeasured. Opening/closing a HID
   handle alone is not a power cycle.
2. **Routing, power removed:** identify the chip marking and accessible pads;
   map cap ground, supply, D−/D+ and mode contact by continuity. Record endpoints
   and resistance. Do not assume a contact is MCU supply merely because it
   carries USB VBUS.
3. **Powered levels:** use a high-impedance instrument to measure logic supply,
   PA23 at cold boot, and reset behavior. Compare cap and camera sessions
   separately. Record voltage, timing, reference ground and any pull network;
   the camera and cap must not provide competing power paths during this check.
4. **USB path:** confirm PA24/PA25 routing and supply behavior using the
   [Microchip USB application note](https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-42261-SAM-D21-USB_Application-Note_AT06475.pdf).
   USB-cap continuity and analog signal quality have not been inferred from HID
   enumeration alone.
5. **Independent debug:** identify SWDIO, SWCLK, reset, ground and target reference
   voltage. Specify a probe/tool configuration that disables automatic
   programming, erase and unlock, then repeat independent flash/user-fuse reads
   and compare hashes. Debug attachment can halt/reset the CPU even when the
   intended memory operations are reads. Revision D's DSU cold-plug erratum
   1.8.1 must be included in that procedure.
6. **Restoration and prototype:** separately prepare a concrete restoration
   experiment before modifying the loader. Only after recovery qualification
   test the motor-disabled management-entry application. Backups do not prove
   restoration or custom USB operation.

For each physical check record: date/operator; adapter/cap identity; instrument
and probe settings; power source; named test points; connection diagram; measured
values; raw trace/photo path; expected versus actual result; and the design
decision it supports. Mark every unperformed measurement **pending**. No
multimeter, logic-analyser or SWD connection was made in this run. A subsequent
user-reported unplug and measured re-enumeration are recorded above.

## Backup scope and preservation

The backup covers all main flash, a 64-byte user-row window containing the
documented user fuses, and the complete depicted 64-byte AUX1 block. It does not
capture every factory auxiliary region, the lockbit row or the MCU serial-number
words. Security status is recorded, not changed. Keep the original files and
provenance intact and preserve a second copy before a write experiment.

Private provenance records compiler/tool hashes, session commands, source
versions and file hashes. The reference catalogue/checksums include the new
evidence and errata. Public documentation contains decoded hardware facts and
hashes; USB serial strings, registry identity and proprietary firmware remain
in the ignored private folder.

# EDL / firehose — the universal bypass (and why it's hard)

**Applies to:** every Qualcomm BlackBerry. EDL (Emergency Download, USB
`05c6:9008`) runs in the **PBL ROM** and bypasses the OS, the authboot gate, and
the boot-partition write-protect — **if** you can enter it and have a signed
programmer.

---

## The two gates

1. **Entry.** Software EDL (`adb reboot edl`, `fastboot oem edl`) is **disabled**
   on production units. Entry is **hardware-only**: short eMMC CMD/DAT0 to GND at
   power-up, the factory test points, or an EDL "deep-flash" cable.
2. **Programmer.** EDL loads a **firehose programmer** signed with the OEM key
   fused into the SoC. A programmer from a different OEM is rejected.

## Where BlackBerry programmers exist

| SoC | Device | Programmer | Status |
|---|---|---|---|
| **MSM8953** | KEYone / Motion | `prog_emmc_firehose_8953_ddr.mbn` | **found** — extracted from the official ABL766 autoloader (`qcbc/fh/`); signed; supports `program`/`read`/`erase` |
| SDM660 | KEY2 | BlackBerry `fhprg` | public in `bkerler/Loaders` |
| MSM8992 | Priv | — | **none public** (community `MSM8992.mbn` is Huawei-signed → rejected) |

## What a programmer enables

With a valid programmer + EDL entry: full eMMC **read** (backup), `program`
(flash), and on some programmers `peek`/`poke` (arbitrary R/W). This is the path
to (a) a full device backup and (b) writing the `devinfo` unlock byte / a patched
boot partition.

## The catch

- **Entry is physical** — teardown/test-points/cable. For many owners this is
  the blocker.
- Even with a programmer, `devinfo` unlock is a **write** — back up first.

## Evidence / artifacts

- KEYone: `prog_emmc_firehose_8953_ddr.mbn` + `rawprogram0.xml` in the autoloader
  teardown (KEYone repo). `devinfo` = sector 425760.
- Priv: `notes/priv-research-log.txt` §15 (no MSM8992 programmer).
- Tooling: hub `toolchain/` + `bkerler/edl`.

## Related

- [authboot-rtas.md](authboot-rtas.md) — what EDL bypasses
- [bbss-boot-wp.md](bbss-boot-wp.md) — what EDL bypasses

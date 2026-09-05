# Research notes

Chronological session notes (raw, unedited) from the BlackBerry research. They
are provided as-is as a research aid.

## Session index (summary)

- `session2-findings.md` — initial recon
- `session3-authfull-decode.md` — autoloader / auth decoding
- `session7b-qseecom-audit.md` — QSEECOM audit
- `session7c-bb-kernel-source.md` — BlackBerry kernel source review
- `session7d-bide-detection-strategy.md` — boot image detection strategy
- `session7e-bide-audit.md` — boot image audit
- `session7f-pathtrust-snapshot.md` — path-trust snapshot
- `session7g-live-recon-3outcomes.md` — live recon
- `session7h-audit-conclusion.md` — audit conclusion
- `session7i-vtnvfsd-emmc-isp.md` — eMMC / ISP path
- `session7j-classic-emmc-access.md` — Classic eMMC access
- `session7k-bbss-insecure-pinned.md` — `bbss.insecure` flag pinned
- `session7l-boot0-writeprotect.md` — boot0 write-protect
- `session7m-mmcsdpub-wp.md` — mmcsdpub write-protect attempt
- `session7n-final-classic.md` — Classic summary
- `session7o-classic-real-root.md` — **real uid-0 root achieved**
- `session7p-dcmd-write-protect.md` — QNX MMC devctl constants + live tests
- `session7q-extcsd-bootwp.md` — `ext_csd` reveals power-on (temporary) boot WP
- `session7r-sdmmc-driver-re.md` — `sdmmc-rim-msmsdcc` reverse engineering
- `session7s-oleksandr-answer.md` — upstream researcher's guidance
- `session7t-proc-as-patching.md` — `/proc/<pid>/as` patch primitive
- `session7u-ext-struct-location.md` — (superseded hyphen attempt)
- `session7v-eio-is-switch.md` — **correction**: EIO is from the CMD6 SWITCH,
  not a flag gate
- `session7x-windows-connect.md` — Windows SSH connect ritual + full recipe
- `session7y-map-device-common.md` — `MAP_DEVICE` is common among QNX drivers
- `session8a-group-wrapper-emmc.md` — group-wrapper priv-esc unlocks `/dev/emmc`
- `session8b-wpgrp-patch.md` — WP group-patch targeting, driver re-map
- `session8c-writable-data-and-extcsd-loc.md` — **live eMMC driver `.data` R/W**;
  live `ext_csd` located (BOOT_WP=0x04, clearable)
- `session9a-live-extcsd-reread.md` — fresh boot-WP state; ranked CMD6 paths
- `session9b-ifs-verify-cap-diff.md` — **IFS integrity verifier DISPROVEN for
  custom IFS** (red-blink experiment); rooted cap.exe 3-byte diff; public tool
  haul from bb10.root.sx
- `session10a-passport-path-audit.md` — **Passport path audit**: `/dev/mem` is a
  `deadbeef` canary decoy (no physical RAM window); cross-process `/proc/pid/as`
  write = errno 312; Oleksandr `DCMD_SDMMC_ANY` / `sdmmc_raw_cmd` interface
  decoded (`FUNC_CLEAR_WP`); why the raw-command handler must be *added* (not
  just triggered); validity of autoloader/wipe/desolder ideas ranked
- `bug-report-pathtrust-fput-leak.md` — path-trust `fput` leak analysis
- `priv-research-log.txt` — device milestones

⚠️ These notes describe procedures that can brick a device. See
[../SECURITY.md](../SECURITY.md).

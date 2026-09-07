# Session 8d — r2 accurate devctl/resmgr map (radare2 now installed)

## Tooling
- **radare2 5.9.8 installed on Parrot** (`/bin/r2`, `/bin/radare2`). CLI works under the
  no-new-privileges sandbox. Use batch mode; r2pipe (python) not installed and pip blocked.
- Key flags: `r2 -q -e asm.arch=arm -e asm.bits=32 -e asm.thumb=true -B 0x10a00000 -c "<cmds>" sdmmc.elf`
- The on-device ELF `/tmp/opencode/kgsl/sdmmc.elf` is byte-identical to live code
  (first 4K match:0 diffs; live pattern @0x56c0 == ELF @0x56c0). So the ELF **is** the live
  module; r2@base `0x10a00000` is our ground truth.

## Corrected architecture (important — earlier manual capstone RE had 2 big errors)
1. **The module is BLENDED ARM + Thumb**, not pure Thumb:
   - `entry0` @`0x10a03d78` is **ARM** (crt0), does `blx main`.
   - `main` @`0x10a03cc0` (Thumb, 142B) sets up resmgr scaffolding (calls `0x10a03a5c`
     = resource-manager init; uses `__aeabi_uidiv`, `pathmgr_unlink`, magic `0x70800013`).
   - Application functions (`0x10a040cc+`) are Thumb.
2. **`0x10a0d574` is the `io_devctl` DISPATCHER** (138 blocks / 3428 B), a dcmd
   compare-table that tail-calls per-dcmd handlers. It decodes `r3=[r1,#0x24]` and matches:
   | dcmd               | tail-call handler |
   |--------------------|-------------------|
   | 0x42001a75         | 0x10a0ccc8        |
   | 0x40011a46 (extcsd read, the one we used) | 0x10a0d620 |
   | 0x40101a44 (CID)   | 0x10a0d5f2        |
   | 0x41081a74         | 0x10a0ca60        |
   | **0xc0181a14 (CARD_REGISTER)** | **0x10a0d492** |
   | 0xc0081a42         | 0x10a0d410        |
   | **0xc0201a11 (WRITE_PROTECT)** | **0x10a0fcec**  ← real WP handler |
   | **0xc0201a13 (WRITE_PROTECT+2)** | **0x10a0fdb4**  ← likely ERASE / group |
3. **WRITE_PROTECT handler is `0x10a0fcec`, NOT `0x10a0d664`.** (My prior note attributed
   it to `0x10a0d664`, which was a mis-decode of a nested block inside the dispatcher.)
   - `0x10a0fcec` builds the card table entry (`stride = [r1,#0xa]*0x2c8 + [r1,#0xb]*0x58 + base+0x1d0`),
     reads the devctl params from `[r5]`,`[r5,#4]`,`[r5,#0x10]` (the `mmcsd_mmc_write_protect`
     struct), checks **`cmp r1,#3` (mode), then bounds-gate** `= m½` (group extent), then for
     mode==1 calls `bl 0x10a0f48c`.
   - On gate/setup mismatch it returns **5** (matches our live WRITE_PROTECT returns of 5).
   - `0x10a0fda0: movs r0,5` is the "not allowed now" path; `0x10a0fda4: movs r0,0x16` is the
     bounds-error path.
4. **`0x10a0f48c` = `mmc_write_protect` worker.** Does the 64-bit `nlba / wp_grp` group division
   via `sym.__aeabi_uldivmod`, calls `0x10a075f8` (state res), `0x10a074ca`, `0x10a076c0`
   (program/switch helper). This is the real native CMD6 path for WP.
5. **`0x10a074ae` is the ext_csd pointer getter** (confirmed used by the WP worker) —
   matches prior live finding `ext_csd@live 0x10a1954f`.

## Consequence
- The dcmd handlers are reached by **tail-call (`b.w`) from the dispatcher `0x10a0d574`,
  NOT via a static `.data` FP table.** `axt` on the handlers shows no `.data` pointer hits.
  → Confirms: **no clean static FP** for these handlers; the resmgr-level `dispatch_t`/io_devctl
  FP we'd want to redirect is heap-allocated (dispatch_create) — statically unreachable.
- r2 found import surface: `sim_alloc_hba`, `simq_reset_dev`, `cam_*`, `mmap_device_io`,
  `hwi_*` — the hardware abstraction calls. No direct `sim_mmc_switch` import (mmc_switch is internal).

## Open decision for user
- **Route A (native devctl):** figure out the exact `mmcsd_mmc_write_protect` input layout the
  driver's handler expects (mode/group/start/len, plus the correct buffer/status header) so the
  gate at `0x10a0fcec` passes and reaches `0x10a0f48c`. We currently send it wrong → returns 5.
  The mode & group-setup must be valid (mode<=3, valid group). If the card already reports
  WP as set, mode 1 (set) on the boot area may be the right call — worth testing a *correct*
  input rather than assuming a hard gate. **Lowest risk, no code injection.**
- **Route B (injection/FP-redirect of a static slot):** still needs a static FP; handler table is
  tail-call so not exposed. Only the heap `dispatch_t` remains → hard.
- **Route C (higher-ability / signed carrier):** unchanged.

Recommendation: exhaust **Route A** — craft a correct WRITE_PROTECT devctl (proper
`mmcsd_mmc_write_protect` struct + io_devctl input header, mode=1, valid group) so the native
gate passes. Test incrementally (start with a harmless read-like field / a reserved group) before
attempting the real boot-area clear, on the sacrificial Classic.
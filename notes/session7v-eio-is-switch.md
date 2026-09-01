================================================================================
SESSION 7V - CORRECTION: EIO IS FROM CMD6 SWITCH, NOT THE "ATTACHED" FLAG
================================================================================
2026-08-30. Corrects a wrong conclusion in 7t/7u.

[1] WHAT WE DID
  - Patched .bss @0x10fe9630 (deadbeef round-trip) - confirmed /proc/as WRITE
    works on data, NOT code (code = "Server fault", read-only).
  - Located boot0 partition-entry candidate @0x10fea314 (ptype=1, nlba=8192,
    slba=0) and its "flag" @+0x28 (0x10fea33c) = 0. Patched to 1. NO EFFECT:
    WRITE_PROTECT still EIO. => that was a FALSE POSITIVE (struct had pointers,
    not clean partition fields).

[2] DECISIVE DIAGNOSTIC (new)
  WRITE_PROTECT SET mode=0 on /dev/emmc/boot0 (via Disk_Drivers group):
    nlba=1      -> ret=5   (EIO)
    nlba=8192   -> ret=5   (EIO)
    nlba=0xFFFF -> ret=22  (EINVAL)
    nlba=0x20000-> ret=22  (EINVAL)
  => The range check (nlba vs partition size) is AFTER the 0xe53a availability
     check in the handler. Since large nlba gives EINVAL (reaches range check),
     0xe53a actually RETURNS 1 (passes) for boot0. The EIO is from the NEXT
     stage: mmc_write_protect -> mmc_switch (CMD6 SWITCH to ext_csd[173]).
  => CONCLUSION: there is NO "attached flag" gate. 7t/7u flag-patch theory is
     WRONG. The driver DOES reach the boot_wp switch, but the SWITCH FAILS.

[3] PROOF FROM DRIVER slog2 (definitive)
  slog2info -b devb_sdmmc_rim_msmsdcc shows (timestamps match our tests):
    "sdmmc_write_protect: switch ext_csd_boot_wp"   (x2, = each SET attempt)
  This string is the ERROR log at 0xf48c+0xa4 (logged only when mmc_switch
  returns nonzero at 0xf5a2 cbz). => the driver issues CMD6 SWITCH to
  ext_csd[173] (index 0xad) but the CARD rejects it (SWITCH_ERROR).

[4] WHY THE SWITCH FAILS (analysis)
  - 0x8240 (raw CMD6 send) builds arg = (mode<<24)|(index<<16)|(value<<8)|cmdset
    = 0x03AD0001 (WRITE byte 173 = 0x00). Correct per JEDEC.
  - value written = wp->mode & 1 (masked at handler 0xfd18). For mode=0 => 0x00.
  - ext_csd[173] currently 0x04 = B_PWR_WP_EN (power-on WP, bit2). Writing 0x00
    SHOULD clear it (BOOT_CONFIG_PROT=0). But card returns SWITCH_ERROR.
  - Likely cause: eMMC rejects clearing B_PWR_WP_EN while boot partitions are
    not the "active" partition, OR a vendor-specific sequence is needed (e.g.
    write B_PERM_WP_DIS=0x10 first), OR the boot partition must be selected via
    ext_csd[179] PARTITION_ACCESS before the WP register is writable.
  - This matches Oleksandr: his patch = "execute any emmc command" (VUC_CMD),
    i.e. RAW command passthrough, NOT the standard WRITE_PROTECT path. The raw
    path lets us send the exact CMD6 (or the vendor sequence) the standard
    handler can't.

[5] CORRECTED PATH FORWARD
  - Need RAW CMD6 SWITCH (or vendor sequence) = DCMD_MMCSD_VUC_CMD, which the
    stock driver returns ENOTTY for (7p). That is EXACTLY what sdmmc.zip adds.
  - Since code is read-only via /proc/as, we cannot patch the dispatch table in
    .text. Options:
    (a) Find a WRITABLE hook (function pointer in .data/.got) that the devctl
        path goes through, and redirect it to 0x76c0 (mmc_switch) with crafted
        args - hard but maybe doable.
    (b) Use /proc/<pid>/ctl + debug API (DCMD_PROC_STOP/SETGREG/CURTHREAD) to
        hijack a driver thread to call 0x76c0 - complex.
    (c) Figure out the vendor sequence that makes the STANDARD WRITE_PROTECT
        succeed (e.g. set PARTITION_ACCESS=1 for boot0 first, or write
        B_PERM_WP_DIS). Try the CARD_REGISTER write? (it's read-only).
    (d) Accept raw-command passthrough requires code injection; pivot to
        ISP/desolder or ask Oleksandr for the technique.

[6] KEY FACTS (unchanged, still true)
  - boot WP = power-on temporary (B_PWR_WP_EN=0x04), clearable in principle.
  - /proc/as: data writable, code read-only.
  - WRITE_PROTECT handler DOES contain the CMD6 switch code (0xf48c -> 0x76c0
    -> 0x8240), index 0xad.
  - VUC_CMD missing (ENOTTY). GET_CID wrong (returns ENOTTY for 0xC0481A10; the
    driver uses 0x40101a44 -> handler 0xd5f2 for CID).

ARTIFACTS:
  /tmp/pp/{diag_eio.py, patch_flag.py, restore_flag.py, one.bin, zero.bin}
  /home/stanw47/priv-research/work/session7t-proc-as-patching.md (flag theory - superseded)
================================================================================

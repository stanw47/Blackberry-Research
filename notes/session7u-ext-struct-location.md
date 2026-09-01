================================================================================
SESSION 7U - ext-STRUCT LOCATION + CODE-RO/DATA-RW CONSTRAINTS - 2026-08-30
================================================================================
Follow-up to 7t. Goal: locate the writable `ext` (SIM_MMC_EXT) struct so we can
set boot0's per-partition "attached" flag (offset 0x1f8) and unblock WRITE_PROTECT.

[1] CONFIRMED CONSTRAINTS (from 7t, re-verified)
  - .data/.bss WRITABLE via /proc/741404/as (wrote deadbeef -> read back ok).
  - .text READ-ONLY ("Server fault on msg pass" on write). Cannot patch code or
    the dispatch literal pool (0xd644, in .text).
  - Runtime base 0x10fce000 verified byte-for-byte (dispatch 0xd574, handler
    0xfd00/0xfd40 all match the pulled binary).

[2] WRITABLE DATA LAYOUT
  - .data/.bss vaddr 0x18ea4 (memsz 0x2c1c) -> runtime 0x10fe6ea4..0x10fe9ac0.
  - Dumped ddata.bin (11292 bytes). First ~0x100 bytes are GOT/function pointers
    (pointing into 0x10fdxxxx code). No obvious inline ext struct here -> ext is
    HEAP allocated, not a static global.

[3] DRIVER HEAP MAPPINGS (pid 741404)
  - The mappings dump shows a huge anonymous (no-file) heap region spanning
    ~0x16a91000 .. 0x16c64xxx (and more). flags 0x02080002 = RW (writable anon).
  - The ext struct + its targets[].partitions[] array lives somewhere in this
    heap. Need to locate it by scanning for the boot-partition signature:
      ptype=1 (MMC_PTYPE_BOOT), pflags (MMC_PFLAG_WP?), config, slba=0,
      elba=..., nlba=8192 (boot0 = 4MB/512), name[...]
    Reference struct stride from disasm: MMC_TARGET stride 0x2c8, partition
    stride 0x58, and the "attached" flag at partition+0x1f8 (per 0xe53a).

[4] DCMD_MMCSD_GET_CID note
  - Standard DCMD_MMCSD_GET_CID (0xC0481A10) returns ENOTTY(25) on this driver.
  - The driver's own CID/CSD handlers are at custom DCMDs (0x40101a44 -> 0xd5f2
    reads CID, 0x40011a46 -> 0xd620 reads ext_csd[0xa8], 0x40011a45 -> 0xd60e
    reads ext_csd[0xb5]). Not needed for the flag patch.

[5] OPTION B RESULT (unmount)
  - Unmounted /accounts/1000/removable/sdcard (sd0) OK.
  - boot0/boot1 are NOT mounted anyway, so unmount does NOT change their 0x1f8
    flag. The "unmount + exclusive access" hint (Oleksandr) applies to READING
    eMMC firmware on Passport, not to boot0 write on Classic. Option B is a
    dead end for the WRITE_PROTECT gate.

[6] NEXT (Option A, concrete)
  - Scan the driver heap for the boot partition table: look for u32 pattern
    ptype=1 at stride 0x58 within a 0x2c8 target block, with slba=0 and
    nlba=8192 nearby. The "attached" flag @ +0x1f8 is a u32; set it = 1.
  - OR: find the ccb->ext pointer by issuing a live devctl and reading the
    GOT/global that holds `ext`. The handler does r6 = [ccb+8]; the ccb is
    built by cam-disk. Could trace the global in .data that points into heap.
  - After setting the flag, re-issue DCMD_MMCSD_WRITE_PROTECT action=SET mode=0
    -> should call mmc_switch(0xad, 0) -> clears B_PWR_WP_EN -> boot0 writable.

ARTIFACTS:
  /tmp/pp/{ddata.bin, disp.bin, rd40.bin, getcid.py, devctl_wpmatrix.py}
  /home/stanw47/priv-research/sdmmc-driver/devb-sdmmc-rim-msmsdcc
================================================================================

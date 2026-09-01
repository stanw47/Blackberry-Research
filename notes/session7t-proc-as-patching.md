================================================================================
SESSION 7T - /proc/as PATCHING PRIMITIVE + CODE-IS-RO FINDING - 2026-08-30
================================================================================

[1] MEMORY PATCH PRIMITIVE (works, with constraints)
  - open /proc/<pid>/as as root (via __root). devuser/g_Disk_Drivers get EPERM.
  - READ: dd if=/proc/741404/as bs=1 skip=<vaddr> count=N  (works, as root)
  - WRITE to .data/.bss: WORKS. (wrote deadbeef to 0x10fe9630, read back ok)
  - WRITE to .text (code): FAILS - "Server fault on msg pass" (read-only page).
  => We can patch WRITABLE data, NOT code. This kills the "patch dispatch table"
     idea (dispatch + literal pool @0xd644 are in .text RO).

[2] DRIVER RUNTIME BASE CONFIRMED
  - /proc/boot/devb-sdmmc-rim-msmsdcc loaded at base 0x10fce000 (ELF header there).
  - Code at file off X == runtime 0x10fce000 + X. Verified dispatch 0xd574,
    handler 0xfd00, and 0xfd40 byte-for-byte match the pulled binary.
  - .data/.bss: vaddr 0x18ea4 (memsz 0x2c1c) -> runtime 0x10fe6ea4..0x10fe9ac0.

[3] THE EIO GATE (why WRITE_PROTECT devctl returns EIO)
  - WRITE_PROTECT handler 0xfcec calls 0xe53a (availability check) at 0xfd50.
    if 0xe53a != 1 -> 0xfda0 -> r0=5 (EIO).
  - 0xe53a logic:
      r6 = [ccb+8] = ext
      r3 = [ext+4]; test bit31 -> if clear, call 0xe4ce(r2=0x13) init
      r6 += target*0x2c8 + lun*0x58
      r3 = [r6 + 0x1f8]  ; per-partition "attached/ready" flag
      if r3 != 0 -> return r0 (=1)
      else call 0xe4ce(r2=6) "attach partition" and return its result
  => The EIO is because boot0's partition flag @0x1f8 is 0 and the attach call
     (0xe4ce) fails (or returns error). If we set that flag, WRITE_PROTECT
     reaches the mmc_switch(0xad) boot-WP code that is ALREADY in the driver.

[4] NOTE: CARD_REGISTER (0xd492) also calls 0xe53a but SUCCEEDS (returns ext_csd),
  so the ext+4 bit31 "driver ready" is set, and the card-level register read is
  fine. Only the PARTITION-level 0x1f8 flag for boot0 is 0. (boot0/boot1 aren't
  "attached" as normal block partitions; consistent with Oleksandr's "unmount +
  exclusive access" note.)

[5] WHAT THIS MEANS
  - We don't need to add VUC_CMD code (which would need RO .text patch). The
    driver's own WRITE_PROTECT already does mmc_switch(EXT_CSD_BOOT_WP=0xad).
  - We need to either:
    (a) find the `ext` struct in writable heap and set boot0's 0x1f8 flag = 1,
        then issue WRITE_PROTECT SET mode=0 to clear B_PWR_WP_EN; OR
    (b) find where 0xe4ce(r2=6) attach fails and satisfy it (unmount/exclusive).

[6] NEXT
  - Locate the `ext` (SIM_MMC_EXT) struct address: scan driver heap mapping for
    the partition table signature (ptype=1 BOOT, slba=0, nlba=8192 for boot0),
    or trace the ccb->ext pointer from a live devctl.
  - Then write 1 (or the attach-flag value) to [ext + target*0x2c8 + lun*0x58
    + 0x1f8] for boot0, and retry WRITE_PROTECT SET mode=0.

ARTIFACTS:
  /home/stanw47/priv-research/work/session7q-extcsd-bootwp.md (ext_csd finding)
  /home/stanw47/priv-research/work/session7r-sdmmc-driver-re.md (driver RE)
  /home/stanw47/priv-research/work/session7s-oleksandr-answer.md
  /home/stanw47/priv-research/sdmmc-driver/devb-sdmmc-rim-msmsdcc (binary)
  /tmp/pp/{devctl_cardreg.py,devctl_wpmatrix.py,ddata.bin,disp.bin,rd40.bin}
================================================================================

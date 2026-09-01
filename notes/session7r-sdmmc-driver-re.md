================================================================================
SESSION 7R - RE OF sdmmc-rim-msmsdcc (Classic MMC driver) - 2026-08-30
================================================================================
Follow-up to 7q (ext_csd revealed boot WP = power-on temporary). Now dissecting
the actual driver to find how to invoke CMD6 SWITCH to clear B_PWR_WP_EN.

[1] DRIVER IDENTITY
  - Process: sdmmc-rim-msmsdcc (2 instances; Classic: pid 741404 + 2330666)
  - Binary: /proc/boot/devb-sdmmc-rim-msmsdcc (ELF32 ARM EABI5, PIE/shared, stripped)
  - Downloaded to: /home/stanw47/priv-research/sdmmc-driver/devb-sdmmc-rim-msmsdcc
    (size 114780)
  - This is BlackBerry's fork of the QNX devb-sdmmc (rim = RIM vendor name).

[2] DCMD DISPATCH (devctl handler) - located at 0xd574 (Thumb)
  Reads dcmd from [r1,#0x24], compares against literal pool @0xd644..0xd65c:
    dcmd              handler
    0x42001a75        -> 0xccc8   (DEVINFO, via 0xd5ca)
    0x40011a46        -> 0xd620   (read ext_csd byte 0xa8, via 0xd620)
    0x40011a45        -> 0xd60e   (read ext_csd byte 0xb5)
    0x40101a44        -> 0xd5f2   (read CID, 0xd5f2)
    0x41081a74        -> 0xca60   (via 0xd5c2)
    0xc0181a14        -> 0xd492   (DCMD_MMCSD_CARD_REGISTER, via 0xd5e2)
    0xc0081a42        -> 0xd410   (via 0xd5ea)
    0xc0201a11        -> 0xfcec   (DCMD_MMCSD_WRITE_PROTECT, via 0xd5d2)
    0xc0201a13        -> 0xfdb4   (via 0xd5da; WRITE_PROTECT+2 = ERASE)
    (fallthrough     -> 0xd63a   sets [r4,#0x28] = 0x80000001 -> ENOTTY)
  => CONFIRMS 7p result: VUC_CMD (0xC0441A16) is NOT in the table -> ENOTTY.

[3] DCMD_MMCSD_WRITE_PROTECT handler (0xfcec)
  - Loads target/lun from [r1,#0xa]/[r1,#0xb], indexes ext->targets[]/partitions[]
    (0x2c8 * target + 0x58 * lun + 0x1d0 into ext).
  - wp struct = [r1,#0x30]; reads action [r5], mode [r5,#4], lba/nlba [r5,#0x10/0x18].
  - action (sb) computed via table lookup at [pc+...]+0xd9 (sign-extended byte).
  - Calls #0xe53a (some check) then #0xf48c (the real write-protect function).

[4] write-protect core (0xf48c) - THE MMC SWITCH CALLS
  - 0xf4f0: bl #0x75f8  (get card / acquire)
  - 0xf51e: cmp sl, #0x1c  -> if sl != 0x1c skip switch
  - 0xf532 branch (r5 & 7 == 0): 
        ldrb [ext_csd] +0xab (=171 EXT_CSD_USER_WP); mode tst r7,#1
        bl #0x76c0 with (r0=hba, r1=1, r2=3, r3=0xab=171) -> switch USER_WP
  - 0xf58c branch (r5 == 2): 
        bl #0x76c0 with (r0=hba, r1=1, r2=3, r3=0xad=173) -> switch BOOT_WP
        value passed in r7 (=mode).
  => 0x76c0 = mmc_switch(hba, flgs=1, cmdset=1, mode=3 WRITE, index, value).

[5] mmc_switch (0x76c0) = CMD6 SWITCH wrapper
  - bl #0x73b0 (lock/acquire), then bl #0x8240 (the actual CMD6 send with
    (cmdset, mode, index, value)), then unlock #0x73b0.
  - 0x8240 is the low-level CMD6 SWITCH implementation.

[6] KEY CONCLUSION
  - The driver ALREADY contains the exact code to write ext_csd[173] BOOT_WP
    (via WRITE_PROTECT devctl -> 0xf48c -> mmc_switch 0x76c0, index 0xad).
  - The action/mode routing: action selects via table; mode r5 selects USER_WP
    (r5&7==0) vs BOOT_WP (r5==2). Need to decode the action->sb table and the
    sl==0x1c partition-type gate to craft a working WRITE_PROTECT devctl.
  - Alternatively patch driver memory to call 0x76c0(hba,1,3,0xad,0) directly.

[7] NEXT
  - Decode action table + sl (0x1c) gate; determine exact WRITE_PROTECT action/
    mode/lba/nlba values that route to the 0xad (BOOT_WP) switch with value 0.
  - If the devctl route is gated, use /proc/741404/as memory patch (unlock_path_trust
    technique) to invoke mmc_switch directly, or jump to 0x76c0 with crafted regs.

ARTIFACTS:
  /home/stanw47/priv-research/sdmmc-driver/devb-sdmmc-rim-msmsdcc
  Disassembly via capstone (host) - functions 0xd574 (dispatch), 0xfcec
  (WRITE_PROTECT), 0xf48c (wp core), 0x76c0 (mmc_switch).
================================================================================

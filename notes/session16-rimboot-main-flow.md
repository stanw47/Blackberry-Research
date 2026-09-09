==============================================================================
SESSION 16 - rimboot_update MAIN FLOW FULLY MAPPED: -x DOES NOT BYPASS WP CHECK
==============================================================================
2026-09-09, offline disassembly of /tmp/opencode/rimboot_update (19336 B,
rimboot_update-qct, capstone Thumb2).

------------------------------------------------------------------------------
[1] GETOPT FLAGS -> STACK SLOTS
------------------------------------------------------------------------------
  -n "No shutdown after upgrade"       -> [sp,#0x2c]=0
  -t "Test if update available"        -> [sp,#0x30]=1
  -d "Dump only"                       -> [sp,#0x34]=1
  -x "Force"                           -> [sp,#0x38]=1
  -f <file> bootrom to upgrade to      -> parsed/opened in getopt loop (0x0dea..)
  getopt long names: gpt_valid(0x21ef) =-gpt_valid; [sp,#0x30/0x34/0x38] set
  per option; usage handler 0x0f5e prints Usage string 0x2b9f.

------------------------------------------------------------------------------
[2] POST-PARSE CONTROL FLOW (definitive)
------------------------------------------------------------------------------
  0x0fe0 getopt... returned -1 -> fall through
  0x0fea r3=[sp,#0x34] (dump) ; if sl!=0 r3|=1
  0x0ffc cbz r3 -> 0x105c      ; if no -d, go to main path
  ; ---- -d branch 0x1002..0x105a: prints Board bootrom info / File bootrom
  ;      info (strings 0x2c3f/0x2c6c), returns rc=2 at 0x1146 (no update).

  0x105c main path:
  0x105c r3=[pc]; r2=[sp,#0x38] (force)
  0x1064 bne 0x10e6            ; if -x: SKIP gpt/bootrom validation block
  0x1066..0x10e4  (no -x): reads gpt, validates bootrom via bl 0x2110
       (validate_bootrom); any fail -> ERROR + return rc=1 (0xd78). This is
       the ONLY block -x skips.

  0x10e6 r3=[sp,#0x30] (test)
  0x10e8 cbz r3, 0x10f8        ; if no -t -> fall into WP CHECK
  0x10ea..0x10f6 (with -t): print "Test if update available", return rc=3.

  0x10f8 bl 0x19be             ; boot_sector_write_protected()  <== REACHED
       WITH or WITHOUT -x (as long as neither -d nor -t)
  0x10fc cmp r0,#-1
  0x1102 beq 0xd78             ; r0==-1 -> return rc=1 (abort, NO NV set)
  0x1106 cmp r0,#1
  0x1108 bne 0x114a            ; r0==0 -> proceed branch
  0x110a..0x1120 (r0==1, power-on): print "Boot sector is write protected,
       setting NVRAM bits"; bl nvram_wp(1); print "removing boot sector write
       protection"; b 0x13e4 (power down / ask to cycle)
  0x1136..0x1142 (nvram_wp(1) failed): error prints
  0x114a (r0==0): ldr r0,[sp,#0x30]; bl 0x1dc4 nvram_wp()  (clean WP bits);
       then write/verify/flash path (0x2000+ helper fns, "Writing bootrom (%d
       bytes)...", "Verifying bootrom...", force_relearn, "RIMBOOT Upgrade
       complete" rc=0)

------------------------------------------------------------------------------
[3] boot_sector_write_protected (0x19be) EXACT BIT LOGIC
------------------------------------------------------------------------------
  0x1a0e reads ext_csd via devctl 0xc0181a14 (MMCSD_CARD_REGISTER):
       struct{action=0,type=2(EXT_CSD),address=0,length=512} + 512B buffer
  0x1a76 ldrb.w r2,[r6,#0xad]  ; r2 = ext_csd[0xAD] (=BOOT_WP byte 173)
  0x1a7a lsls r3, r2, #0x1d    ; bit2 -> sign
  0x1a7c bpl #0x1a90           ; if bit2 (0x04) NOT set -> test bit0
  0x1a7e..0x1a8e  bit2 SET: print "Flash boot regions are permanently locked
       : %x" (0x2469); return -1
  0x1a90 ands r0, r2, #1       ; bit0 (0x01)
  0x1a94 beq #0x1aa4           ; not set -> return 0
  0x1a96..0x1aa2  bit0 SET: print "Flash boot regions is power-on protected
       : %x" (0x2499); return 1

=> LIVE DEVICE: BOOT_WP=0x04 => bit2 SET => tool returns -1
   => main aborts rc=1 ("permanently locked"), NEVER sets NVRAM bits, never
      writes. This holds for BOTH bare and -x invocations ( -x skips only the
      gpt/bootrom validation at 0x1064 ). Only -d/-t avoid reaching 0x10f8.

------------------------------------------------------------------------------
[4] SEMANTIC CONFLICT WITH 7q/8b (MUST RESOLVE BEFORE ANY FLASH)
------------------------------------------------------------------------------
  * bb_kernel_AAO474/mmc.h lines 290-293:
        EXT_CSD_BOOT_WP_B_PWR_WP_DIS (0x40) bit6
        EXT_CSD_BOOT_WP_B_PERM_WP_DIS (0x10) bit4
        EXT_CSD_BOOT_WP_B_PERM_WP_EN  (0x04) bit2
        EXT_CSD_BOOT_WP_B_PWR_WP_EN   (0x01) bit0
    => 0x04 = B_PERM_WP_EN = PERMANENT write-protect enable.
       kernel MMDR/C spec semantics: bit2 = permanent engagement.
  * rimboot_update treats bit2 as "permanently locked" (return -1).
  * session7q/8b interpreted live 0x04 as "bit2 = B_PWR_WP_EN = power-on
    temporary" -- THIS NOW CONFLICTS with the kernel macro set + rimboot's own
    bit2 branch. 0x04 is assigned to PERM_WP_EN in the BB kernel, while
    PWR_WP_EN is 0x01 (bit0).
  * BUT: BOOT_WP_STATUS(0xae)=0x0A = 0b1010 -> indicates >one status bit.
    Per earlier Exascend eMMC5.1 datasheet note: bit0=power-on status,
    bit2=permanent status, bit4=perm-dis, bit6=pwr-dis. 0x0A = bits 1+3,
    which does NOT fit the bit0/bit2 read of that datasheet linearly --
    suggests per-boot-area status (B_PERM_WP_EN for boot1/B_PWR_WP_EN for
    boot2, etc.). Not yet fully decoded. Live values match the Passport
    session9a read (0x04 / 0x0A) exactly.
  * Field-updatable boot0 in production + session8b "in-session clear" both
    argue the WP is NOT a one-time fuse. Candidate explanations:
      (a) RIM's "permanent" = GPT/boot-chain-enforced, and PBL + NV bits
          0x2019 re-arm/clear per upgrade window (oleksandr flow).
      (b) The bit meaning on this eMMC differs between the day rimboot was
          built (2013) and kernel AAO474 conventions; live 0x04 may STILL be
          the "power-on" state the tool was built around, and rimboot's bit2
          branch would have matched a device where 0x04 was truly permanent.
      (c) Device genuinely PERM locked -> -x/-f dead end; only cap.exe/NV
          bootrom lane could matter.

------------------------------------------------------------------------------
[5] OPERATIONAL CONSEQUENCE
------------------------------------------------------------------------------
  - -t and -d are the ONLY safe probes (return rc=3/rc=2 BEFORE 0x10f8).
  - Any real -x -f run on the live Passport as of latest EXT_CSD read would
    print "Flash boot regions are permanently locked : 4" and exit rc=1 with
    NO writes and NO NVRAM changes (bit2 branch never calls nvram_wp). So
    executing -x -f is NOT itself a write risk TODAY -- it asserts the lock.
  - The NV-bits 42/43 + power-cycle cable (oleksandr) is the ONLY plausible
    way to change ext_csd[0xad] between boots. Test: arm bits 42/43 -> physical
    power cycle -> IMMEDIATELY re-read BOOT_WP before anything else. If still
    0x04, either the bits were consumed by bootrom (recheck NV) or perm.

------------------------------------------------------------------------------
[6] STRINGS (authoritative offsets)
------------------------------------------------------------------------------
  0x238c /dev/emmc/boot0
  0x2469 Flash boot regions are permanently locked : %x
  0x2499 Flash boot regions is power-on protected : %x
  0x2781 nvram_wp / 0x278a /dev/nvram
  0x27ff BEFORE --> WP : %d WP_PROGRESS : %d
  0x28b5 AFTER  --> WP : %d WP_PROGRESS : %d
  0x2d96 Boot sector is write protected, setting NVRAM bits
  0x2dca removing boot sector write protection
  0x2df0 Previous reset was not a proper power cycle...
  0x2e61 Please power cycle your board to allow for the upgrade to happen
  0x2fc3/0x2f8f/0x2f3b  Writing/Verifying/force_relearn bootrom
  0x31fd RIMBOOT Upgrade complete.
  0x22a1 ... partition; 0x2332 hw id / security mismatch strings (validation)
  0x2b9f Usage; 0x2bdc returns legend (0:success 1:error/wp 2:no-upg 3:avail)

[7] NV-BITS UNLOCK TEST - NEGATIVE RESULT (2026-09-09, live device)
------------------------------------------------------------------------------
  Test executed per [5]: NV 0x2019 bits 42/43 armed (0x0C at byte5, verified),
  physical power-cycle performed (device fully off, powered back on, dev-mode
  re-enabled, OS booted), IMMEDIATELY re-read before anything else:
      BOOT_WP[173]        = 0x04   (unchanged)
      BOOT_WP_STATUS[174] = 0x0A   (unchanged)
      NV 0x2019 byte5     = 0x0C   (bits NOT consumed by bootrom; unchanged)
  => The PBL/bootrom does NOT clear ext_csd[0xad] on boot when NV 0x2019
     bits 42/43 are set. The oleksandr power-cycle-with-bits-armed theory is
     REFUTED on this unit. Confirms [4](c): live 0x04 is being read as a
     genuine perm lock by rimboot, and this machine stays bit2 across boots.
  This also empirically validates [5]: the tool's -x -f would print
  "permanently locked : 4", rc=1, no writes. 0x04/0x0A reproduced a 3rd time
  (matches session9a + session16 [4]).
  REMAINING hypotheses, ranked:
    (A) 0x04 is stock on this build but UPGRADABLE via official updater lane
        (SBL1 carried in autoloader; boot-chain/cap.exe gate) - bits 42/43
        gate the UPDATER's CMD6 switch, NOT the bootrom. [session15 plan]
    (B) Device is one-time-fuse locked (0x04 = true PERM) - only an NV/boot
        update through a signed factory path could ever matter. Dead end for
        -x -f as written.
    (C) 0x04 bit meaning differs on this eMMC part vs kernel/r0mboot headers
        (part datasheet needed) - resolve by DCMD_MMCSD whoami/vendor probe.
  NEXT CANDIDATE TESTS (cheapest first, all read-only except explicit CMD6):
    1. Re-read NV immediately after a boot cycle with bits CLEARED (0x00)
       to rule out polarity inversion.
    2. Empirical -x -f<dummy-file> probe: asserts lock rc=1 (expected), no
       writes (per [5]) - confirms tool behavior live, ~1 min.
    3. Vendor/manufacturer ID via EXT_CSD/CSD to identify eMMC part and
       obtain exact BOOT_WP/BOOT_WP_STATUS bit docs (tests C).

ARTIFACTS / REF
  /tmp/opencode/rimboot_update  (original 19336B)
  disasm of main 0xc70-0xfda, 0xfda-0x1150, 0x19be-0x1ab4 (this session)
  bb_kernel_AAO474/include/linux/mmc/mmc.h:290-293
  notes: session7q-extcsd-bootwp.md, session8b-wpgrp-patch.md,
         session9a-live-extcsd-reread.md, session15-oleksandr-unlock
==============================================================================
================================================================================
SESSION 18 - NV POWER-CYCLE RITUAL: DECISIVE NEGATIVE (PERMANENT WP CONFIRMED)
================================================================================
2026-09-09. Forced rimboot's r0==1 "boot sector is power-on protected" branch to
arm the NV WP bits, power-cycled, re-read EXT_CSD -> BOOT_WP still 0x04.

[0] TL;DR
  The Oleksandr-style NV-arming power-cycle flow DOES NOT clear the Passport's
  boot0 write-protect. BOOT_WP[173] stayed 0x04 (B_PERM_WP_EN, bit2) and
  BOOT_WP_STATUS[174] stayed 0x0A before AND after the clean power-cycle.
  Boot0 is PERMANENTLY write-protected at the card level. The NV bits that
  rimboot arms only govern POWER-ON wp (bit0); this card's bit2 is set, which
  rimboot itself maps to "permanently locked : 4" and refuses to touch.
  => The rimboot/software NV route is CLOSED on this unit.

[1] WHAT WAS DONE
  - Built rimboot_update_wparm from stock rimboot_update (flat ELF, VA==offset,
    md5 2a4a709ac93bf77f2da9d0f639e55bdb) with TWO patches:
      0x1a7c: 08 d5 -> 08 e0  (bpl 'permanently locked' -> jump over it)
      0x1a90: 12 f0 01 00 -> 01 20 00 bf
              (ands r0,r2,#1 -> movs r0,#1; nop)   [boot_sector_write_protected -> ret 1]
    => main took the r0==1 branch (0x110a): printed "Flash boot regions is
       power-on protected : 4", called nvram_wp(1), then shutdown.
  - Ran via SSH tunnel on live Passport:
      BEFORE --> WP : 0 WP_PROGRESS : 0
      AFTER  --> WP : 1 WP_PROGRESS : 1
      Shutting down : removing boot sector write protection
    Device powered off via QCT powerdown (init_shutdown_8941, track reg 88e=0x42).
  - Tunnel had dropped (java proc died on power-off). Re-established via
    setsid blackberry-connect; keep it detached or it dies with the shell.
  - Re-read EXT_CSD full 512 bytes via g_Disk_Drivers python3.11 probe.

[2] HOW EXT_CSD WAS READ (and why earlier single-byte reads were bogus)
  - probe_extcsd_full.py: devctl DCMD_MMCSD_CARD_REGISTER (0xC0181A14),
    MMC_REG{action=0,type=2,address=0,length=512} on /dev/emmc/boot1.
  - The OLD probe_extcsd.py did single-byte reads at address=0xA8..0xC8 and
    printed garbage (e.g. BOOT_WP=0x00). Root cause: the driver returns a
    buffer shifted relative to the requested address. Old raw[0xA8:0xC8] ==
    new full-read raw[0x10:0x30] ("09 03 00 00 e9 00 00 00 e9 ..."). All
    single-byte reads in the old probe were reading the wrong buffer segment.
    Only a full 512-byte read at address=0 maps to real JEDEC EXT_CSD bytes.
  - post-power-cycle values (device: /dev/emmc/boot1):
      B_BOOT_INFO[0xA2]          = 0x02
      BOOT_CONFIG_PROT[0xB2]     = 0x10
      BOOT_WP[173]               = 0x04   (bit2 B_PERM_WP_EN)  <-- UNCHANGED
      BOOT_WP_STATUS[174]        = 0x0A
      USER_WP[171]               = 0xD0
      PARTITION_CONFIG[179]      = 0x48
      BOOT_BUS_WIDTH[177]        = 0x04
  - raw[0xA0:0xC0] = 07 00 02 00 00 00 05 1f 20 01 00 d0 00 04 0a 01 00 04 10 48 ...

[3] INTERPRETATION
  - bit2 of BOOT_WP is B_PERM_WP_EN (permanent write-protect enable). This is
    the bit rimboot's own boot_sector_write_protected() checks and prints as
    "permanently locked : 4" -> returns -1 -> hard abort (session16).
  - The NV WP/WP_PROGRESS bits that nvram_wp() manages control power-on WP
    (bit0), which was never set. Arming them then power-cycling is the CORRECT
    procedure for bit0 protection but does nothing for a permanent bit2 lock.
  - BOOT_CONFIG_PROT[0xB2]=0x10 (bit4) reads as boot WP protected, consistent
    with a fused/permanent boot-area configuration on this production unit.
  - Conclusion: no in-session, no power-cycle software path can clear boot0 WP.
    Confirms and strengthens session16's manual NV test (also negative).

[4] STATE / NEXT ROUTES (unchanged priorities)
  a) PATCHED DRIVER / .data-thunk CMD6 (sessions 9a[4], 10a[5]): still the only
     live-software route, but requires writing the raw mmc_switch(0xAD) handler
     that the stock driver lacks. NB: with bit2 fused, even a successful CMD6
     write to BOOT_WP[173]=0 may be rejected at the card -> likely effectively
     closed, but worth ONE clean shot later since BOOT_CONFIG_PROT is low.
  b) HARDWARE: EDL/bblink raw loader bypass (needs cold-boot into EDL) or
     desolder / ISP-on-eMMC (balika path). Both bypass card-level WP entirely.
  c) bblink lane (session13) remains viable on this unit.

[5] INFRA NOTES (for faster reconnects)
  - blackberry-connect MUST be launched detached (setsid ... </dev/null &);
    a direct nohup & still gets reaped when the caller shell exits.
  - After a power-off, the old Connect.jar dies; port 22 may be open via Native
    SSHd before adbd (5555) re-registers. Re-run Connect.jar, then paramiko.
  - Key was still valid after reboot this time (dev-mode stayed enabled), but
    re-push via blackberry-connect anyway (it does auth + key transfer).
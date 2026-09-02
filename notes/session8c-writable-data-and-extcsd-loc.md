================================================================================
SESSION 8C - PROVING WRITE ACCESS TO THE LIVE eMMC DRIVER .data
================================================================================
2026-09-02, Classic (MSM8960), sacrificial unit. Follows 8b (read-only era).

GOAL: reach the MMC/SDCC controller to clear the temporary boot-partition
write-protect (B_PWR_WP_EN, ext_csd[0xad]=0x04) so a new boot image can be
flashed. Prior sessions assumed the driver memory was READ-ONLY and never
attempted a write. This session DISPROVED that and located the live ext_csd.

--------------------------------------------------------------------------------
KEY VERIFIED FINDINGS
--------------------------------------------------------------------------------
* **The driver's .data IS WRITABLE via /proc/<pid>/as.**
    Wrote a byte at a .data slot (0x10a18eec): 0x93 -> 0x5a, PERSISTED
    (read-back confirmed 0x5a), then restored to 0x93. Genuine R/W.
    This is the OPPOSITE of screen (pid 3596335), whose /proc/as writes were
    refused (0 records). So the eMMC driver is a real, writable injection host.
* **"Operation not permitted" flapping** earlier was a DEGRADED session artifact,
    NOT a real denial. A CLEAN QNX() connection (fresh paramiko transport) is
    fully functional (read AND write). Always reconnect fresh before diagnosing.

* **Live ext_csd copy located in .data at VA 0x10a1954f** (module-offset 0x1954f).
    Verified bytes (match the driver/ECSD read):
      [0xaa] BOOT_CONFIG_PROT = 0x00   (NOT fused -> temporary, clearable)
      [0xad] BOOT_WP          = 0x04   (B_PWR_WP_EN SET)
      [0xb3] BOOT_WP_STATUS   = 0x08
      [0x28] ERASE_GRP_SIZE = 1, [0x2a] WP_GRP_SIZE = 2, [0x2b] MULT = 3
      [0x5a] BOOT_SIZE_MULTI = 6
      [0xa8:0xb0] = 01 07 01 03 02 04 03 05
    (A nearby alias 0x10a520a8 matched [0xad]=0x04/[0xb3]=0x08 but has garbage
     REV/CARD_TYPE -- FALSE POSITIVE. The real copy is at 0x10a1954f.)

* **The WRITE_PROTECT (0xc0201a11) handler 0x10a0d664 is a CUSTOM block/group
  machine, NOT a clean mmc_switch gate.** It builds 0x2c8-stride / 0x58-stride
  descriptors and enqueues to background threads; it reads ext_csd bytes
  [0xa0],[0xa2],[0xa8],[0xe2] (power/boot-state) -- NOT the classic
  nlba % (ERASE_GRP*WP_GRP*512K) gate. => patching ext_csd seed values does NOT
  reliably reach CMD6. The only clean way to run mmc_switch(173,0) is to CALL it.

* **No clean static FP to redirect.** The devctl path:
     io_devctl -> 0x10a0c5d0 (io_msg wrapper) -> 0x10a0c4e4 (card dispatcher)
               -> 0x10a0f7f0 (generic block op)
  and the dcmd-specific handlers 0x10a0d492 (CARD_REGISTER) / 0x10a0d664 (WP).
  The resmgr io_devctl FUNCTION POINTER lives in a HEAP dispatch_t (built by
  dispatch_create) -- NOT a static .data slot. The module's own .data FP tables
  (e.g. 13-ptr @ 0x10a18ecc) point MID-FUNCTION (exception/setjmp-style slots)
  => unsafe to hijack blindly.

* **Card/context identity (confirmed multiple paths):**
    ext = [ctp+8]        (per-devctl context)
    card = [ext+0x10]    (same object mmc_switch calls "hba")
    ext_csd = [card+0x2c] + 0x178      (helper 0x10a074ae)
    mmc_switch @ 0x10a056c0 (Thumb): mmc_switch(hba,cmds=1,arg?...,index,mode..)
        r0=hba, r1=flgs, r2=cmdset, r3=index, [sp+0x20]=value, [sp+0x24]=arg
        -> bl 0x10a053b0 (lock); bl 0x10a06240 (CMD6 send); bl 0x10a053b0 (unlock)

--------------------------------------------------------------------------------
STATE / BLOCKER
--------------------------------------------------------------------------------
* Driver fully healthy; only a test write (restored) was ever made; ext_csd
  untouched. BOOT_WP still 0x04.
* To issue mmc_switch(173,0) we need EXECUTION context. .data is writable so a
  Thumb thunk CAN live there, but we have not yet found a SAFE, deterministic
  redirect that fires on a controlled trigger (resmgr FP is heap; .data FP
  tables are mid-function/unsafe).

--------------------------------------------------------------------------------
NEXT LEVERS (in ascending risk)
--------------------------------------------------------------------------------
A) Call mmc_switch from a signed helper / higher-ability context (no live write;
   requires a carrier with an ability grant -- the original screen idea, but that
   needs a WRITE host we still lack).
B) Find the resmgr dispatch_t at RUNTIME: read the heap to locate dispatch_create
   output, then redirect its io_devctl slot to a .data thunk. More RE + a heap
   address (volatile across exec, but resolvable per-session).
C) Hijack ONE devctl-reached indirect call that uses a static .data FP table,
   gated by a marker so unrelated calls pass through -- highest risk, needs a
   careful single-slot candidate.

ARTIFACTS:
  notes/session8b-wpgrp-patch.md (prior read-only era)
  /tmp/opencode/kgsl/{code_live.bin, ro.bin, data3.bin, fulldata.bin, p.bin,
    ec.bin, verif.bin, back.bin}
================================================================================
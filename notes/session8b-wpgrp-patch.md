================================================================================
SESSION 8B - TARGETING THE WP_GRP GATE IN THE LIVE eMMC DRIVER
================================================================================
2026-09-02, Classic (MSM8960), sacrificial unit. Follow-up to 8a & 7q.

GOAL (user-selected): neutralise the nlba % wp_grp_size gate so the existing
WRITE_PROTECT SET devctl reaches the driver's own mmc_switch(EXT_CSD_BOOT_WP=173,
mode=0) and clears the temporary boot-partition write-protect (B_PWR_WP_EN).

--------------------------------------------------------------------------------
NOTABLE REROUGHING OF PRIOR ASSUMPTIONS
--------------------------------------------------------------------------------
* The sdmmc driver module's TRUE load base is 0x10a00000 (not 0x109fe000).
  pidin's "@109fe000" is a rounded segment start; verified live instruction
  decode is consistent only with 0x10a00000 (mmc_switch @ 0x10a056c0).
* The driver code is **Thumb-2**, not ARM as assumed in 8a. mmc_switch @
  0x10a056c0:
      10a056c0 push.w {r0,r1,r4-r8,lr}
      10a056c4 mov r6,r1            ; flgs
      10a056c6 movs r1,#1
      10a056c8 mov r5,r2            ; cmdset
      10a056cc mov r4,r0            ; hba
      10a056ce mov r8,r3            ; index
      10a056d0 bl 0x10a053b0        ; lock
      10a056d8 ldr r3,[sp,#0x20]    ; value
      10a056de ldr r3,[sp,#0x24]    ; arg
      10a056e4 ldr r0,[r4,#0x2c]    ; host->card?
      10a056e8 bl 0x10a06240        ; send CMD6 SWITCH
      10a056f4 mov r0,r4
      10a056f6 bl 0x10a053b0        ; unlock
* DCMD_MMCSD_WRITE_PROTECT literal = 0xc0201a11 sits at **file offset 0xd65c,
  VA 0x10a0d65c** (early guess 0x10a0b65c was a stale-base error).

--------------------------------------------------------------------------------
CURRENT LIVE BOOT0 WP STATE (re-confirmed this session, /dev/emmc/boot0)
--------------------------------------------------------------------------------
Via DCMD_MMCSD_CARD_REGISTER (0xc0181a14) struct MMCSD_CARD_REGISTER:
  action=READ(0), type=EXT_CSD(2), address=0, length=512, then data[512] AFTER
  the 24-byte header. (Earlier reads failed because data lives at buf+24.)
  Current read (512 bytes):
    data[0x00]         = 0x00
    data[0xa2]         = 0x02
    data[0xa8:0xb0]    = 04 01 00 d0 00 04 0a 01
  => BOOT_WP(0xad)=0x04 (B_PWR_WP_EN set), BOOT_CONFIG_PROT(0xaa)=0x00 (NOT
     fused), BOOT_WP_STATUS(0xb3)=0x08.
  => STILL temporary, clearable. Confirms 7q.

--------------------------------------------------------------------------------
KEY NEW FINDINGS (devctl handler geometry)
--------------------------------------------------------------------------------
* devctl status/register handler at 0x10a0a610 reads ext_csd via helper
  **0x10a074ae** = { ldr r0,[r0,#0x2c]; add r0,#0x178 } -> returns the LIVE
  ext_csd buffer address given `card` in r0 (card comes from `[ext,#0x10]`
  where ext=[ctp,#8]).
  Handlers:
    0x10a0d5f2 ... bl 0x10a074ae; copies CID
    0x10a0d60e ... bl 0x10a074ae; ldrb [r0,#0xb5]  (BOOT_WP_STATUS)
    0x10a0d620 ... bl 0x10a074ae; ldrb [r0,#0xa8]  (ext_csd[0xa8])
* resmgr devctl dispatch table (literal pool) @ **0x10a0b680**:
    0x10a0b684 = 0x0000fa5a   -> fn 0x10a0fa5a
    0x10a0b688 = 0x00000260   -> fn 0x10a00260
    0x10a0b68c = 0x0000a454   -> fn 0x10a0a454
    0x10a0b690 = 0x0000a60e   -> fn 0x10a0a60e
    0x10a0b694 = 0x0000a402   -> fn 0x10a0a402

--------------------------------------------------------------------------------
ATTEMPTS & RESULTS
--------------------------------------------------------------------------------
* CARD_REGISTER action=WRITE (action 1 / 0x11 / 2) -> devctl ret 48 (0x30,
  ENOTSUP). The driver does NOT implement a write action for CARD_REGISTER.
  Only READ works. => cannot clear BOOT_WP via register-write devctl.
* Dumped big heap windows and searched for the ext_csd fingerprint
  "04 01 00 d0 00 04 0a 01" (bytes at ext_csd[0xa8:0xb0]):
     0x10a20000..0x10c20000 (heap8)  0
     0x10a4e000..0x10a51000 (heapA)  0
     0x10c20000..0x10f60000 (heapB)  0
     0x10f60000..0x11220000 (heapC)  0
     code_live / data2_live           0
  => The authoritative live ext_csd copy is NOT in any dumped window.
* Relocated dense heap objects mutate across reads (0x10a4b9f0 changed between
  two reads: +0x28 0x20000000 vs 0x10a4f4e0) -> these are ACTIVE/transient DMA
  or io-blk ("blk-" 0x2d6b6c62) structures, not a stable card anchor.
* No literals/code loaded the dispatch-table dcmd in a way that yields the ext
  global address cheaply; live memory is too volatile for a blind write.

--------------------------------------------------------------------------------
CURRENT STATUS / BLOCKER
--------------------------------------------------------------------------------
* State: fully verified READ-ONLY; driver healthy and responsive throughout;
  no write was made. ext_csd[0xad]=0x04, BOOT_CONFIG_PROT=0x00 (temporary WP).
  All cleanup done; /proc/as reads only.
* Blocked on: locating a STABLE, exec-invariant address for the live mmc card /
  ext_csd (or ext global) so wp-grp raw[0x28]/[0x2a] (or the nlba%wp_grp result)
  can be patched WITHOUT guessing into volatile heap. Driver re-EXECs change
  heap layout; only link-time .data/.bss offsets (module-base-relative) survive.

--------------------------------------------------------------------------------
RECOMMENDED NEXT (most robust)
--------------------------------------------------------------------------------
Trace `ext` (=[ctp,#8]) back to a **link-time .bss/.data global** (module-base
relative) and use its VA = 0x10a00000 + fixed_offset for /proc/as writes. That
offset is identical every exec -> only remaining step is the single patch:
  - either force the nlba%wp_grp check to pass (patch wp-grp fields or the
    comparison), then send WRITE_PROTECT SET mode=0 to clear ext_csd[173]=0;
  - or, once ext is known, write the wp-grp seed values directly.
Fallback if ext-trace stays elusive: dump the ONE region the ecs3 READ returns
and note that the driver's card pointer chain is reachable from the resmgr
context; do a single guided read, not a blind write.

ARTIFACTS:
  code_live.bin (0x10a00000..0x10a64000), heap8/A/B/C/D.bin, extcsd_full.bin
  /tmp/opencode/pp/{cid,ecs2,ecs3,wr}.py + ecs2.out
  qnx-mmcsd-headers/dcmd_sim_mmcsd.h (MMCSD_CARD_REGISTER layout, line ~230)
================================================================================
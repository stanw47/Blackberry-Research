# Session 8e — r2 convergence: native WP devctl is a confirmed dead end

## Tooling
- radare2 5.9.8 installed on Parrot (works headless, no root). r2pipe python not
  installed (pip blocked) -> use CLI batch mode:
  `r2 -q -e asm.arch=arm -e asm.bits=32 -e asm.thumb=true -B 0x10a00000 -c "<cmds>" sdmmc.elf`
- `/tmp/opencode/kgsl/sdmmc.elf` is byte-identical to live driver code (verified).

## r2-verified io_devctl dispatcher (0x10a0d574)
dcmd table (r3=[r1,#0x24]) handler tail-calls:
  0x42001a75(DEVINFO) -> 0x10a0ccc8
  0x40011a46(extcsd byte 0xa8) -> 0x10a0d620
  0x40101a44(CID)      -> 0x10a0d5f2
  0x41081a74           -> 0x10a0ca60
  0xc0181a14(CARD_REGISTER) -> 0x10a0d492
  0xc0081a42           -> 0x10a0d410
  0xc0201a11(WRITE_PROTECT)  -> 0x10a0fcec   <- REAL WP handler (corrected)
  0xc0201a13(WRITE_PROTECT+2) -> 0x10a0fdb4   <- ERASE/group

## Corrected WRITE_PROTECT handler = 0x10a0fcec
- Builds part entry: r6 = dev_obj + target*0x2c8 + lun*0x58 + 0x1d0.
- Input MMCSD_WRITE_PROTECT at r5=[r1,#0x30]:
    action [r5+0], mode [r5+4], lba [r5+8]:u64, nlba [r5+0x10]:u64, rsvd2 [r5+0x18]
- Worker 0x10a0f48c:
    - sl=r1 (the "part-type/mode" arg)
    - gate: cmp.w sl,#0x1c ; bne -> SCAN path (never-switch)
      => need sl==0x1c (28) to reach the mmc_switch branch
    - then r5&7==0 -> USER_WP mmc_switch(hba,1,3,0xab, val)
          r5==2   -> BOOT_WP mmc_switch(sb,1,3,0xad, val)  [val=r7=input.mode]
- availability gate (0x10a0e53a): returns non-1 for boot partitions -> sets
  handler to return 5 (EIO) BEFORE unit dispatch. Reads flag [r6+0x1d0+0x1f8]
  = [part-entry+0x1f8]; zero for boot partitions.

## Prior empirical facts that still hold (7p/7q/7s) and now all coherent
- WRITE_PROTECT on boot0/boot1 CLR -> ret=5 EIO (both instances), twice.
- sim_mmc.c mmc_wp(): EINVAL if slba>pend or (slba+nlba-1)>pend or nlba % wp_grp_size.
   wp_grp ~3.2G (HC_WP_GRP=raw[168]=0x20 * ERASE_GRP=raw[171]=0xd0 * 512K) > boot0 4MB
   => ANY nlba for boot fails nlba % wp_grp_size -> EINVAL before mmc_switch.
- VUC_CMD (0xC0441A16) not in dispatch table -> ENOTTY (raw CMD6 passthrough absent).
- partition availability flag is on the *heap* (sim_alloc_hba import -> heap), not
  stable `.data/.bss` -> cannot be patched at a fixed /proc/as address.

## CONCLUSION (Route A = native devctl = confirmed dead end)
The stock driver's DCMD_MMCSD_WRITE_PROTECT can NOT clear boot-partition WP from a
user-space client:
  1. any nlba fails nlba % wp_grp_size  (EINVAL) before reaching CMD6,
  2. even if that passed, the heap availability flag returns EIO for boot parts,
  3. no raw-CMD6 (VUC) exists to bypass.
Only direct in-driver invocation of mmc_switch(hba,1,3,0xad,0) can clear B_PWR_WP_EN.

## Route B (in-driver CMD6) - updated targeting with r2
- mmc_switch   = 0x10a076c0  (lock 0x73b0, CMD6-send 0x8240, unlock 0x73b0)
- Needed call: mmc_switch(hba, r1=1, r2=3, r3=0xad, value=0)  (value at [sp])
- hba = the card/controller struct (heap). Reachable from a devctl in-driver
  (the WRITE_PROTECT handler already has r0=hba in-context). So the cleanest
  injection is: redirect the WP devctl dispatch to a Thumb thunk that calls
  mmc_switch(r0(hba),1,3,0xad,0), using the dispatcher's own r0.
- Dispatch is a tail-call `b.w 0x10a0fcec` from 0x10a0d574 -> repoint that
  immediate to a writable+executable thunk, OR repoint a `.data` code pointer.
  The `.text` writability via /proc/<pid>/as must be tested first.
- next: test .text writability of pid 741404 at the dispatcher's `b.w` slot.

## Next
1. Reserve a Thumb thunk in driver memory; test if `.text` (0x10a0dxxx) is writable
   via /proc/741404/as (write/replace the `b.w 0x10a0fcec` immediate in a scratch
   test, verify persists, restore).
2. If `.text` RW: build thunk that does mmc_switch(hba,1,3,0xad,0) and repoint the
   WP tail-call to it; trigger via an otherwise-harmless WRITE_PROTECT devctl.
3. Verify live ext_csd[0xad]@0x10a1954f goes 0x04 -> 0x00, then write boot0.
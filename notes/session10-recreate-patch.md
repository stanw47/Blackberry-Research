# Session 10 — Can we re-create Oleksandr's raw-MMC patch ourselves? 2026-09-03

## Question
User cannot obtain Oleksandr's Patreon `sdmmc.zip`/patch. Can we re-create the
raw-MMC/CMD6 capability ourselves so we can clear boot0 `B_PWR_WP_EN`
(ext_csd[0xAD]) and unlock the Classic?

## Live-device state (2026-09-03, via adb-over-TCP)
- Working channel stays adb: `adb connect 169.254.0.1:5555`.
- `g_Disk_Drivers` (setgid 132): euid=850 egid=132.
    - CAN open `/dev/emmc/boot0` O_RDWR, issue devctls (MY probes returned real
      EIO=5 on WRITE_PROTECT and ENOTTY=25 on VUC_CMD => genuine silicon/driver).
    - CANNOT open `/proc/<pid>/as` (Operation not permitted) => NO memory patch.
- `__root` (setuid 800, NOT 0): cannot even exec python now (pathtrust
  "Operation not permitted") => NOT granting root in this adb session.
- => TRUE root (uid 0 + pathtrust -> /proc/as write) is CURRENTLY UNAVAILABLE.
  It only existed via the SSH/blackberry-connect ritual (btool pathtrust grant),
  which broke after reboot. This is the same root cause that broke SSH.

## Confirmed stock-driver dispatch map (Classic devb-sdmmc-rim-msmsdcc)
Dispatcher at 0x10a0d574 (base PIE 0x10a00000), range-compare chain on devctl
code r3 against constant table @0x10a0d644 (all LE). Handled codes:
  | code        | cmd                                  |
  | 0x42001a75  | DCMD (new-style CAM)                 |
  | 0x40011a46  |                                      |
  | 0x40101a44  |                                      |
  | 0x41081a74  |                                      |
  | 0xc0181a14  | DCMD_MMCSD_CARD_REGISTER             |
  | 0xc0081a42  |                                      |
  | 0xc0201a11  | DCMD_MMCSD_WRITE_PROTECT             |
  | (0x... +2)  | adjacent paired command (0x... +2)   |
  default(no match at 0x10a0d63a): r3=[0x10a0d660]=0x80000001 -> err  -> ENOTTY
- NOTE: DCMD_MMCSD_VUC_CMD = 0xC0441A16 is ABSENT => this is exactly the gap
  Oleksandr's raw-cmd handler fills (matches my live ENOTTY=25 on CMD13).
- WRITE_PROTECT handler @0x10a0ccc8 reaches live ext_csd/switch internals; it
  reads ext_csd[0xa8] and [0xb5] (0x10a0d61a/0x10a0d62c) => live EXT_CSD is in
  driver .data (confirms 8c finding @0x10a1954f region).
- Internal mmc_switch target located (8c): 0x10a056c0.

## Can we re-create? (honest assessment)
Three routes, all blocked by missing TRUE ROOT in current session:
1. In-memory patch of running driver dispatch/`,data`: turn an existing slot or
   WRITE_PROTECT into a raw-CMD6/CLEAR_WP that calls internal mmc_switch(0xAD,0).
   RE blueprint complete. BLOCKED: needs /proc/<pid>/as write = /proc/as open +
   pathtrust. Have neither (uid 850 only).
2. Swap/recompile a patched devb-sdmmc driver: have genuine binary + mmc_switch
   addr. BLOCKED twice: driver lives in read-only IFS/eMMC we are trying to
   unlock (chicken-egg); needs signed BB10 NDK toolchain.
3. Standalone stub calling raw silicon: driver won't expose raw cmd (ENOTTY) and
   we lack uid0 to map controller MMIO/VUs. BLOCKED the same way.

=> Re-creating Oleksandr's patch IS technically feasible (route 1 blueprint done)
   but the linchpin is TRUE ROOT, which is currently lost. Must first restore the
   pathtrust grant (SSH ritual / dev-mode / blackberry-connect / btool). Without
   /proc/as write, any in-memory re-creation is impossible.

## Next decision needed from user
Restore true root (pathtrust) to enable route 1. Trade-offs: re-run the connect
ritual, dev-mode toggle, possibly reboot. Ask user how to proceed.
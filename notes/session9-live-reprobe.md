# Session 9 — Live re-probe 2026-09-03: stock driver WP/raw-CMD state (Classic)

## Connection
- SSH re-push/reconnect FAILED (auth timeout) even after blackberry-connect key
  push + dev-mode re-enable + toggle. Root cause not host-side: device sshd not
  completing ANY auth (key or password) after reboot.
- **WORKING route found: adb over TCP.** `adb connect 169.254.0.1:5555` (BB10
  adbd) gives a shell with NO key/auth requirement. This is the reliable access
  channel; SSH is unneeded.

## Root/eMMC access (working, no SSH)
- Device is rooted; group-wrapper rootkit intact:
  - `/base/bin/__root` (setuid root, spawns root ksh when pathtrust-whitelisted)
  - `/base/bin/g_Disk_Drivers` (setgid 132 = Disk_Drivers)
  - `/base/bin/g_nto`
- Raw eMMC + devctl via `g_Disk_Drivers -> berrycore python3.11 -> ctypes devctl`:
  `echo 'export PYTHONHOME=...; exec .../python3.11 /path/py' | /base/bin/g_Disk_Drivers`
  Python path: `/accounts/1000/shared/misc/berrycore/lib/python3_ntoarmv7-qnx-static/tools/python3/python3.11`

## Live probe results (all on /dev/emmc/boot0)
| devctl | dcmd | result | meaning |
|--------|------|--------|---------|
| CARD_REGISTER read ext_csd | 0xC0181A14 | devctl_r=0 but all bytes 0x00 | card-register read path returned zeros (artifact); not used for WP verdict |
| WRITE_PROTECT | 0xC0201A11 | CLR/SET pwr on boot0 -> **5 (EIO)**; nlba=0xFFFF -> 22 (EINVAL) | stock WP devctl CANNOT clear boot-partition WP |
| VUC_CMD (raw MMC passthrough) | 0xC0441A16 | CMD13 -> **25 (ENOTTY)** | stock driver does NOT implement raw-MMC cmd |

## Conclusion (empirically confirmed)
- Stock `sdmmc-rim-msmsdcc` driver (both instances) has NO raw-MMC command path
  (VUC_CMD = ENOTTY). This is the exact primitive needed to issue CMD6 SWITCH
  (clear ext_csd[0xAD] B_PWR_WP_EN) to make boot0 writable.
- Stock WRITE_PROTECT devctl is a confirmed dead end for boot partitions (EIO).
- => Oleksandr's `sdmmc_raw_cmd` patch (raw CMD0-255 + CLEAR_WP + MMC_INIT_DEVICE)
  is EXACTLY the missing software primitive to clear B_PWR_WP_EN on the Classic.
  No other software route exists (native devctl dead, no VUC, /proc/as root not
  currently usable over adb).

## Notes / caveats
- `__root` via adb shell currently reports "Operation not permitted" on
  /proc/<pid>/as (pathtrust whitelist not fully active in adb context). So the
  Route-B in-driver memory-patch approach is NOT live-testable over adb right
  now; would need SSH root or re-applying the btool pathtrust whitelist.
- Adb TCP is the dependable channel going forward (no key/reboot re-push needed).

## Artifacts
- Local: /home/stanw47/Documents/blackberry-research/{probe_extcsd,probe_wp,probe_vuc}.py
- On device: /accounts/1000/shared/misc/berrycore/{probe_extcsd,probe_wp,probe_vuc}.py
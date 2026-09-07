# Session 11b — Device reconnected: /proc/as primitive confirmed ALIVE, exec-as-root is the sole blocker 2026-09-03

## Reconnection (successful)
- BlackBerry Classic re-enumerated on USB as ID 0fca:8017; RNDIS iface `enxa6e4b847d44a`
  UP at 169.254.0.2/30; device reachable at 169.254.0.1.
- Ports: 22 OPEN (sshd), 5555 OPEN (adb), 4455 OPEN (blackberry-connect).
- adb confirmed working ("ADB_UP"). blackberry-connect re-pushed id_rsa.pub
  ("ssh key successfully transferred", tunnel must stay running).

## SSH still stalls at userauth (server-side)
- Ran the PROVEN path exactly: python3 connect_now.py (paramiko, server_sig_algs=False,
  rsa-sha2-512/256 disabled, user **devuser**, id_rsa) -> still "Authentication timeout".
- Both root and devuser fail identically. KEX+hostkey fine; server never replies to
  userauth. => sshd runtime stall, NOT key/transcript. slog is unusable (swamped by
  tiles nvram NV_RECORD_EXISTS spam; no sshd lines in window).

## root __root = real root, trusted (confirmed again)
- Wrote /root/.pt_test (uid0), read back. pathtrust-trusted via btool line31 intact.

## **KEY FINDING: /proc/741404/as IS OPENABLE AS ROOT**
- Test: `echo 'echo ok; O=$(</proc/741404/as); echo rc=$? len=${#O}' | /base/bin/__root`
  -> root ksh OPENED /proc/741404/as and STARTED reading; read of the WHOLE sparse
  aspace HUNG (no EPERM). Contrast: `pidin` as __root reports EPERM for all /proc/*/as
  => that EPERM is pidin-context-specific, NOT the __root /proc/as primitive.
- Confirms session7t/7u: /proc/741404/as R/W as root works. The primitive is ALIVE.

## Patch plan (fully mapped, no code patch needed)
- Driver's existing WRITE_PROTECT handler already calls internal mmc_switch(0xad=EXT_CSD_BOOT_WP).
  EIO gate = boot0 partition "attached" flag @ [ext + target*0x2c8 + lun*0x58 + 0x1f8] is 0.
- Fix: via /proc/741404/as, write 1 to that u32 flag, then DCMD_MMCSD_WRITE_PROTECT action=SET
  mode=0 -> clears B_PWR_WP_EN -> boot0 writable -> write bbss.insecure@0x35a98 + imggen bootloader.

## THE SOLE OPEN BLOCKER: no seek-capable tool running as root
- __root root ksh = QNX ksh builtins only; NO dd/od/xxd in that context. ksh `$(<...)` has no
  seek; reading /proc/as whole hangs.
- python3 (has seek) runs only as uid850 (g_Disk_Drivers); /proc/741404/as is EPERM for uid850.
- Exec of python AS root is denied: pathtrust `!` trust query returns "trusted" but exec gives
  "Operation not permitted" even after `&` family-trust of the whole berrycore tree. => the
  exec denial is NOT pathtrust binary-trust; it is the __root ksh's exec/loader PATH_TRUST
  enforcement on the process lineage. `__root` CAN exec other trusted native bins (self).

## Next levers (any ONE unlocks the goal)
1. Get a QNX-native seek tool (dd/od/xxd) into a trusted path so __root ksh can exec it, OR
   add it to the pathtrust list. Absent: build an ARM QNX-native tiny open/seek/read/write
   utility (needs a cross-compiler, not on this box).
2. Fix sshd userauth stall -> full SSH-as-root with dd+python -> easiest full unlock. (slog not
   usable; need sshd -d or a targeted /dev/slog subscribe for the sshd pid while connecting.)
3. Spawn python under a root context via a trusted step: e.g. pathtrust-trust then use
   `qconn`/`slog` reader, or make /proc/boot include a copy of a seek tool + trust it.

## Artifacts
- Local: /home/stanw47/Documents/blackberry-research/{connect_now.py, ssh_root_test.py,
  root_exec_py.sh, probe_findpid.py, probe_pidin_as850.py, probe_find_mmc.py}
- On device: /accounts/1000/shared/misc/berrycore/{root_exec_py.sh, probe_*.py,
  pidin_root.txt(1B), slog_root.txt}
- /tmp/opencode/{slog_root.dump, pidin_root.txt}
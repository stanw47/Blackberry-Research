# Session 11c — Root dd/cat WORKS; /proc/as ability-gated; boot0 HW-WP confirmed EROFS 2026-09-03/04

## Re-connected state after several hours + replug
- Device re-enumerated (USB 0fca:8017), RNDIS enxa6e4b847d44a @169.254.0.2/30, pings.
- ports 22/4455/5555 OPEN. adb works. blackberry-connect re-pushed id_rsa.pub (tunnel up).

## TOOLS DISCOVERED: QNX-native root dd + cat work via __root
- /base/bin/dd and /base/bin/cat exec AS ROOT through __root ksh.
  (/base/bin/dd missing from /usr/bin; /usr/bin has no dd/od/cat, uses cut/tail/etc.)
- dd needs DECIMAL skip/seek (no 0x hex). Reads/writes files in root's namespace.
- /base is read-only (pfs): cannot drop files into trusted root fs.

## DEVICE NODE MAP (live)
- devuser (g_Disk_Drivers, uid850) block devices live under /dev/emmc/*:
  boot0,boot1,os0,os1,uda0,user0,dmi0,nvram0,cal_work0,rpmb0,sd0,radio0.
  - python devuser opening /dev/emmc/boot0 -> EPERM (owner 800:132, devuser not in ACL).
  - /dev/emmc itself = DIRECTORY (mode 0o40000) in both namespaces.
  - /dev/boot0 /dev/hd* /dev/eMMC do NOT exist (wrong names).
- root __root namespace: /dev/emmc (dir); root dd READS /dev/emmc/boot0 (16 bytes -> zeros).
  root dd WRITE to /dev/emmc/boot0 -> "Read-only file system" + "Input/output error".
  => HARDWARE B_PWR_WP_EN at eMMC controller; uid-0 does NOT bypass. Confirms session7q.

## FIND CURRENT DRIVER PID (it changed after replug)
- old sdmmc pid 741404 is GONE. driver is /proc/boot/devb-sdmmc-rim-msmsdcc, now pid 2330666
  (cmdline read via root cat: "/proc/boot/devb-sdmmc-rim-msmsdcc blkcache=10M,commit=none,...").

## /proc/<pid>/as IS HARD ABILITY-GATED (the wall)
- root dd/cat reading /proc/2330666/as AND even /proc/253961/as (unprivileged ksh)
  -> "Operation not permitted" for BOTH.
- => root __root does NOT hold PROCMGR_AID_MEM_PHYS effectively. asroot_main.c *requests*
  MEM_PHYS via PROCMGR_ADN_NONROOT | ... | PROCMGR_AOP_ALLOW | SUBRANGE, but under ADN_NONROOT
  it does NOT apply to the now-root __root process => /proc/as stays EPERM.
- /proc/<pid>/cmdline IS readable as root (so /proc root access partially works; only /as gated).

## THE GOAL: boot0 write needs B_PWR_WP_EN cleared, and clearing needs raw CMD6/mmc_switch
- Driver's own WRITE_PROTECT does mmc_switch(0xad) but EIO-gated by boot0 attach flag.
- Stock driver has NO raw-CMD path (DCMD_MMCSD_VUC_CMD = ENOTTY) => need in-memory patch via
  /proc/<pid>/as (requires MEM_PHYS) OR re-created Oleksandr driver patch (same /proc/as).
- boot0 is emptied/zeroed head and hardware EROFS now; must clear HW WP first.

## DECISION POINT (recommendation)
- EITHER restore the ability-rich interactive shell (the SSH-as-root path that historically held
  /proc/as + MEM_PHYS) by fixing the sshd userauth stall — the highest-value single unlock; OR
- get an ARM QNX cross-compiler to build a native tool that opens /proc/<pid>/as itself after
  __root grants MEM_PHYS (escape the ADN_NONROOT scoping by spawning via procmgr with proper
  signature) ; OR
- obtain Oleksandr's sdmmc.zip raw-CMD driver (the original private patch) to drop in.

## Artifacts (local / on-device)
- Local: /home/stanw47/Documents/blackberry-research/{probe_bootdev.py, probe_devlist.py,
  probe_hd.py, probe_emmc_dir.py, probe_emmc_boot0.py, root_exec_py.sh}
- On device /accounts/1000/shared/misc/berrycore/: same + h.bin(absent) + slog_root.txt
- Notes: session11b + this file.
# Session 11d — sshd restored + root; definitive /proc/as ability regression diagnosis 2026-09-03/04

## Device left HEALTHY
- adb UP; sshd daemonized running (port 22 OPEN); blackberry-connect tunnel (4455) OPEN.
- Root dd/cat work via __root. g_Disk_Drivers (egid132) opens /dev/emmc/* + devctl channel intact.
- Scratch probes + debug logs cleaned from /accounts/1000/shared/misc/berrycore/.

## SSH-as-root diagnosis (exhaustive, server-side hang)
- Restarted sshd cleanly:  /base/usr/sbin/sshd -f /etc/ssh/sshd_config (daemonizes OK; the earlier
  `&`-background from __root ksh killed orphans -> do NOT use `&`; run directly so it daemonizes).
- Full paramiko verbose: banner OK (SSH-2.0-paramiko), KEX ecdh-sha2-nistp256, hostkey ssh-rsa
  accepted, cipher aes128-ctr, client sends pubkey userauth ("userauth is OK")... then SERVER NEVER
  REPLIES -> "Authentication timeout." Same for root and devuser.
- sshd debug (-d -e) shows it binds + accepts ("Connection from 169.254.0.2") but then either
  "Bad protocol version identification ''" (when client socket closed) or silently stalls at
  userauth. Non-debug sshd logs nothing to slog (slog swamped by jauthman/bbm/nvram; no sshd lines).
- => sshd's userauth handler hangs server-side on this QNX build; NOT key/transport/client.
  Root key 'stanw47@parrot' + 'lc@t560' both present in /etc/ssh/authorized_keys2; AllowUsers=root;
  PermitRootLogin=yes; PasswordAuthentication=no. Config correct.

## DEFINITIVE: /proc/<pid>/as is ability-gated and NOT held on this boot
- Tested open('/proc/<pid>/as') under EVERY available context, see pids 2330666(sdmmc) + 253961(ksh):
  * root dd via __root            -> "Operation not permitted"
  * root cat via __root           -> perms on /proc/<pid>/cmdline OK, /as EPERM
  * python (uid850) as g_Disk_Drivers (egid132, non-root ADN_NONROOT) -> EPERM
- /proc/<pid>/cmdline IS readable as root (root access to /proc works); ONLY /as is gated.
- Root __root / g_Disk_Drivers request PROCMGR_AID_MEM_PHYS but the grant does NOT yield /as.
- Regression: sessions 7t/7u/8a documented /proc/741404/as R/W working (wrote deadbeef to .data).
  On THIS boot (post reflash/replug, sdmmc pid 741404->2330666) /proc/as is EPERM for all.
- Conclusion: the sole blocker to the in-driver mmc_switch(0xad,0) patch (Route B, session8e) is the
  /proc/<pid>/as ability, which the current boot does not grant where earlier boots did.

## Tool/mount map (live, re-confirmed)
- devuser block devs: /dev/emmc/{boot0,boot1,os*,uda0,user0,dmi0,nvram0,cal_work0,rpmb0,sd0,radio0}
  owned 800:132 (root:Disk_Drivers). g_Disk_Drivers(egid132) opens them; plain uid850 EPERM.
- root __root namespace: /dev/emmc (dir); root dd reads /dev/emmc/boot0 (zeros); WRITE -> EROFS/EIO
  => hardware B_PWR_WP_EN; uid0 does NOT bypass. Confirms session7q/8e.
- sdmmc binary /proc/boot/devb-sdmmc-rim-msmsdcc, pid 2330666 (was 741404).

## Cast of remaining paths for B_PWR_WP_EN (the actual goal)
1. Regain /proc/<pid>/as on boot0 attach flag / thunk patch — blocked by ability regression (this is
   the crux; earlier sessions had it).
2. Drive the driver's existing mmc_switch(0xad) — unreachable via normal WRITE_PROTECT actions
   (sl==0x1c gate; session8a/e). Native devctl = confirmed dead end (session8e).
3. Oleksandr's sdmmc.zip raw-CMD driver patch — per user, must self-recreate (routes to #1).

## Recommended next
- Focus on WHY /proc/as ability is now absent vs sessions 7-8: re-provision __root's pathtrust +
  ability grant on a clean interactive run; or compare OS slot (dev-mode/switchzone) since
  .rootfs.os.version changed. OR build an ARM QNX-native opener with explicit
  PROCMGR_AID_MEM_PHYS after __root, escaping ADN_NONROOT scoping.

## Artifacts
- /tmp/opencode/{ssh_clean.py, sshd_srvd.log, sshd_dbg.log, slog_auth.dump, pidlist.txt}
- notes/session11b, 11c, this file (11d).
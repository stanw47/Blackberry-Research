================================================================================
SESSION 7F - BIDE SNAPSHOT MECHANISM + PATHTRUST ENFORCEMENT (full map) - 2026-08-29
================================================================================

[1] BIDE SNAPSHOT MECHANISM (bide_ctl.c) - the "blind window"
  - ctx.taken is atomic_t, starts 0. ctl_snapshot_complete() = atomic_read(taken).
  - Snapshot is taken ONCE by the JBIDE process via BIDE_IOCTL_TAKE_SNAPSHOT
    (only if !snapshot_complete). ctl_snapshot_initialize():
      tz_init_kernel() -> tz_gen_keypair/set_keypair -> ctl_initialize_nonce
      -> vma_scan_task(current) [baseline of JBIDE memory] -> atomic_inc(taken)
      -> caps_clean_list(0) -> vma_scan_processes() [full scan].
  - ALL sensors (capset/mount/mprotect/bprm-root/report) are gated on
    ctl_snapshot_complete(): before the snapshot they return early = BLIND.
  - No ioctl resets 'taken'; it's monotonic. BUT if tz_init_kernel() fails,
    ctl_snapshot_initialize returns BEFORE atomic_inc -> 'taken' stays 0 FOREVER
    -> BIDE permanently blind. (Not attacker-controllable from unprivileged.)
  - => The blind window is boot-time only (until DTEK/JBIDE initializes). Not a
     practical unprivileged window, but worth knowing for the threat model.

[2] PATHTRUST = A SECOND *ENFORCEMENT* LSM (unlike BIDE's audit-only)
  - security/pathtrust/ registers 6 LSM hooks that can return -EPERM (BLOCK):
      sb_mount / sb_kern_mount  -> pathtrust_sb_mount/sb_kern_mount
      bprm_set_creds            -> pathtrust_bprm_set_creds  (exec)
      mmap_file                 -> pathtrust_mmap_file        (mmap PROT_EXEC)
      kernel_fw_from_file       -> pathtrust_kernel_fw_from_file (firmware)
      kernel_module_from_file   -> pathtrust_kernel_module_from_file (modules)
  - pathtrust_enforce toggles audit vs enforce. Config BOOTPARAM_VALUE=1 ->
    boots ENFORCED (blocking), unless bootparam overrides.
  - Independent of SELinux: even after setenforce(0), Pathtrust still enforces.

[3] TRUSTED FILESYSTEMS (the enforcement basis)
  - A mount is MNT_TRUSTED iff mounted with MS_TRUSTED flag AND the block device
    is in the pathtrust dev whitelist (pathtrust_dev_trusted).
  - CRITICAL: drivers/md/dm-verity.c:979 calls pathtrust_add_dev(bdev->bd_dev)
    when a dm-verity target is set up -> /system and /oem (dm-verity) are
    AUTOMATICALLY trusted. /data is NOT (no dm-verity) -> NOT trusted.
  - Plus init/fstab-added devices and the path whitelist (dalvik-cache .oat/.dex
    from CONFIG_SECURITY_PATHTRUST_PATHNAMES).

[4] WHO IS SUBJECT TO ENFORCEMENT
  - is_root(cred): euid==0 || egid==0.
  - has_banned_caps(): ANY of CAP_CHOWN, CAP_DAC_OVERRIDE, CAP_DAC_READ_SEARCH,
    CAP_FOWNER, CAP_MAC_ADMIN, CAP_MAC_OVERRIDE, CAP_MKNOD, CAP_SETGID,
    CAP_SETUID, CAP_SYS_ADMIN, CAP_SYS_MODULE, CAP_SYS_PTRACE, CAP_SYS_RAWIO.
  - is_forbidden_sid(): process SELinux sid is in the pathtrust forbidden list
    (populated at init via pathtrust_add_selctx).
  - => an unprivileged shell (uid 2000, no banned caps, not forbidden sid) is
     NOT subject to Pathtrust. Enforcement only bites once you are root / gain
     banned caps / land in a forbidden SELinux domain.

[5] WHAT THIS MEANS FOR THE EXPLOIT CHAIN (MAJOR REFRAME)
  - The prior log assumed: "get root -> setenforce 0 -> drop binary to
    /data/local/tmp -> run" OR "get root -> insmod root module".
  - Pathtrust BLOCKS BOTH, even after root:
      * exec from /data/local/tmp: bprm_set_creds sees root + non-MNT_TRUSTED
        -> -EPERM. Cannot run a payload binary from /data.
      * mmap PROT_EXEC from /data -> -EPERM.
      * insmod/finit_module from /data -> -EPERM; ANONYMOUS init_module
        (file==NULL) is ALWAYS -EPERM (kernel_module_from_file).
      * request_firmware from /data -> -EPERM.
  - THE ONLY VIABLE POST-ROOT PATH (narrower but cleaner):
      kernel write primitive -> direct cred overwrite (skip setuid syscall) ->
      write hlos_unsigned.tkn to the RAW /dev/block nvuser (a kernel-level
      block write; Pathtrust does NOT hook block I/O, SELinux bypassed by
      writing at kernel level) -> reboot.
      No exec, no module load, no mmap-exec, no setenforce needed.
  - The hard part is UNCHANGED: obtaining the kernel write primitive (LPE).
    Post-exploitation is actually SIMPLER than the log assumed (fewer steps),
    but the pre-exploitation (LPE) is unchanged.

[6] NON-BYPASS INTERFACES (confirmed)
  - /dev/pathtrust ioctl IOCTL_TRUST_FILE = QUERY (returns -EPERM if the queried
    file is non-trusted and caller is root/banned/forbidden). NOT a "mark
    trusted" primitive. No bypass.
  - pathtrust netlink (NETLINK_PATHTRUST) = BROADCAST-ONLY (ptnl_notify_enforce),
    NL_CFG_F_NONROOT_RECV. No kernel receive path -> cannot toggle enforce from
    userspace via netlink.
  - BIDE netlink = listener-only (already documented).

[7] REMAINING OPEN ITEMS
  - Where pathtrust_enforce is toggled at runtime (pathtrustfs.c? bootparam?
    sysctl?). pathtrustfs.c (343 lines) not yet read.
  - What SELinux domains are in the pathtrust forbidden list (pathtrust_add_selctx
    callers - init-time).
  - The full list of MNT_TRUSTED mounts on the live device (which partitions
    beyond /system+/oem are trusted, e.g. is /firmware or /persist trusted?).

OVERALL DEFENSE STACK (now fully enumerated):
  1. Boot chain (ECDSA, hierarchical)
  2. GRSEC/PaX (in-tree)
  3. SELinux (enforcing)
  4. PATHTRUST (2nd LSM, ENFORCES exec/mmap/module/firmware from trusted fs only)
  5. BIDE (integrity DETECTION + TZ bridge, audit-only)
  6. dm-verity (/system+/oem, which also auto-trusts them for Pathtrust)
================================================================================

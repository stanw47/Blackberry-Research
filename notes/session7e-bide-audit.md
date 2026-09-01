================================================================================
SESSION 7E - BIDE KERNEL SOURCE AUDIT (vma/secop/tlv/dev/hash) - 2026-08-29
================================================================================
Goal: find an unprivileged-triggerable bug in BIDE's own kernel code, and map
the detection surface precisely for stealth.

FILES AUDITED (full source): bide_vma.c, bide_secop.c, bide_tlv.c, bide_dev.c,
bide_netlink.c, bide_hash.c, bide_auth.c (skims). No memory-corruption bug found;
BIDE is defensively written. Findings below are architectural + detection-gap.

[1] ARCHITECTURE - BIDE IS DETECTION-ONLY, NEVER BLOCKS
  - All LSM hooks (bide_secop.c) return 0 (allow) unconditionally; they only
    report_incident() -> XML -> JBIDE userspace. BIDE cannot be "bypassed to
    gain anything" because it never denies anything. Being "under BIDE" is
    purely a STEALTH concern (DTEK red), not a survival barrier.
  - /dev/bide ioctl is UID-gated (dev_check_access: BIDE_UID/root/system only),
    all copy_from_user use fixed sizeof(...) (no user-controlled sizes).

[2] DETECTION SURFACE - WHAT IT ACTUALLY WATCHES (bide_secop.c LSM hooks)
  task_create     -> no-op
  task_free       -> auth_remove_pid + child propagation
  task_fix_setuid -> SN_ESCALATED_UID/GID / SN_SYSTEM_UID  (setuid/setgid SYSCALL)
  sb_mount        -> SN_NOSUID / SN_NODEV (only if MS_NOSUID/MS_NODEV REMOVED)
  mmap_file       -> SN_LOW_MMAP_ADDR (only if mmap_min_addr < DEFAULT)
  capset          -> SN_CAPSET (only if cap not already 'allowed')
  bprm_set_creds  -> SN_ROOT_PROCESS_DETECTOR (new root proc after snapshot)
  file_mprotect   -> SN_MPROTECT (CROSS-process only, see gap #1)
  kernel_module_init/free -> COMPILED OUT (#ifdef AVEN_44469_FIXED, never set)

[3] CONCRETE DETECTION GAPS (the stealth map - THE VALUABLE FINDINGS)
  G1. file_mprotect: hook returns 0 if (vma->vm_flags & VM_SHARED) OR
      (vma->vm_mm == current->mm). => mprotect(RWX) on the process's OWN memory
      is NEVER flagged. Only cross-process (ptrace-style) mprotect is flagged.
  G2. task_fix_setuid: hook fires on the setuid/setgid SYSCALL path. A direct
      kernel cred overwrite (current->cred->uid=0) does NOT go through
      task_fix_setuid -> never flagged. (Confirms session 7D stealth plan.)
  G3. capset: 'int allowed_caps = caps_get_caps_for_process()' is an INT (32-bit)
      but kernel_cap_t is 64-bit. Caps 32-63 are INVISIBLE. Also only flags caps
      NOT already allowed. => setting CAP_SYS_ADMIN (21, <32) if already in the
      process's allowed set is NOT re-flagged.
  G4. sb_mount: only flags mounts that REMOVE nosuid or nodev. A normal bind
      mount WITH nosuid+nodev passes silently.
  G5. ALL sensors gated by ctl_snapshot_complete(): before the boot "snapshot"
      finishes, capset/mount/mprotect/report all return early (blind). The
      snapshot is taken via BIDE_IOCTL_TAKE_SNAPSHOT (once). => a pre-snapshot
      or snapshot-abort window exists in theory.
  G6. VMA scanner (vma_scan_task) only scans ROOT processes (util_is_task_root).
      Unprivileged process memory is never hashed/verified.
  G7. Kernel module integrity hashing (kernel_module_init -> tz_add_section) is
      COMPILED OUT (AVEN_44469_FIXED undefined). BIDE does NOT hash loaded
      kernel modules into TZ on this build.

[4] MINOR BUGS / LATENT ISSUES (none exploitable)
  - bide_vma.c vma_find_page(): pte_offset_map() is not pte_unmap()'d on the
    error path (pte !present -> return -EFAULT). kmap leak on 32-bit; no-op on
    ARM64 (the Priv). Correctness bug only.
  - bide_secop.c secop_task_free(): iterates task->children WITHOUT tasklist_lock
    (comment admits IRQ context). Likely dead code (children reparented before
    task_free) but a latent race/UAF hazard if ever reached with live children.
  - bide_secop.c secop_capset(): the int truncation (G3) is also a bug (BIDE
    loses the top 32 capability bits).

[5] THE WHITELIST / LINEAGE MODEL (bide_auth.c)
  - auth_add_pid(pid, AUTH_PERM_*) adds PIDs to an authorized set. Flags:
    PRIVILEGED_GID, PRIVILEGED_CHILDREN, PRIVILEGED_LINEAGE, PRIVILEGED_ZYGOTE,
    SYSTEM_UID, ZYGOTEMGR, ZYGOTEMGR_CHILD, INSTALLD, BUGREPORT.
  - auth_check_parents_permission() walks the PARENT chain (lineage) so a
    process is "authorized" iff its ancestors were whitelisted.
  - Whistlisting is done by the JBIDE process via /dev/bide ioctl
    (BIDE_IOCTL_WHITELIST_* / REGISTER_INSTALLD / FOR_CAPS). Gated by
    dev_check_access() (BIDE_UID/root/system).
  - Implication: BIDE's model = "process is trusted iff its lineage was
    pre-authorized". An exploit must either (a) originate from an already-
    authorized lineage (e.g. system_server) or (b) avoid the syscall hooks.

[6] CONCLUSION
  - BIDE is NOT a kernel-exploit target (no memory bug; defensive code).
  - BIDE is a DETECTION system with a clear, bounded sensor set and several
    concrete gaps (self-mprotect, direct-cred-write, cap truncation, snapshot
    gating, root-only VMA scan).
  - Stealth recipe is now precise: kernel write primitive -> direct cred
    overwrite (skip setuid) -> raw-block token write (skip file LSM) -> do not
    mprotect OTHER processes -> do not mount without nosuid/nodev -> do not
    call setenforce(0). This avoids every BIDE sensor.
  - OPEN QUESTION (next): ctl_snapshot_complete() mechanics - when/how is the
    snapshot taken, can it be prevented/aborted to keep BIDE permanently blind?
    Check bide_ctl.c (ctl_snapshot_initialize) + bide_module.c init order.

ARTIFACTS: durable source at /home/stanw47/priv-research/kernel/bb_kernel_AAO474/
  (drivers/bide/*, security/pathtrust/*, grsecurity/*, bbryqc8992_defconfig).
================================================================================

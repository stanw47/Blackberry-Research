================================================================================
SESSION 7D - BIDE DETECTION MODEL + REBOOT/HEALING ANALYSIS + STRATEGY REVISIT
================================================================================
Triggered by: "why does the phone auto-reboot on exploit push; is BIDE why;
is there self-healing; how to stay under BIDE; can we corrupt boot+system+oem
at once."

[1] WHY IT REBOOTS (corrected understanding - NOT BIDE)
  BIDE's report_incident() (bide_report.c) only builds an XML report -> JBIDE
  userspace (DTEK). It does NOT panic/reboot/kill. BIDE = detector + reporter.
  The reboot is a KERNEL PANIC + forced watchdog bite:
    CONFIG_MSM_FORCE_WDOG_BITE_ON_PANIC=y   (any panic -> watchdog reboot)
    CONFIG_MSM_WATCHDOG_V2=y
    CONFIG_PANIC_TIMEOUT=5
    CONFIG_PANIC_ON_RECURSIVE_FAULT=y
    CONFIG_PANIC_ON_DATA_CORRUPTION=y
  => exploit corrupts kernel state -> panic -> watchdog reboots in ~5s. This is
     fail-CLOSED (reboot on any fault), NOT a "log then decide to reboot" step.
     The "logging" is reset_region_v2.c = persistent reset log written FOR
     FORENSICS (records panic reason), not a pre-reboot protective decision.
  => IMPORTANT: a REBOOT means we actually corrupted kernel state (panic), not
     just got caught. GRSEC/PaX violations usually SIGKILL the process, not
     reboot. So a reboot = real corruption happened (or a BUG_ON / recursive
     fault / data-corruption panic path was hit).

[2] SELF-HEALING?  (answer: NO content self-healing)
  - NO repair/restore phase exists. The closest mechanisms are:
    * Dual bootchain (primary AAW068 + backup AAC603): SBL1 falls back to backup
      aboot if primary is bad. This is the ONLY real "fallback" - already used
      (mute-key recovery). It is failover, not content healing.
    * QCOM watchdog: recovery-by-reset (reboot on hang), not healing.
    * dm-verity: fail-CLOSED (blocks boot on modified /system or /oem). No heal.
    * aboot factory/blocklist check: marks bad state, no heal.
  => The device fails CLOSED everywhere. It never "repairs" a tampered image.

[3] "CORRUPT boot + system + oem AT ONCE" - NO, verification is HIERARCHICAL
  - Each boot stage independently verifies the NEXT stage; it is sequential, not
    a simultaneous all-at-once check:
      PBL (fused key, immutable) -> verifies SBL1 -> verifies aboot ->
      aboot verifies boot.img (ECDSA) -> ramdisk holds dm-verity root-of-trust
      -> dm-verity verifies /system and /oem.
  - Corrupting boot+system+oem simultaneously still trips the SAME gate: aboot
    rejects the modified boot.img. The VERIFIER (aboot) cannot be corrupted
    because it is itself verified by SBL1 (verified by PBL fused key).
  - dm-verity root-of-trust lives INSIDE boot.img's ramdisk (already ECDSA-gated),
    so you cannot change the verity root without a signed boot.img.
  => No "corrupt everything at once" wins; the top of the hierarchy is immutable.

[4] HOW BIDE DETECTS (the model that matters for stealth)
  BIDE = PID-LINEAGE based AUTHORIZATION system (bide_auth.c / bide_secop.c):
    - auth_add_pid(pid, AUTH_PERM_*) adds a PID to an authorized set (granted
      via /dev/bide by JBIDE: zygote, system_server, installd, bugreport, etc.).
    - auth_check_permission(pid, perm) + auth_check_parents_permission(task, perm)
      (walks parent lineage) + auth_check_capabilities(uid, ...) +
      auth_check_banned_caps(task).
    - Sensors fire on SYSCALL/event hooks and report if the action is outside the
      process's authorized lineage:
        setuid/setgid escalation -> SN_ESCALATED_UID / SN_ESCALATED_GID
        capset()               -> SN_CAPSET
        mprotect(RWX)          -> SN_MPROTECT
        mmap low addr          -> SN_LOW_MMAP_ADDR
        mount nosuid/nodev     -> SN_NOSUID / MS_NODEV
        setenforce(0)/policy   -> SN_SELINUX_DISABLED/CHANGED (netlink listener)
        pathtrust disable      -> SN_PATHTRUST_DISABLED (netlink listener)
        VMA anomalies          -> vma_scan_task() + report (bide_vma.c, has BUG_ON)
  KEY: BIDE is AUDIT-ONLY. It never blocks. Being "under BIDE" is a STEALTH
  concern (avoid DTEK red flag), NOT a survival concern (the survival barriers
  are GRSEC/PaX/SELinux, which DO block).

[5] HOW TO STAY UNDER BIDE (stealth rules)
  - The sensors are on SYSCALLS, not on direct kernel memory state. So:
    * Do NOT call setuid(0)/setgid(0) -> instead DIRECTLY overwrite
      current->cred->uid/gid via a kernel write primitive (cred overwrite).
      This never trips SN_ESCALATED_UID/GID.
    * Do NOT call setenforce(0) -> write the token to the RAW nvuser block
      device (bypasses SELinux file check entirely; no setenforce needed).
      Avoids SN_SELINUX_DISABLED.
    * Do NOT capset()/mprotect() -> avoid these syscalls in the payload.
    * Do NOT panic -> keep the exploit clean; a panic = reboot = reset log.
  - Endgame write of hlos_unsigned.tkn goes straight to /dev/block/.../nvuser
    (raw block, kernel-level write), not via /nvram/nvuser (fuse+SELinux).

[6] NEW STRATEGY / NEW ATTACK SURFACE (the important pivot)
  BIDE's kernel hooks (bide_secop.c LSM hooks, bide_vma.c VMA scanner,
  bide_hash.c, bide_tlv.c, bide_xml.c) run in KERNEL context and consume
  ATTACKER-INFLUENCED data from the calling process's own actions:
    - mmap/mprotect/exec layout -> vma_scan_task() walks and hashes the process's
      VMAs (a BUG_ON exists in that path).
    - process caps, mount flags, mmap addresses -> secop hooks.
  This is BB-ORIGINAL kernel code operating on unprivileged-influenced data -
  a genuinely NEW unprivileged-reachable kernel attack surface that was NOT in
  the prior log. If vma_scan_task / secop / hash / tlv has a bug (e.g. an
  inconsistent VMA list, an integer overflow in section hashing, a TLV length
  bug), an unprivileged process can trigger it purely by crafting its own maps.
  => PRIORITY NEW TARGET: audit bide_vma.c (VMA scanner) + bide_secop.c (hooks)
     + bide_hash.c + bide_tlv.c for bugs reachable from unprivileged process
     actions. This is BB's own code AND it's kernel-reachable without root.

REVISED STRATEGY (ranked):
  1. Audit BIDE kernel hooks (vma/scan + secop + hash + tlv) for an unprivileged
     -triggerable kernel bug (NEW surface, BB-original code).
  2. Resume kernel LPE (session 7A) with STEALTH payload: cred overwrite (no
     setuid), raw-block token write (no setenforce/file), clean (no panic).
  3. Crash forensics: after each reboot, read the persistent reset region
     (reset_region_v2) to learn the exact panic reason.
  4. Hardware (balika eMMC swap / ISP) remains the only PROVEN endgame.
  5. Trustlet (widevine underflow) still needs a prior foothold; unchanged.

COULD-MEAN / COULD-NOT-MEAN (explicit):
  - "6 layers" -> COULD mean impenetrable in practice; COULD NOT mean bug-free
    (widevine trustlet underflow already proves inherited code is soft).
  - "BIDE audit-only" -> COULD mean exploitation without BIDE stopping it; COULD
    NOT mean undetected (DTEK will still go red if sensors trip).
  - "watchdog-on-panic" -> COULD mean clean exploits avoid reboot; COULD NOT
    mean the reboot is a deliberate protective "decision" (it is a crash).
  - "AAW068 kernel unreleased" -> COULD mean GPL gap; COULD NOT mean AAW068 is
    materially different from AAO474 (same 3.10.84 line).
================================================================================

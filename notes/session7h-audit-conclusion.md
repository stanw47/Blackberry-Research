================================================================================
SESSION 7H - BIDE/PATHTRUST FULL AUDIT CONCLUSION - 2026-08-29
================================================================================
All BIDE + Pathtrust source files audited. RESULT: no unprivileged-reachable
memory-safety bug that yields a privilege-escalation primitive. The code is
genuinely well-written. Full bug inventory below.

[1] BUG INVENTORY (complete; all minor, none is a root primitive)
  B1. Pathtrust ioctl.c IOCTL_TRUST_FILE: fget() without fput() -> file refcount
      LEAK. Reachable from shell (0666 /dev/pathtrust). LOW (not UAF; f_count is
      64-bit so overflow impractical; not an allocation).
  B2. BIDE vma.c vma_find_page(): pte_offset_map() not pte_unmap()'d on the
      !present error path -> kmap leak. No-op on ARM64 (Priv). Correctness only.
  B3. BIDE secop.c secop_task_free(): iterates task->children WITHOUT
      tasklist_lock (IRQ context). Latent race/UAF; likely dead code (children
      reparented before task_free).
  B4. BIDE secop.c secop_capset() + caps.c: capabilities tracked in a 32-bit
      'int' -> caps 32-63 invisible (detection gap, not memory bug).
  B5. BIDE hash.c: rbtree keyed ONLY on a 32-bit Jenkins/FNV hash; find_node()
      never compares the full key -> hash collision returns the WRONG node.
      Detection-correctness issue (VMA hash baseline confusion), not memory bug.
  B6. BIDE util.c util_get_task_cmdline(): NUL-conversion loop reads p[len+1]
      up to p[sz] -> 1-byte OOB READ (info leak). Gated behind /dev/bide report
      (root/system). LOW.
  B7. Pathtrust pathtrustfs.c pathtrust_write_selinux(): NO capable(CAP_SYS_ADMIN)
      check (unlike the enforce/debug writers). Latent - currently DAC-gated
      (securityfs 0660 root:root) + load-once (pathtrust_ctx_loaded). Not
      reachable as-is.

[2] PATHTRUST RUNTIME STATE (confirmed from source + defconfig)
  - pathtrust_enforce = 1 (CONFIG_SECURITY_PATHTRUST_BOOTPARAM_VALUE=1), and a
    bootparam "pathtrust=" can override at boot.
  - The /sys/kernel/security/pathtrust/enforce WRITE path is COMPILED OUT
    (CONFIG_SECURITY_PATHTRUST_DEVELOP=n). => no runtime userspace toggle.
    (READ-only enforce file exists at /sys/kernel/security/pathtrust/enforce.)
  - The /sys/kernel/security/pathtrust/selinux write path exists (loads the
    forbidden-SID list) but is DAC-gated (0660 root:root) + load-once.

[3] HONEST STRATEGIC CONCLUSION
  - "Audit BlackBerry's own code for a bug" produced 7 real (minor) bugs but NO
    escalation primitive. BIDE/Pathtrust are defensively written (kzalloc,
    strlcat, min_t, fixed sizeof copies, mutexes). The "checks everywhere"
    instinct is correct; the code quality is high where it matters.
  - The B1 fput leak is the most "real" finding and is independently publishable,
    but it is a refcount leak, not a primitive.
  - The AUDIT still had value: (a) it produced a complete, precise map of the
    DETECTION (BIDE) and ENFORCEMENT (Pathtrust) surfaces = the stealth recipe
    (session 7D/7E), and (b) 7 concrete bugs to report.
  - The path to ROOT is therefore UNCHANGED: (i) kernel LPE (session 7A, the
    only software route), or (ii) hardware eMMC swap (the only proven route).
  - The BIDE/Pathtrust audit is DONE. Further effort here has diminishing
    returns; the marginal value now is in the kernel LPE (7A slab-reuse fix) or
    the hardware route, not more BIDE reading.

[4] WHAT IS ACTUALLY PUBLISHABLE (contribution list)
  - Bug report: Pathtrust fput refcount leak (bug-report-pathtrust-fput-leak.md)
  - Bug report: BIDE capset 32-bit truncation (detection gap)
  - Bug report: BIDE hash-collision detection bypass (32-bit hash, no key compare)
  - Bug report: BIDE util_get_task_cmdline 1-byte OOB read
  - Architecture note: BIDE (audit-only) vs Pathtrust (enforcement) + the 6-layer
    stack + the snapshot "blind window" + the detection-gap stealth map.
  None of these is a CVE-grade privilege escalation, but as a set they are a
  genuinely novel public map of BlackBerry's Priv kernel security internals.

ARTIFACTS: sessions 7A-7H + bug reports in /home/stanw47/priv-research/work/;
  source at /home/stanw47/priv-research/kernel/bb_kernel_AAO474/.
================================================================================
